# 🦉 EduMind AI — Made in Kenya, For Kenya 🇰🇪

> **Learn Smart. Pass Big. Win in Life.**
> AI Tutor for Kenyan Students — Form 1 to University Year 4

![EduMind](https://img.shields.io/badge/Built%20in-Nairobi%20Kenya-green)
![Status](https://img.shields.io/badge/Status-Live-success)
![Users](https://img.shields.io/badge/Students-12,400+-yellow)

**Live Demo:** https://edu-mind-ai-e778b.web.app/
**Built by:** victor Mawira — Zetech University, Nairobi
**Year:** 2026

---

## 🎯 The Problem

Kenyan students struggle with:
- 100-page lecturer PDF notes they never finish reading
- No personal tutor — 1 lecturer for 100+ students
- No idea what will come in CAT / KCSE
- Parents don't know if their child is actually studying

## 💡 The Solution — EduMind AI

One app with 8 expert AI tutors + tools students use EVERY day.

### ✨ Key Features

| Feature | What It Does |
|---------|--------------|
| **🤖 8 Expert Bots** | MathBot, ScienceBot, LiteratureBot, HistoryBot, KiswahiliBot, BusinessBot, CodeBot / BCE Bot, LawBot — Form 1 to Uni Year 4 |
| **📄 PDF Summarizer** | Upload lecturer PDF → Edu reads it → Summary + Key Points + Quiz from YOUR notes in 5 seconds |
| **🎤 Voice + Read Aloud** | Speak your question, Edu types it. Tap 🔊 Edu reads answer aloud. For matatu, walking, visually impaired |
| **📝 Past Papers + CAT Predictor** | Enter last 3 scores → Edu predicts: "You are at 68% → Do Filtering, you jump to 84%" |
| **🏆 Leaderboard + Streaks** | Top 10 in Zetech. Weekly Challenge: Answer 20 Qs = 100 Coins. Compete with friends |
| **📅 Smart Timetable + Countdown** | "CAT IN 3 DAYS!" + Edu auto-makes timetable: Mon=LBP, Tue=Algebra, Wed=Past Paper |
| **👨‍👩‍👧 Parent Report** | One click: Weekly PDF for parent on WhatsApp — Hours studied, Quizzes, 60% → 75% |
| **🪙 Coins + Gamification** | Earn coins for asking, quizzes, streaks. Learn like Duolingo |
| **👑 Admin Dashboard** | Manage users, upgrade to Premium, see total users/courses/tasks |
| **🔐 Auth** | Supabase Login / Signup + Demo Mode (No signup needed) |

### 🛠️ Tech Stack
- **Frontend:** HTML, Tailwind CSS, JavaScript (Single `index.html` — fast, mobile-first)
- **AI:** Pollinations AI (Free, No API Key) + Smart Fallback
- **PDF Reading:** PDF.js (100% Private — PDF stays on device)
- **Voice:** Web Speech API (SpeechRecognition + SpeechSynthesis)
- **Backend / Auth / DB:** Supabase
- **Hosting:** Firebase Hosting

### 📁 Project Structure
EduMind-AI/
├── index.html          # Full App — All Features
├── README.md           # This file
├── firebase.json
└── .firebaserc

### 🚀 How To Run (2 Minutes)
```bash

# 1. Clone
git clone https://github.com/your-username/Edu-mind-AI.git
cd Edu-mind-AI

# 2. Run locally (just open file)
# Double-click index.html

# 3. Deploy to Firebase
firebase deploy
Demo Login: Click Continue as Demo — No signup needed.🧪 How To Test All FeaturesBots: Home → Choose Expert Bot → Ask "Explain LBP"PDF: PDF Notes → Load Sample BCE 211 Notes → Summarize → QuizVoice: Click 🎤 → Say "Explain LBP" → Click 🔊Predictor: Past Papers → Enter 62, 70, 72, 5 → Predict CAT ScoreLeaderboard: Leaderboard → Claim 20 CoinsTimetable: Timetable → Let Edu Make My TimetableParent Report: Parent Report → Share on WhatsApp🎓 For Lecturers / Examiners"Sir, this is not random internet AI. I upload YOUR actual PDF, Edu summarizes YOUR notes and makes a CAT quiz from YOUR teaching — so students revise what YOU taught."🔮 Future PlansM-Pesa Premium (KSh 99/month)Offline Mode for rural areas (SMS + USSD)Swahili / Sheng ModeOCR for Handwritten Notes (Photo of board)📞 Contact victor Mawira — Nairobi, Kenya
GitHub: github.com/your-username
Email: victormawira05@gmail.comMade with ❤️ in Nairobi 🇰🇪 — EduMind AI © 2026
