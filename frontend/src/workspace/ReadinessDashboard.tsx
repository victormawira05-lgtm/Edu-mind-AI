import React, { useEffect, useState } from "react";
import { fetchReadinessDashboardApi } from "../api/client";
import type { AuthHeadersInput } from "../api/client";
import type { ReadinessDashboardResponse } from "../types/readiness";

interface Props {
  auth: AuthHeadersInput;
  unitId?: string;
}

export const ReadinessDashboard: React.FC<Props> = ({ auth, unitId }) => {
  const [data, setData] = useState<ReadinessDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReadinessDashboardApi(auth, unitId)
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load readiness."));
  }, [auth.accessToken, auth.devUserId, unitId]);

  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p>Loading readiness summary...</p>;

  return (
    <section aria-label="Readiness and Revision Dashboard">
      <h2>Readiness & Revision Dashboard</h2>
      <p role="note">{data.note}</p>
      <p>
        Overall Accuracy: <strong>{data.overall_accuracy_percentage}%</strong> (
        {data.total_correct_answers}/{data.total_questions_answered} questions across{" "}
        {data.total_attempts} attempt(s))
      </p>

      <h3>Demonstrated Topic Performance ({data.demonstrated_topics.length})</h3>
      <ul>
        {data.demonstrated_topics.map((t) => (
          <li key={`${t.unit_id ?? "all"}-${t.topic}`}>
            <strong>{t.topic}</strong> â€” {t.accuracy_percentage}% ({t.correct_count}/
            {t.questions_answered}) [Demonstrated]
            <div>
              <small>{t.evidence_note}</small>
            </div>
          </li>
        ))}
      </ul>

      <h3>Insufficient Evidence Topics ({data.insufficient_evidence_topics.length})</h3>
      <ul>
        {data.insufficient_evidence_topics.map((t) => (
          <li key={`${t.unit_id ?? "all"}-${t.topic}`}>
            <strong>{t.topic}</strong> â€” {t.accuracy_percentage}% ({t.correct_count}/
            {t.questions_answered}) [Insufficient Evidence]
            <div>
              <small>{t.evidence_note}</small>
            </div>
          </li>
        ))}
      </ul>

      <h3>Revision Recommendations</h3>
      <ul>
        {data.recommendations.map((rec, idx) => (
          <li key={`${rec.topic}-${idx}`}>
            <strong>
              [{rec.priority.toUpperCase()}] {rec.topic}
            </strong>{" "}
            â€” {rec.reason}
            <div>{rec.suggested_action}</div>
          </li>
        ))}
      </ul>

      <h3>Recent Quiz Attempts</h3>
      <ul>
        {data.recent_attempts.map((att) => (
          <li key={att.attempt_id}>
            {att.title}: {att.score}/{att.total_questions} ({att.percentage}%)
          </li>
        ))}
      </ul>
    </section>
  );
};
