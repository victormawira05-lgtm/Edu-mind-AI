import React, { useState } from "react";
import { analyzePastPapersApi, AuthHeadersInput } from "../api/client";
import { PastPaperInsightsResponse } from "../types/pastPapers";

interface Props {
  auth: AuthHeadersInput;
  unitId: string;
}

export const PastPaperInsightsPanel: React.FC<Props> = ({ auth, unitId }) => {
  const activeUnit = unitId.trim() || "general";
  const [insights, setInsights] = useState<PastPaperInsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await analyzePastPapersApi(auth, activeUnit);
      setInsights(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze past papers.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section aria-label="Past-Paper Insights">
      <h2>Past-Paper Insights ({activeUnit})</h2>
      <p>
        Optional analysis of uploaded past papers. Historical recurrence reflects only uploaded
        papers and does not guarantee what will appear on future exams.
      </p>

      <button type="button" onClick={runAnalysis} disabled={loading}>
        {loading ? "Analyzing Past Papers..." : "Analyze Uploaded Past Papers"}
      </button>

      {error && <p role="alert">{error}</p>}

      {insights && (
        <div>
          <p role="note">{insights.disclaimer}</p>
          <p>
            Papers analyzed: {insights.analyzed_paper_count} | Questions extracted:{" "}
            {insights.extracted_questions.length}
          </p>

          <h3>Observed Topic Recurrence & Lecture Links</h3>
          <ul>
            {insights.recurrence.map((rec) => (
              <li key={rec.topic}>
                <strong>{rec.topic}</strong> — Observed {rec.occurrence_count} time(s) across{" "}
                {rec.paper_count} paper(s) [{rec.question_types.join(", ")}]
                <div>
                  <small>
                    Evidence:{" "}
                    {rec.evidence
                      .map(
                        (ev) =>
                          `${ev.document_title} (p.${ev.page_number}, ${ev.chunk_id}): "${ev.excerpt}"`
                      )
                      .join(" | ")}
                  </small>
                </div>
                {rec.linked_lectures.length > 0 && (
                  <div>
                    <small>
                      Linked Lecture Notes:{" "}
                      {rec.linked_lectures
                        .map(
                          (lnk) =>
                            `${lnk.lecture_document_title} (p.${lnk.page_number}, ${lnk.chunk_id})`
                        )
                        .join("; ")}
                    </small>
                  </div>
                )}
              </li>
            ))}
          </ul>

          <h3>Extracted Past-Paper Questions</h3>
          <ol>
            {insights.extracted_questions.map((q) => (
              <li key={q.question_id}>
                <strong>
                  {q.question_label} [{q.question_type} — {q.topic}]
                </strong>
                <p>{q.question_text}</p>
                <small>
                  Source: {q.source_evidence.document_title}, Page {q.source_evidence.page_number},
                  Chunk {q.source_evidence.chunk_id}
                </small>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
};
