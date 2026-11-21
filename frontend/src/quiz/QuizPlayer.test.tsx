import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QuizPlayer } from "./QuizPlayer";
import { StudentQuizResponse } from "../types/quiz";

const sampleQuiz: StudentQuizResponse = {
  quiz_id: "quiz-101",
  title: "Calculus Practice",
  questions: [
    {
      id: "q-1",
      prompt: "What is d/dx(x^2)?",
      options: ["2x", "x", "2"],
      topic: "Derivatives",
      lecture_reference: {
        document_title: "Calculus 1 notes",
        section_or_page: "Page 14",
      },
    },
    {
      id: "q-2",
      prompt: "What is d/dx(5)?",
      options: ["0", "5", "1"],
      topic: "Constants",
      lecture_reference: null,
    },
  ],
};

describe("QuizPlayer", () => {
  it("supports navigation, answer selection, deterministic grading results, and omits raw JSON", async () => {
    const onSubmitAnswers = vi.fn().mockResolvedValue({
      attempt_id: "att-1",
      quiz_id: "quiz-101",
      title: "Calculus Practice",
      score: 1,
      total_questions: 2,
      percentage: 50,
      results: [
        {
          question_id: "q-1",
          prompt: "What is d/dx(x^2)?",
          options: ["2x", "x", "2"],
          selected_option_index: 0,
          correct_option_index: 0,
          is_correct: true,
          explanation: "Power rule gives 2x.",
          topic: "Derivatives",
          lecture_reference: {
            document_title: "Calculus 1 notes",
            section_or_page: "Page 14",
          },
        },
        {
          question_id: "q-2",
          prompt: "What is d/dx(5)?",
          options: ["0", "5", "1"],
          selected_option_index: 1,
          correct_option_index: 0,
          is_correct: false,
          explanation: "The derivative of any constant is 0.",
          topic: "Constants",
          lecture_reference: null,
        },
      ],
    });

    render(
      <QuizPlayer
        quiz={sampleQuiz}
        onSubmitAnswers={onSubmitAnswers}
        onResetQuiz={vi.fn()}
      />
    );

    expect(screen.getByText(/What is d\/dx\(x\^2\)\?/i)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("2x"));

    fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    expect(screen.getByText(/What is d\/dx\(5\)\?/i)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("5"));

    fireEvent.click(screen.getByRole("button", { name: /Submit Quiz/i }));

    await waitFor(() => {
      expect(screen.getByTestId("quiz-score")).toHaveTextContent("Score: 1 / 2 (50%)");
    });
    expect(screen.getByText(/Question 1: Correct/i)).toBeInTheDocument();
    expect(screen.getByText(/Question 2: Incorrect/i)).toBeInTheDocument();
    expect(screen.getByText(/The derivative of any constant is 0\./i)).toBeInTheDocument();
    expect(screen.getByText(/Calculus 1 notes \(Page 14\)/i)).toBeInTheDocument();
    expect(screen.queryByText(/"attempt_id"/i)).not.toBeInTheDocument();
  });
});
