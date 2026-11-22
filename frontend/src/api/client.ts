import type {
  QuizAnswerSubmission,
  QuizAttemptResult,
  StudentQuizResponse,
  WorkspaceProfile,
} from "../types/quiz";
import type {
  DocumentCategory,
  RetrieveResponse,
  UploadedDocumentSummary,
} from "../types/documents";
import type { PastPaperInsightsResponse } from "../types/pastPapers";
import type { ReadinessDashboardResponse } from "../types/readiness";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export interface AuthHeadersInput {
  accessToken: string | null;
  devUserId?: string;
}

function buildHeaders(auth: AuthHeadersInput, includeJson = true): Record<string, string> {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }
  if (auth.accessToken) {
    headers["Authorization"] = `Bearer ${auth.accessToken}`;
  } else if (auth.devUserId) {
    headers["X-Dev-User-Id"] = auth.devUserId;
  }
  return headers;
}

export async function fetchWorkspace(auth: AuthHeadersInput): Promise<WorkspaceProfile> {
  const res = await fetch(`${API_BASE}/api/workspace`, {
    headers: buildHeaders(auth),
  });
  if (!res.ok) throw new Error(`Workspace load failed (${res.status})`);
  return res.json();
}

export async function saveWorkspace(
  auth: AuthHeadersInput,
  profile: WorkspaceProfile
): Promise<WorkspaceProfile> {
  const res = await fetch(`${API_BASE}/api/workspace`, {
    method: "PUT",
    headers: buildHeaders(auth),
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error(`Workspace save failed (${res.status})`);
  return res.json();
}

export async function listUnitDocumentsApi(
  auth: AuthHeadersInput,
  unitId: string
): Promise<UploadedDocumentSummary[]> {
  const normalizedUnit = encodeURIComponent(unitId.trim() || "general");
  const res = await fetch(`${API_BASE}/api/units/${normalizedUnit}/documents`, {
    headers: buildHeaders(auth),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Failed to list documents (${res.status})`);
  }
  return res.json();
}

export async function uploadUnitDocumentApi(
  auth: AuthHeadersInput,
  params: {
    unitId: string;
    file: File;
    title?: string;
    category?: DocumentCategory;
  }
): Promise<UploadedDocumentSummary> {
  const normalizedUnit = encodeURIComponent(params.unitId.trim() || "general");
  const formData = new FormData();
  formData.append("file", params.file);
  if (params.title) {
    formData.append("title", params.title);
  }
  if (params.category) {
    formData.append("category", params.category);
  }

  const res = await fetch(`${API_BASE}/api/units/${normalizedUnit}/documents`, {
    method: "POST",
    headers: buildHeaders(auth, false),
    body: formData,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const detail =
      typeof errBody.detail === "string"
        ? errBody.detail
        : errBody.detail?.message || `Document upload failed (${res.status})`;
    throw new Error(detail);
  }
  return res.json();
}

export async function retrieveUnitChunksApi(
  auth: AuthHeadersInput,
  unitId: string,
  query: string,
  topK = 5,
  category?: DocumentCategory
): Promise<RetrieveResponse> {
  const normalizedUnit = encodeURIComponent(unitId.trim() || "general");
  const res = await fetch(`${API_BASE}/api/units/${normalizedUnit}/retrieve`, {
    method: "POST",
    headers: buildHeaders(auth),
    body: JSON.stringify({
      query,
      top_k: topK,
      category: category ?? null,
    }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Chunk retrieval failed (${res.status})`);
  }
  return res.json();
}

export async function analyzePastPapersApi(
  auth: AuthHeadersInput,
  unitId: string
): Promise<PastPaperInsightsResponse> {
  const normalizedUnit = encodeURIComponent(unitId.trim() || "general");
  const res = await fetch(`${API_BASE}/api/units/${normalizedUnit}/past-papers/analyze`, {
    method: "POST",
    headers: buildHeaders(auth),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Past-paper analysis failed (${res.status})`);
  }
  return res.json();
}

export async function fetchReadinessDashboardApi(
  auth: AuthHeadersInput,
  unitId?: string
): Promise<ReadinessDashboardResponse> {
  const url = new URL(`${API_BASE}/api/readiness`);
  if (unitId && unitId.trim()) {
    url.searchParams.set("unit_id", unitId.trim());
  }
  const res = await fetch(url.toString(), {
    headers: buildHeaders(auth),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Readiness load failed (${res.status})`);
  }
  return res.json();
}

export async function generateQuizApi(
  auth: AuthHeadersInput,
  payload: {
    topic: string;
    num_questions: number;
    unit_id?: string | null;
    lecture_title?: string | null;
  }
): Promise<StudentQuizResponse> {
  const res = await fetch(`${API_BASE}/api/quizzes/generate`, {
    method: "POST",
    headers: buildHeaders(auth),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Quiz generation failed (${res.status})`);
  }
  return res.json();
}

export async function submitQuizApi(
  auth: AuthHeadersInput,
  quizId: string,
  answers: QuizAnswerSubmission[]
): Promise<QuizAttemptResult> {
  const res = await fetch(`${API_BASE}/api/quizzes/${quizId}/submit`, {
    method: "POST",
    headers: buildHeaders(auth),
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Quiz submission failed (${res.status})`);
  }
  return res.json();
}
