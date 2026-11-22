import React from "react";
import type { QuizAttemptResult } from "../types/quiz";

interface Props {
  result: QuizAttemptResult;
  onStartNewQuiz: () => void;
}

export const QuizResults: React.FC<Props> = ({ result, onStartNewQuiz }) => {
  return (
    <section aria-label="Quiz Results">
      <h2>Quiz Completed: {result.title}</h2>
      <p data-testid="quiz-score">
        Score: {result.score} / {result.total_questions} ({result.percentage}%)
      </p>

      <ol>
        {result.results.map((item, idx) => (
          <li key={item.question_id}>
            <div>
              <strong>
                Question {idx + 1}: {item.is_correct ? "Correct" : "Incorrect"}
              </strong>
              <p>{item.prompt}</p>
              <p>
                Your answer:{" "}
                {item.selected_option_index !== undefined &&
                item.selected_option_index !== null
                  ? item.options[item.selected_option_index]
                  : "No answer selected"}
              </p>
              <p>Correct answer: {item.options[item.correct_option_index]}</p>
              <p>Explanation: {item.explanation}</p>
              {item.lecture_reference && (
                <p>
                  Lecture Reference: {item.lecture_reference.document_title}
                  {item.lecture_reference.section_or_page
                    ? ` (${item.lecture_reference.section_or_page})`
                    : ""}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>

      <button type="button" onClick={onStartNewQuiz}>
        Start Another Quiz
      </button>
    </section>
  );
};
