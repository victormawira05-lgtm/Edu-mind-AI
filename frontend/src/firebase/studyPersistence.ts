import {
  addDoc,
  collection,
  doc,
  getDocs,
  increment,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  type Firestore,
} from "firebase/firestore";
import type { TelemetryEvent } from "../ai/hybridInference";

export interface SavedSummaryRecord {
  documentName: string;
  documentChars: number;
  question: string;
  summaryText: string;
  onDeviceCount: number;
  inCloudCount: number;
  totalLatencyMs: number;
  updatedAt?: unknown;
}

export function buildDocumentSlug(docName: string): string {
  const cleaned = docName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || "untitled-document";
}

export async function saveStudySummaryToFirestore(
  db: Firestore,
  params: {
    documentName: string;
    documentChars: number;
    question: string;
    summaryText: string;
    telemetry: TelemetryEvent[];
    userId?: string;
  }
): Promise<string> {
  const docId = buildDocumentSlug(params.documentName);
  const docRef = doc(db, "studySummaries", docId);

  const onDeviceCount = params.telemetry.filter((t) => t.actualSource === "ON_DEVICE").length;
  const inCloudCount = params.telemetry.filter((t) => t.actualSource === "IN_CLOUD").length;
  const totalLatencyMs = params.telemetry.reduce((acc, t) => acc + t.latencyMs, 0);

  await setDoc(
    docRef,
    {
      documentName: params.documentName,
      documentChars: params.documentChars,
      question: params.question,
      summaryText: params.summaryText,
      userId: params.userId ?? "anonymous",
      lastOnDeviceCount: onDeviceCount,
      lastInCloudCount: inCloudCount,
      lastRunLatencyMs: totalLatencyMs,
      totalOnDeviceCalls: increment(onDeviceCount),
      totalInCloudCalls: increment(inCloudCount),
      updatedAt: serverTimestamp(),
    },
    { merge: true }
  );

  const telemetryCol = collection(db, "studySummaries", docId, "telemetryEvents");
  for (const ev of params.telemetry) {
    await addDoc(telemetryCol, {
      ...ev,
      documentName: params.documentName,
      userId: params.userId ?? "anonymous",
      recordedAt: serverTimestamp(),
    });
  }

  return docId;
}

export async function loadRecentTelemetryForDocument(
  db: Firestore,
  docName: string,
  limitCount = 25
): Promise<TelemetryEvent[]> {
  const docId = buildDocumentSlug(docName);
  const telemetryCol = collection(db, "studySummaries", docId, "telemetryEvents");
  const q = query(telemetryCol, orderBy("timestamp", "asc"));
  const snap = await getDocs(q);

  return snap.docs.slice(-limitCount).map((d) => {
    const data = d.data() as TelemetryEvent;
    return {
      id: d.id,
      timestamp: data.timestamp ?? new Date().toISOString(),
      taskType: data.taskType ?? "short_prompt",
      requestedMode: data.requestedMode ?? "PREFER_ON_DEVICE",
      actualSource: data.actualSource ?? "IN_CLOUD",
      latencyMs: Number(data.latencyMs ?? 0),
      inputChars: Number(data.inputChars ?? 0),
      outputChars: Number(data.outputChars ?? 0),
      fallbackOccurred: Boolean(data.fallbackOccurred),
    };
  });
}
