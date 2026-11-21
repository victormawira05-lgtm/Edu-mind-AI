export type EvidenceStatus = "demonstrated" | "insufficient_evidence";

export interface QuizHistoryItem {
  attempt_id: string;
  quiz_id: string;
  unit_id?: string | null;
  title: string;
  score: number;
  total_questions: number;
  percentage: number;
}

export interface TopicPerformanceItem {
  topic: string;
  unit_id?: string | null;
  questions_answered: number;
  correct_count: number;
  accuracy_percentage: number;
  evidence_status: EvidenceStatus;
  evidence_note: string;
}

export interface RevisionRecommendation {
  topic: string;
  unit_id?: string | null;
  priority: string;
  evidence_status: EvidenceStatus;
  reason: string;
  suggested_action: string;
  related_documents: string[];
}

export interface ReadinessDashboardResponse {
  user_id: string;
  unit_id?: string | null;
  min_evidence_questions: number;
  total_attempts: number;
  total_questions_answered: number;
  total_correct_answers: number;
  overall_accuracy_percentage: number;
  demonstrated_topics: TopicPerformanceItem[];
  insufficient_evidence_topics: TopicPerformanceItem[];
  recommendations: RevisionRecommendation[];
  recent_attempts: QuizHistoryItem[];
  note: string;
}
