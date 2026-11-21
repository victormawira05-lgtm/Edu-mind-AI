import React, { useEffect, useState } from "react";
import {
  fetchWorkspace,
  generateQuizApi,
  saveWorkspace,
  submitQuizApi,
} from "./api/client";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { QuizPlayer } from "./quiz/QuizPlayer";
import { StudentQuizResponse, WorkspaceProfile } from "./types/quiz";
import { WorkspacePanel } from "./workspace/WorkspacePanel";

const EduMindWorkspaceApp: React.FC = () => {
  const {
    session,
    accessToken,
    devUserId,
    setDevUserId,
    signIn,
    signUp,
    signOut,
    isSupabaseConfigured,
  } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);

  const [profile, setProfile] = useState<WorkspaceProfile>({ units: [] });
  const [topic, setTopic] = useState("Limits and Continuity");
  const [numQuestions, setNumQuestions] = useState(3);
  const [activeQuiz, setActiveQuiz] = useState<StudentQuizResponse | null>(null);
  const [loadingQuiz, setLoadingQuiz] = useState(false);
  const [quizError, setQuizError] = useState<string | null>(null);

  const authInput = { accessToken, devUserId };
  const isAuthenticated = Boolean(session) || !isSupabaseConfigured;

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchWorkspace(authInput)
      .then(setProfile)
      .catch(() => {});
  }, [isAuthenticated, accessToken, devUserId]);

  const handleAuth = async (mode: "signin" | "signup") => {
    setAuthError(null);
    const err =
      mode === "signin"
        ? await signIn(email, password)
        : await signUp(email, password);
    if (err) setAuthError(err);
  };

  const handleStartQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoadingQuiz(true);
    setQuizError(null);
    try {
      const quiz = await generateQuizApi(authInput, {
        topic: topic.trim(),
        num_questions: numQuestions,
        unit_id: profile.units[0] ?? null,
      });
      setActiveQuiz(quiz);
    } catch (err) {
      setQuizError(err instanceof Error ? err.message : "Could not generate quiz.");
    } finally {
      setLoadingQuiz(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <main>
        <h1>EduMind AI</h1>
        <p>Sign in to access your private study workspace and interactive quizzes.</p>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Student email"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
        />
        <button type="button" onClick={() => handleAuth("signin")}>
          Sign In
        </button>
        <button type="button" onClick={() => handleAuth("signup")}>
          Create Account
        </button>
        {authError && <p role="alert">{authError}</p>}
      </main>
    );
  }

  return (
    <main>
      <header>
        <h1>EduMind AI</h1>
        {!isSupabaseConfigured && (
          <label>
            Local Test Student ID:
            <input
              value={devUserId}
              onChange={(e) => setDevUserId(e.target.value)}
            />
          </label>
        )}
        {session && (
          <button type="button" onClick={signOut}>
            Sign Out
          </button>
        )}
      </header>

      <WorkspacePanel
        profile={profile}
        onSave={async (next) => {
          const saved = await saveWorkspace(authInput, next);
          setProfile(saved);
        }}
      />

      {!activeQuiz ? (
        <section aria-label="Quiz Generator">
          <h2>Interactive Quiz</h2>
          <form onSubmit={handleStartQuiz}>
            <label>
              Topic
              <input value={topic} onChange={(e) => setTopic(e.target.value)} />
            </label>
            <label>
              Questions
              <input
                type="number"
                min={1}
                max={15}
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value) || 3)}
              />
            </label>
            <button type="submit" disabled={loadingQuiz}>
              {loadingQuiz ? "Generating Quiz..." : "Start Interactive Quiz"}
            </button>
          </form>
          {quizError && <p role="alert">{quizError}</p>}
        </section>
      ) : (
        <QuizPlayer
          quiz={activeQuiz}
          onSubmitAnswers={(answers) =>
            submitQuizApi(authInput, activeQuiz.quiz_id, answers)
          }
          onResetQuiz={() => setActiveQuiz(null)}
        />
      )}
    </main>
  );
};

export const App: React.FC = () => (
  <AuthProvider>
    <EduMindWorkspaceApp />
  </AuthProvider>
);

export default App;
