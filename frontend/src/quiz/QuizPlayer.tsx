import React, { useState } from "react";
import type { StudentQuizQuestion } from "../types/quiz";

interface Props {
  questions: StudentQuizQuestion[];
  currentIndex: number;
  selectedAnswers: Record<string, number>;
  onSelectQuestion: (index: number) => void;
}

export const QuestionNavigator: React.FC<Props> = ({
  questions,
  currentIndex,
  selectedAnswers,
  onSelectQuestion,
}) => (
  <nav aria-label="Question Navigation">
    {questions.map((q, idx) => {
      const answered = selectedAnswers[q.id] !== undefined;
      const active = idx === currentIndex;
      return (
        <button
          key={q.id}
          type="button"
          aria-current={active ? "step" : undefined}
          aria-pressed={active}
          onClick={() => onSelectQuestion(idx)}
        >
          Q{idx + 1} {answered ? "✓" : "•"}
        </button>
      );
    })}
  </nav>
);

export const QuizPlayer: React.FC<{
  quiz: { quiz_id: string; title: string; questions: StudentQuizQuestion[] };
  onSubmitAnswers: (answers: { question_id: string; selected_option_index: number }[]) => Promise<any>;
  onResetQuiz: () => void;
}> = ({ quiz, onSubmitAnswers, onResetQuiz }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attemptResult, setAttemptResult] = useState<any | null>(null);

  if (attemptResult) {
    return (
      <section aria-label="Quiz Results">
        <h2>Quiz Completed: {attemptResult.title}</h2>
        <p data-testid="quiz-score">
          Score: {attemptResult.score} / {attemptResult.total_questions} ({attemptResult.percentage}%)
        </p>
        <ol>
          {attemptResult.results.map((item: any, idx: number) => (
            <li key={item.question_id}>
              <strong>
                Question {idx + 1}: {item.is_correct ? "Correct" : "Incorrect"}
              </strong>
              <p>{item.prompt}</p>
              <p>Explanation: {item.explanation}</p>
              {item.lecture_reference && (
                <p>
                  Lecture Reference: {item.lecture_reference.document_title}
                  {item.lecture_reference.section_or_page ? ` (${item.lecture_reference.section_or_page})` : ""}
                </p>
              )}
            </li>
          ))}
        </ol>
        <button type="button" onClick={onResetQuiz}>
          Start Another Quiz
        </button>
      </section>
    );
  }

  const currentQuestion = quiz.questions[currentIndex];
  const currentSelection = selectedAnswers[currentQuestion.id];

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const answers = quiz.questions.map((q) => ({
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
        <div role="radiogroup" aria-label={currentQuestion.prompt}>
          {currentQuestion.options.map((optionText, idx) => (
            <label key={idx}>
              <input
                type="radio"
                name={`question-${currentQuestion.id}`}
                checked={currentSelection === idx}
                onChange={() =>
                  setSelectedAnswers((prev) => ({ ...prev, [currentQuestion.id]: idx }))
                }
              />
              {optionText}
            </label>
          ))}
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
          onClick={() => setCurrentIndex((i) => Math.min(quiz.questions.length - 1, i + 1))}
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

