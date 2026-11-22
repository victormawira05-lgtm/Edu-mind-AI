import React from "react";
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
}) => {
  return (
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
            Q{idx + 1} {answered ? "âœ“" : "â€¢"}
          </button>
        );
      })}
    </nav>
  );
};
