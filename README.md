 EduMind AI 🎓🤖
### Your Intelligent AI Learning Assistant

EduMind AI helps students learn smarter by uploading PDFs and chatting with their documents. Built with FastAPI, PyPDF, and deployed on Render.

**Live API:** `https://edu-mind-ai.onrender.com/docs` 
frontend http://127.0.0.1:8000/docs
---

### 🚀 Features
- **PDF Understanding:** Upload any textbook, notes, or research paper
- **Smart Chat:** Ask questions and get answers from your document
- **FastAPI Docs:** Interactive Swagger UI at `/docs`
- **CORS Ready:** Ready to connect to any frontend
- **Lightweight RAG:** Keyword-based context retrieval (upgradable to OpenAI/Gemini)

---

### 📁 Project StructureEdu-mind-AI/
├── backend/
│   ├── main.py              # FastAPI app with /upload-pdf and /chat
│   ├── requirements.txt     # Python dependencies
│   └── .env.example
├── .gitignore
└── README.mdjavascript
---

### 🔧 Tech Stack
- **Backend:** Python 3.11, FastAPI, Uvicorn
- **PDF Processing:** pypdf
- **Deployment:** Render.com
- **Future:** OpenAI API / Gemini for real LLM answers

---

### ⚡ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload-pdf` | Upload PDF and extract text |
| POST | `/chat` | Chat with uploaded document |
| GET | `/context` | Check if document is loaded |
| GET | `/docs` | Interactive API docs |

#### Example Usage:

**1. Upload PDF**
```bash
curl -X POST https://your-api.onrender.com/upload-pdf \
  -F "file=@your_notes.pdf"2. Chatbashcurl -X POST https://your-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize chapter 1"}'💻 Run Locallybash# Clone
git clone https://github.com/victormawira05-lgtm/Edu-mind-AI.git
cd Edu-mind-AI

# Create venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install
pip install -r backend/requirements.txt

# Run
uvicorn backend.main:app --reload --port 8000

# Open http://localhost:8000/docs☁️ Deployment on Render
Build Command: pip install -r backend/requirements.txtStart Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORTEnvironment Variables:
PYTHON_VERSION=3.11.9OPENAI_API_KEY=... (optional, for future upgrade)🧠 Roadmap
FastAPI backend deployedPDF upload & text extractionBasic chat over documentIntegrate OpenAI GPT-4o / Gemini for intelligent answersFrontend (React + Tailwind)User authentication & document historyVector DB (Pinecone/Chroma) for long PDFs👨‍💻 Author
Victor Mawira - Nairobi, KenyaBuilt with ❤️ for students who learn by questioning.
📄 License
MIT License - Free to use and improve.
EduMind AI: Don't just read — converse with your knowledge.javascript
