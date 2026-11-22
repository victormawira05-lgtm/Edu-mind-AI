import React, { useEffect, useMemo, useState } from "react";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type Auth,
  type User,
} from "firebase/auth";

interface GoogleAuthBarProps {
  auth: Auth;
  onUserChange?: (user: User | null) => void;
}

export const GoogleAuthBar: React.FC<GoogleAuthBarProps> = ({ auth, onUserChange }) => {
  const provider = useMemo(() => {
    const p = new GoogleAuthProvider();
    p.setCustomParameters({ prompt: "select_account" });
    return p;
  }, []);

  const [user, setUser] = useState<User | null>(auth.currentUser);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      onUserChange?.(nextUser);
    });
    return () => unsub();
  }, [auth, onUserChange]);

  async function handleSignIn() {
    if (busy) return;
    setBusy(true);
    setErrorMsg("");
    try {
      await signInWithPopup(auth, provider);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Google sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOut() {
    if (busy) return;
    setBusy(true);
    setErrorMsg("");
    try {
      await signOut(auth);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Sign-out failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      {user ? (
        <>
          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700">
            {user.photoURL ? (
              <img
                src={user.photoURL}
                alt={user.displayName ?? "Student avatar"}
                className="h-5 w-5 rounded-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 font-semibold text-white">
                {(user.displayName || user.email || "U").charAt(0).toUpperCase()}
              </span>
            )}
            <span className="max-w-[180px] truncate font-medium text-slate-900">
              {user.displayName || user.email || "Signed-in Student"}
            </span>
            <span className="rounded bg-slate-200/80 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
              {user.uid.slice(0, 8)}
            </span>
          </div>

          <button
            type="button"
            onClick={handleSignOut}
            disabled={busy}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {busy ? "Signing out..." : "Sign out"}
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={handleSignIn}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-800 shadow-2xs hover:bg-slate-50 disabled:opacity-50"
        >
          <span>{busy ? "Signing in..." : "Sign in with Google"}</span>
        </button>
      )}

      {errorMsg && <span className="text-xs text-red-600">{errorMsg}</span>}
    </div>
  );
};
