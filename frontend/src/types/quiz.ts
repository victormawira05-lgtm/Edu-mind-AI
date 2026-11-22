export interface LectureReference {
  document_title: string;
  section_or_page?: string | null;
  excerpt?: string | null;
}

export interface StudentQuizQuestion {
  id: string;
  prompt: string;
  options: string[];
  topic: string;
  lecture_reference?: LectureReference | null;
}

export interface StudentQuizResponse {
  quiz_id: string;
  title: string;
  unit_id?: string | null;
  questions: StudentQuizQuestion[];
}

export interface QuizAnswerSubmission {
  question_id: string;
  selected_option_index: number;
}

export interface GradedQuestionResult {
  question_id: string;
  prompt: string;
  options: string[];
  selected_option_index?: number | null;
  correct_option_index: number;
  is_correct: boolean;
  explanation: string;
  topic: string;
  lecture_reference?: LectureReference | null;
}

export interface QuizAttemptResult {
  attempt_id: string;
  quiz_id: string;
  title: string;
  score: number;
  total_questions: number;
  percentage: number;
  results: GradedQuestionResult[];
}

export interface WorkspaceProfile {
  institution?: string | null;
  programme?: string | null;
  semester?: string | null;
  units?: string[];
  unit_id?: string;
  unit_name?: string;
  display_name?: string;
  target_grade?: string;
  study_goals?: string;
  notes?: string;
  [key: string]: unknown;
}