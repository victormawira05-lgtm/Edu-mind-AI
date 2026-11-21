export type QuestionType =
  | "calculation"
  | "conceptual"
  | "proof_or_derivation"
  | "short_answer";

export interface EvidencePointer {
  document_id: string;
  document_title: string;
  page_number: number;
  chunk_id: string;
  excerpt: string;
}

export interface LectureLink {
  lecture_document_id: string;
  lecture_document_title: string;
  page_number: number;
  chunk_id: string;
  relevance_score: number;
  excerpt: string;
}

export interface ExtractedPastPaperQuestion {
  question_id: string;
  unit_id: string;
  question_label: string;
  question_text: string;
  topic: string;
  question_type: QuestionType;
  source_evidence: EvidencePointer;
  lecture_links: LectureLink[];
}

export interface TopicRecurrenceEntry {
  topic: string;
  occurrence_count: number;
  paper_count: number;
  question_types: QuestionType[];
  evidence: EvidencePointer[];
  linked_lectures: LectureLink[];
}

export interface PastPaperInsightsResponse {
  unit_id: string;
  analyzed_paper_count: number;
  extracted_questions: ExtractedPastPaperQuestion[];
  recurrence: TopicRecurrenceEntry[];
  disclaimer: string;
}
