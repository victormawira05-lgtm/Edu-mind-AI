import { useEffect, useState } from "react";
import { onAuthStateChanged, signInWithPopup, signOut, User } from "firebase/auth";
import { collection, addDoc, query, where, orderBy, onSnapshot, serverTimestamp } from "firebase/firestore";
import { auth, db, googleProvider } from "./firebase";
import "./App.css";

type Msg = { role: "user" | "ai"; text: string; subject: string; createdAt?: any };

const SUBJECTS = ["Maths", "English", "Kiswahili", "Science", "Social Studies", "CRE", "Computer"];
const GEMINI_KEY = ""; // optional: paste Gemini API key later for real AI

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [subject, setSubject] = useState("Maths");
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => onAuthStateChanged(auth, setUser), []);

  useEffect(() => {
    if (!user) return;
    const q = query(collection(db, "chats"), where("uid", "==", user.uid), orderBy("createdAt", "asc"));
    return onSnapshot(q, (snap) => setHistory(snap.docs.map(d => d.data() as Msg)));
  }, [user]);

  async function askAI(question: string, subj: string): Promise<string> {
    if (!GEMINI_KEY) {
      return `Great question on ${subj}! Here's how to think about it:\n\n"${question}"\n\n1. What do you already know?\n2. Break it into small steps\n3. Try one step, then check.\n\nTip: Ask me to explain it like I'm 12, give an example, or give a practice question. (Connect a Gemini API key to get real AI answers)`;
    }
    const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: `You are Edu-mind AI, a friendly Kenyan tutor for ${subj}. Explain clearly for a student. Question: ${question}` }] }] })
    });
    const data = await res.json();
    return data.candidates?.[0]?.content?.parts?.[0]?.text || "Sorry, I couldn't answer that. Try again.";
  }

  async function send() {
    if (!input.trim() || !user) return;
    const q = input; setInput(""); setLoading(true);
    await addDoc(collection(db, "chats"), { uid: user.uid, role: "user", text: q, subject, createdAt: serverTimestamp() });
    const answer = await askAI(q, subject);
    await addDoc(collection(db, "chats"), { uid: user.uid, role: "ai", text: answer, subject, createdAt: serverTimestamp() });
    setLoading(false);
  }

  if (!user) {
    return (
      <div className="landing">
        <h1>🧠 Edu-mind AI</h1>
        <p>Your smart study buddy for Kenyan students. Ask anything. Learn faster.</p>
        <div className="subjects-preview">{SUBJECTS.map(s => <span key={s}>{s}</span>)}</div>
        <button className="google-btn" onClick={() => signInWithPopup(auth, googleProvider)}>Continue with Google</button>
        <p className="small">Free • Maths • Science • English • KCSE & KCPE help</p>
      </div>
    );
  }

  const filtered = history.filter(h => h.subject === subject);

  return (
    <div className="app">
      <header>
        <b>🧠 Edu-mind AI</b>
        <div><span>{user.displayName}</span><button onClick={() => signOut(auth)}>Logout</button></div>
      </header>
      <div className="layout">
        <aside>
          <h3>Subjects</h3>
          {SUBJECTS.map(s => <button key={s} className={s === subject ? "active" : ""} onClick={() => setSubject(s)}>{s}</button>)}
          <div className="stats">Total chats: {history.length}<br />This subject: {filtered.length}</div>
        </aside>
        <main>
          <h2>{subject} Tutor</h2>
          <div className="chat">
            {filtered.length === 0 && <p className="empty">Ask your first {subject} question below 👇</p>}
            {filtered.map((m, i) => <div key={i} className={`msg ${m.role}`}><b>{m.role === "user" ? "You" : "Edu-mind"}</b><p>{m.text}</p></div>)}
            {loading && <div className="msg ai"><b>Edu-mind</b><p>Thinking...</p></div>}
          </div>
          <div className="input-row">
            <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} placeholder={`Ask a ${subject} question...`} />
            <button onClick={send} disabled={loading}>Send</button>
          </div>
        </main>
      </div>
    </div>
  );
}
