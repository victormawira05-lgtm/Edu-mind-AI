import React, { useState } from "react";
import {
  QuizAnswerSubmission,
  QuizAttemptResult,
  StudentQuizResponse,
} from "../types/quiz";
import { QuestionNavigator } from "./QuestionNavigator";
import { QuizResults } from "./QuizResults";

interface Props {
  quiz: StudentQuizResponse;
  onSubmitAnswers: (answers: QuizAnswerSubmission[]) => Promise<QuizAttemptResult>;
  onResetQuiz: () => void;
}

export const QuizPlayer: React.FC<Props> = ({
  quiz,
  onSubmitAnswers,
  onResetQuiz,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attemptResult, setAttemptResult] = useState<QuizAttemptResult | null>(null);

  if (attemptResult) {
    return <QuizResults result={attemptResult} onStartNewQuiz={onResetQuiz} />;
  }

  const currentQuestion = quiz.questions[currentIndex];
  const currentSelection = selectedAnswers[currentQuestion.id];

  const handleSelectOption = (optionIndex: number) => {
    setSelectedAnswers((prev) => ({
      ...prev,
      [currentQuestion.id]: optionIndex,
    }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const answers: QuizAnswerSubmission[] = quiz.questions.map((q) => ({
        question_id: q.id,
        selected_option_index: selectedAnswers[q.id] ?? -1,
      }));
      const res = await onSubmitAnswers(answers);
      setAttemptResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit quiz.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section aria-label="Interactive Quiz Player">
      <h2>{quiz.title}</h2>
      <QuestionNavigator
        questions={quiz.questions}
        currentIndex={currentIndex}
        selectedAnswers={selectedAnswers}
        onSelectQuestion={setCurrentIndex}
      />

      <div>
        <p>
          Question {currentIndex + 1} of {quiz.questions.length} ({currentQuestion.topic})
        </p>
        <h3>{currentQuestion.prompt}</h3>

        {currentQuestion.lecture_reference && (
          <p>
            Lecture Reference: {currentQuestion.lecture_reference.document_title}
            {currentQuestion.lecture_reference.section_or_page
              ? ` — ${currentQuestion.lecture_reference.section_or_page}`
              : ""}
          </p>
        )}

        <div role="radiogroup" aria-label={currentQuestion.prompt}>
          {currentQuestion.options.map((optionText, idx) => {
            const checked = currentSelection === idx;
            return (
              <label key={idx}>
                <input
                  type="radio"
                  name={`question-${currentQuestion.id}`}
                  checked={checked}
                  onChange={() => handleSelectOption(idx)}
                />
                {optionText}
              </label>
            );
          })}
        </div>
      </div>

      <div>
        <button
          type="button"
          disabled={currentIndex === 0}
          onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
        >
          Previous
        </button>
        <button
          type="button"
          disabled={currentIndex === quiz.questions.length - 1}
          onClick={() =>
            setCurrentIndex((i) => Math.min(quiz.questions.length - 1, i + 1))
          }
        >
          Next
        </button>
        <button type="button" disabled={submitting} onClick={handleSubmit}>
          {submitting ? "Grading..." : "Submit Quiz"}
        </button>
      </div>

      {error && <p role="alert">{error}</p>}
    </section>
  );
};
