import os
import io
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import PyPDF2
import google.generativeai as genai

app = FastAPI(title="EduMind AI", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Setup Gemini
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

DOC_STORE = {}

def extract_text_from_pdf(file_bytes):
    pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf.pages[:10]:
        text += (page.extract_text() or "") + "\n"
    return text[:15000]

# ---- Frontend files ----
# Create static folder if not exists
os.makedirs("backend/static", exist_ok=True)
if os.path.exists("backend/static"):
    try:
        app.mount("/static", StaticFiles(directory="backend/static"), name="static")
    except:
        pass

@app.get("/")
def root():
    # If frontend exists, show it, else show API status
    index_path = "backend/static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"service": "EduMind AI", "status": "live", "ai": "Gemini connected" if model else "Add GEMINI_API_KEY", "tagline": "Upload. Learn. Master.", "frontend": "Create backend/static/index.html to see UI"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not model:
        raise HTTPException(500, "GEMINI_API_KEY not set on Render - Add it in Environment")
    try:
        data = await file.read()
        text = extract_text_from_pdf(data)
        if len(text) < 50:
            raise HTTPException(400, "PDF text too small or scanned image - try text PDF")
        
        doc_id = f"DOC{int(datetime.now().timestamp())}"
        DOC_STORE[doc_id] = text
        
        prompt = f"Summarize these study notes in 5 bullet points, simple English + 1 line Swahili translation:\n\n{text[:8000]}"
        summary = model.generate_content(prompt).text
        
        return {"doc_id": doc_id, "filename": file.filename, "chars": len(text), "summary": summary}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/ask")
async def ask(question: str = Form(...), doc_id: str = Form(...)):
    if doc_id not in DOC_STORE:
        raise HTTPException(404, "Upload document first")
    if not model:
        raise HTTPException(500, "No API key")
    
    context = DOC_STORE[doc_id][:10000]
    prompt = f"You are EduMind tutor. Answer ONLY from these notes. If answer not in notes, say 'Not in your notes'. Notes:\n{context}\n\nQuestion: {question}\nAnswer in clear English, then Swahili if needed."
    ans = model.generate_content(prompt).text
    return {"answer": ans, "doc_id": doc_id}

@app.post("/generate-quiz")
async def quiz(doc_id: str = Form(...), num: int = Form(3)):
    if doc_id not in DOC_STORE:
        raise HTTPException(404, "Upload first")
    context = DOC_STORE[doc_id][:8000]
    prompt = f"Create {num} multiple choice quizzes from these notes. Format JSON like [{{q, options[4], answer}}]:\n{context}"
    res = model.generate_content(prompt).text
    return {"doc_id": doc_id, "quiz": res}

@app.get("/docs-store")
def list_docs():
    return {"count": len(DOC_STORE), "ids": list(DOC_STORE.keys())}
