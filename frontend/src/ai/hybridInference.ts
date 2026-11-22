import { getAI, getGenerativeModel, GoogleAIBackend, InferenceMode } from "firebase/ai";
import type { FirebaseApp } from "firebase/app";

export type ExecutionPath = "ON_DEVICE" | "IN_CLOUD";

export interface TelemetryEvent {
  id: string;
  timestamp: string;
  taskType: "short_prompt" | "long_summary" | "chunk_summary" | "synthesis";
  requestedMode: "PREFER_ON_DEVICE" | "ONLY_IN_CLOUD";
  actualSource: ExecutionPath;
  latencyMs: number;
  inputChars: number;
  outputChars: number;
  fallbackOccurred: boolean;
}

export interface HybridStudyResult {
  text: string;
  telemetry: TelemetryEvent[];
}

export interface HybridRouterConfig {
  firebaseApp: FirebaseApp;
  cloudModel?: string;
  shortPromptThresholdChars?: number; // Default: 2500 chars
  longPdfThresholdChars?: number;     // Default: 60000 chars (matches backend chunking threshold)
  chunkSizeChars?: number;           // Default: 25000 chars per chunk
  onTelemetry?: (event: TelemetryEvent) => void;
}

export function createEduMindHybridRouter(config: HybridRouterConfig) {
  const {
    firebaseApp,
    cloudModel = "gemini-2.5-flash",
    shortPromptThresholdChars = 2500,
    longPdfThresholdChars = 60000,
    chunkSizeChars = 25000,
    onTelemetry,
  } = config;

  const ai = getAI(firebaseApp, { backend: new GoogleAIBackend() });

  // Prefers local Chrome on-device execution when available; falls back to cloud model.
  const preferLocalModel = getGenerativeModel(ai, {
    mode: InferenceMode.PREFER_ON_DEVICE,
    inCloudParams: { model: cloudModel },
  });

  // Forces cloud Gemini execution for large documents or multi-chunk synthesis.
  const cloudOnlyModel = getGenerativeModel(ai, {
    mode: InferenceMode.ONLY_IN_CLOUD,
    inCloudParams: { model: cloudModel },
  });

  function splitIntoSections(text: string, size: number): string[] {
    const cleaned = text.trim();
    if (!cleaned) return [];
    const sections: string[] = [];
    let start = 0;

    while (start < cleaned.length) {
      let end = Math.min(start + size, cleaned.length);
      if (end < cleaned.length) {
        const newlineIdx = cleaned.lastIndexOf("\n", end);
        if (newlineIdx > start + Math.floor(size * 0.7)) {
          end = newlineIdx;
        }
      }
      const slice = cleaned.slice(start, end).trim();
      if (slice) sections.push(slice);
      start = end;
    }

    return sections;
  }

  function normalizeSource(rawSource: unknown, fallbackMode: ExecutionPath): ExecutionPath {
    if (rawSource === "ON_DEVICE" || rawSource === "IN_CLOUD") {
      return rawSource;
    }
    return fallbackMode;
  }

  async function runSingleCall(
    prompt: string,
    taskType: TelemetryEvent["taskType"],
    forceCloud: boolean,
    telemetryLog: TelemetryEvent[]
  ): Promise<string> {
    const startedAt = performance.now();
    const model = forceCloud ? cloudOnlyModel : preferLocalModel;
    const requestedMode: TelemetryEvent["requestedMode"] = forceCloud
      ? "ONLY_IN_CLOUD"
      : "PREFER_ON_DEVICE";

    const response = await model.generateContent(prompt);
    const text = response.response.text();
    const latencyMs = Math.round(performance.now() - startedAt);

    // response.response.inferenceSource indicates whether ON_DEVICE or IN_CLOUD ran.
    const actualSource = normalizeSource(
      (response.response as { inferenceSource?: unknown }).inferenceSource,
      forceCloud ? "IN_CLOUD" : "ON_DEVICE"
    );

    const event: TelemetryEvent = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: new Date().toISOString(),
      taskType,
      requestedMode,
      actualSource,
      latencyMs,
      inputChars: prompt.length,
      outputChars: text.length,
      fallbackOccurred: !forceCloud && actualSource === "IN_CLOUD",
    };

    telemetryLog.push(event);
    onTelemetry?.(event);
    return text;
  }

  async function askOrSummarize(params: {
    question: string;
    documentText: string;
    documentName?: string;
    forceWholeSummary?: boolean;
  }): Promise<HybridStudyResult> {
    const telemetry: TelemetryEvent[] = [];
    const docName = params.documentName || "uploaded-document.pdf";
    const qLower = params.question.toLowerCase();

    const isSummaryRequest =
      Boolean(params.forceWholeSummary) ||
      /\b(summarize|summary|whole pdf|entire document|whole document)\b/.test(qLower);

    const combinedPayloadChars = params.question.length + params.documentText.length;

    // 1. Short study prompt / quick concept check -> prefer on-device execution
    if (!isSummaryRequest && combinedPayloadChars <= shortPromptThresholdChars) {
      const prompt = [
        "You are EduMind AI, a concise study tutor. Answer clearly using bullet points.",
        `Study Context:\n${params.documentText}`,
        `Question: ${params.question}`,
      ].join("\n\n");

      const text = await runSingleCall(prompt, "short_prompt", false, telemetry);
      return { text, telemetry };
    }

    // 2. Medium-to-long document summary up to threshold -> cloud execution in single pass
    if (params.documentText.length <= longPdfThresholdChars) {
      const prompt = [
        `You are summarizing "${docName}" (${params.documentText.length.toLocaleString()} chars).`,
        `User request: ${params.question}`,
        "Provide a structured, thorough summary covering major sections, definitions, formulas/key concepts, and takeaways.",
        `Document Text:\n${params.documentText}`,
      ].join("\n\n");

      const text = await runSingleCall(prompt, "long_summary", true, telemetry);
      return { text, telemetry };
    }

    // 3. Very large PDF (> 60,000 chars) -> section-by-section chunking + cloud synthesis
    const chunks = splitIntoSections(params.documentText, chunkSizeChars);
    const totalParts = chunks.length;
    const partSummaries: string[] = [];

    for (let i = 0; i < totalParts; i++) {
      const partNum = i + 1;
      const chunkPrompt = [
        `Summarize Part ${partNum} of ${totalParts} of "${docName}".`,
        `Goal: ${params.question}`,
        "Extract key headings, definitions, formulas/rules, and main takeaways concisely.",
        `Section Content:\n${chunks[i]}`,
      ].join("\n\n");

      const summary = await runSingleCall(chunkPrompt, "chunk_summary", true, telemetry);
      partSummaries.push(`### Part ${partNum} of ${totalParts}\n${summary}`);
    }

    const synthesisPrompt = [
      `Synthesize these ${totalParts} section summaries of "${docName}" into a cohesive, complete document summary.`,
      `User request: ${params.question}`,
      "Organize by major themes/sections and preserve key definitions, formulas, and takeaways without dropping important details.",
      `Section Summaries:\n${partSummaries.join("\n\n")}`,
    ].join("\n\n");

    const finalText = await runSingleCall(synthesisPrompt, "synthesis", true, telemetry);
    return { text: finalText, telemetry };
  }

  return {
    askOrSummarize,
  };
}
