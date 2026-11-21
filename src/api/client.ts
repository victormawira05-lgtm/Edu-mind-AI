import {
  QuizAnswerSubmission,
  QuizAttemptResult,
  StudentQuizResponse,
  WorkspaceProfile,
} from "../types/quiz";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface AuthHeadersInput {
  accessToken: string | null;
  devUserId?: string;
}

function buildHeaders(auth: AuthHeadersInput): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
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
