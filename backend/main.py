from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="EduMind AI",
    description="Your intelligent AI learning assistant",
    version="1.0.0"
)

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store PDF text in memory (use DB later)
pdf_context = {"text": ""}

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    source: str = "pdf_context"

@app.get("/")
def home():
    return {"message": "EduMind AI is live! Upload a PDF and start chatting."}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        pdf_context["text"] = text[:20000]  # Limit for now
        
        return {
            "filename": file.filename,
            "pages": len(reader.pages),
            "characters": len(text),
            "preview": text[:500] + "..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not pdf_context["text"]:
        return ChatResponse(
            answer="Please upload a PDF first using /upload-pdf, then I can answer questions from it!",
            source="system"
        )
    
    # Simple keyword search for now (replace with OpenAI / Gemini later)
    question = request.question.lower()
    context = pdf_context["text"]
    
    # Very basic RAG - find sentences containing question keywords
    sentences = context.split(".")
    keywords = question.split()
    relevant = [s for s in sentences if any(k in s.lower() for k in keywords)][:3]
    
    if relevant:
        answer = "Based on your document:\n\n" + ". ".join(relevant).strip() + "."
    else:
        answer = f"I read your document ({len(context)} chars), but I couldn't find a direct answer to '{request.question}'. Try asking with different keywords from the document."
    
    return ChatResponse(answer=answer, source="pdf_context")

@app.get("/context")
def get_context():
    return {"has_context": bool(pdf_context["text"]), "length": len(pdf_context["text"])}