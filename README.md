# 🧠 Edu-mind AI — Engineering Maths Tutor (Online)

> Your AI tutor for Engineering Maths that never sleeps, never gets tired, and explains step-by-step.

Edu-mind AI helps students master Statistics, Calculus, Physics, Hypothesis Testing, Linear Regression, ANOVA, Likelihood Ratio Test, and more — with real AI, flashcards, tests, summaries, image generation, and voice answers.

Built for students in Kenya and beyond — study **ONLINE with real AI** or **OFFLINE** when bundles run out.

**Live Demo:** [https://edu-mind-ai.web.app](https://edu-mind-ai.web.app) ← *replace with your real Firebase URL*
**Repo:** https://github.com/victormawira05-lgtm/Edu-mind-AI
**License:** [MIT](https://github.com/victormawira05-lgtm/Edu-mind-AI/blob/main/LICENSE)

---

## ✨ Features

| Feature | What it does |
| :--- | :--- |
| **AI Assistant** | Solves ANY question step-by-step — mean, slope, intercept, prediction, not just final answer |
| **Flashcards** | Turns any topic into quick revision cards |
| **Summary** | Condenses a whole topic into minutes |
| **Test** | Generates MCQs from the same topic to practice for exams |
| **Image Gen** | Generates diagrams for visual learning |
| **Speak Answer** | Reads answers aloud — learn while walking |
| **ONLINE / OFFLINE** | ONLINE = Real AI. OFFLINE = Instant local fallback, no internet needed |
| **Subjects** | Statistics & Probability, Calculus, Physics, Hypothesis Testing, Linear Regression, Computer Vision, ANOVA, Likelihood Ratio Test, Mathematics, Biology |

### Example
**Ask:** *Fit simple linear regression Y on X. X = 41, 28, 41, 31, 22. Y = 74, 64, 82. Predict when X = 35.*
**Edu-mind AI returns:** Mean of X, Mean of Y, Slope, Intercept, then Prediction — fully explained.

---

## 🛠️ Tech Stack

- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **Auth & Database:** Firebase Authentication (Google Login) + Firestore
- **Storage:** Supabase
- **Backend:** Node.js / Express hosted on Render
- **AI:** AI Model API for step-by-step solving, summaries, flashcards, and test generation
- **Deployment:** Firebase Hosting

### How It Meets The Technology Requirement
Edu-mind AI is an AI-powered cloud web app built end-to-end:
1. User logs in with Firebase Auth
2. Frontend (React/Vite) sends question to Node.js backend on Render
3. Backend calls AI model, returns step-by-step solution
4. Firestore saves user history, subjects, and chats
5. Works ONLINE (real AI) and OFFLINE (local fallback)

---

## 🚀 Getting Started

### 1. Clone
```bash
git clone https://github.com/victormawira05-lgtm/Edu-mind-AI.git
cd Edu-mind-AI

##2. Install
npm install

3. Env Variables
Create .env in root:envVITE_FIREBASE_API_KEY=your_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_BACKEND_URL=https://your-backend.onrender.com

4. Run
bash
npm run dev

5.
Buildbashnpm run build

📁 Project StructurejavascriptEdu-mind-AI/
├── src/
│   ├── components/      # Sidebar, Chat, Flashcards, Test, etc.
│   ├── pages/           # Home, Tutor, Auth
│   ├── lib/             # Firebase, Supabase, AI helpers
│   └── App.tsx
├── public/
├── .env.example
└── README.md🎥 Demo Video
Watch 3-Min Demo on YouTube ← paste your link https://youtu.be/qA1vl8cehw4
