import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pypdf import PdfReader
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATE_FILE = os.path.join(TEMPLATE_DIR, "index.html")

app = FastAPI(
    title="EduMind AI",
    description="Your intelligent AI learning assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

document_context = {"text": "", "filename": ""}

@app.get("/", response_class=HTMLResponse)
async def home():
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <h1>Welcome to EduMind AI! 🎓</h1>
    <p>Status: Running successfully</p>
    <p><a href='/docs'>Go to API Docs</a> | <a href='/app'>Go to App UI</a></p>
    """

@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found in backend/templates/</h1>"

@app.get("/health")
async def health():
    return {"status": "healthy", "application": "EduMind AI"}

@app.get("/api/features")
async def features():
    return {
        "features": [
            "AI Learning Assistant",
            "Intelligent Quiz Generator",
            "Academic Performance Analysis",
            "Personalized Revision Plans"
        ]
    }

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global document_context
    content = await file.read()
    reader = PdfReader(io.BytesIO(content))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    document_context["text"] = text
    document_context["filename"] = file.filename
    return {
        "filename": file.filename,
        "pages": len(reader.pages),
        "characters": len(text),
        "preview": text[:500]
    }

@app.post("/chat")
async def chat(question: dict):
    q = question.get("question", "")
    context = document_context["text"][:3000] if document_context["text"] else "No document uploaded yet."
    return {
        "answer": f"Based on '{document_context['filename'] or 'no document'}': {context[:800]}...\n\nYour question was: {q}",
        "question": q
    }

@app.get("/context")
async def get_context():
    return {"loaded": bool(document_context["text"]), "filename": document_context["filename"]}