from fastapi import FastAPI, File, UploadFile, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pypdf import PdfReader

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Global memory
DOC_TEXT = ""
DOC_NAME = ""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/context")
def get_context():
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT)}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global DOC_TEXT, DOC_NAME
    try:
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages[:50]: # first 50 pages
            t = page.extract_text()
            if t:
                text += t + "\n"
        DOC_TEXT = text[:200000] # limit
        DOC_NAME = file.filename
        return {"status": "ok", "filename": DOC_NAME, "pages": len(reader.pages), "chars": len(DOC_TEXT)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/chat")
async def chat(data: dict):
    global DOC_TEXT
    q = data.get("question","").lower().strip()
    if not DOC_TEXT:
        return {"answer": "Please upload a PDF first."}
    if not q:
        return {"answer": "Ask something like: Summarize, explain chapter 2, etc."}
    
    # Simple smart search
    if "summar" in q:
        return {"answer": "SUMMARY of " + DOC_NAME + ":\n\n" + DOC_TEXT[:1500] + "...\n\n[Showing first 1500 chars. Ask specific section to get details]"}
    
    if "quiz" in q or "mcq" in q or "question" in q:
        return {"answer": "Here are 5 quick quiz questions from your notes:\n1. What is the main topic of this document?\n2. Define: " + DOC_TEXT.split()[0:10].__str__() + "\n3. List 3 key points from page 1.\n4. Explain with example from your PDF.\n5. What did you learn? (Open)"}

    # Keyword search
    lines = DOC_TEXT.split("\n")
    matches = [l for l in lines if any(word in l.lower() for word in q.split() if len(word)>3)][:8]
    if matches:
        return {"answer": "Found in your PDF:\n\n" + "\n---\n".join(matches) + "\n\nWant a simpler explanation? Ask 'Explain simply'"}
    else:
        # fallback: first 1000 chars
        return {"answer": "I searched '" + q + "' but didn't find exact match. Here's start of your doc:\n\n" + DOC_TEXT[:1200]}
