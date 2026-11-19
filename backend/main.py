from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import random

app = FastAPI(title="EduMind AI", description="Turn PDFs into Personal Tutor - Quizzes, Flashcards, Summaries", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Fake DB for demo - replace with ChromaDB + Gemini later
DOCUMENTS = []

class AskRequest(BaseModel):
    question: str
    doc_id: str = "demo"

@app.get("/")
def root():
    return {"service": "EduMind AI", "docs": "/docs", "status": "live", "tagline": "Upload. Learn. Master."}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    content = await file.read()
    doc_id = f"DOC{random.randint(1000,9999)}"
    DOCUMENTS.append({"id": doc_id, "filename": file.filename, "size": len(content), "time": datetime.now().isoformat()})
    return {
        "status": "SUCCESS",
        "doc_id": doc_id,
        "filename": file.filename,
        "message": "File uploaded and embedded",
        "next_steps": ["/summarize", "/generate-quiz", "/ask"]
    }

@app.post("/summarize")
def summarize(doc_id: str = Form(...)):
    return {
        "doc_id": doc_id,
        "summary": "This chapter covers Photosynthesis. Key points: 1) Plants make food using sunlight 2) Needs CO2 + Water 3) Produces Oxygen. (Demo summary - connect Gemini here)",
        "key_points": ["Photosynthesis definition", "Chemical equation", "Importance"]
    }

@app.post("/generate-quiz")
def generate_quiz(doc_id: str = Form(...), num_questions: int = Form(5)):
    return {
        "doc_id": doc_id,
        "quiz": [
            {"q": "What is photosynthesis?", "options": ["Food making", "Respiration", "Digestion"], "answer": "Food making"},
            {"q": "What gas is produced?", "options": ["Oxygen", "CO2", "Nitrogen"], "answer": "Oxygen"},
            {"q": "Explain in Swahili: Mimea hutengeneza chakula vipi?", "options": [], "answer": "Kupitia mwangaza wa jua..."}
        ]
    }

@app.post("/ask")
def ask_tutor(req: AskRequest):
    return {
        "question": req.question,
        "answer": f"Great question about '{req.question}'! Based on YOUR document: (Demo) Photosynthesis happens in chloroplasts. Need real RAG? Connect Gemini API here. In Swahili: Hii hutokea kwenye kloroplast.",
        "cited_from": "Page 2, Paragraph 1 of your PDF"
    }

@app.get("/documents")
def list_docs():
    return {"count": len(DOCUMENTS), "documents": DOCUMENTS}
