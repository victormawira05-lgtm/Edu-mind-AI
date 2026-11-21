export type DocumentCategory = "lecture_notes" | "past_paper" | "other";

export interface SourceMetadata {
  document_id: string;
  document_title: string;
  category: DocumentCategory;
  unit_id: string;
  page_number: number;
  chunk_index: number;
}

export interface UploadedDocumentSummary {
  document_id: string;
  user_id: string;
  unit_id: string;
  title: string;
  filename: string;
  category: DocumentCategory;
  page_count: number;
  extracted_chars: number;
  chunk_count: number;
  uploaded_at: string;
}

export interface RetrievedChunkResult {
  chunk_id: string;
  content: string;
  score: number;
  source: SourceMetadata;
}

export interface RetrieveResponse {
  unit_id: string;
  query: string;
  results: RetrievedChunkResult[];
}
