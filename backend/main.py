# backend/main.py
import os, io, uuid
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import PyPDF2
from google import genai as google_genai

from backend.auth import supabase, get_current_user

app = FastAPI(title="EduMind AI", version="2.1")

# Tightened CORS - Phase 1
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = google_genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

MODEL_LIST = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemma-3-27b-it",
]

def extract_text_from_pdf(file_bytes):
    pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf.pages[:10]:
        text += (page.extract_text() or "") + "\n"
    return text[:15000]

def gemini_generate(prompt: str):
    if not client:
        raise Exception("GEMINI_API_KEY not set")
    last_err = None
    for model_id in MODEL_LIST:
        try:
            resp = client.models.generate_content(model=model_id, contents=prompt)
            print(f"Used model: {model_id}")
            return resp.text
        except Exception as e:
            print(f"Fail {model_id}: {e}")
            last_err = e
            continue
    raise HTTPException(500, f"All models failed. Last error: {last_err}")

def chunk_text(text: str, size=3000):
    return [text[i:i+size] for i in range(0, len(text), size)]

HTML_PAGE = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width">
<title>EduMind AI - Phase 1</title>
<style>body{font-family:system-ui;padding:20px;max-width:600px;margin:auto;background:#f8fafc}input,button{width:100%;padding:10px;margin:6px 0}button{background:#2563eb;color:white;border:0;border-radius:8px}</style>
</head><body>
<h2>EduMind AI - Login Required</h2>
<p>1. Get token from Supabase Auth (use Supabase Dashboard > Authentication > Add User, then login via API) or paste JWT below.</p>
<input id="token" placeholder="Paste Supabase JWT Bearer token">
<input id="pdf" type="file" accept=".pdf">
<button onclick="upload()">Upload + Summarize</button>
<pre id="out"></pre>
<input id="docId" placeholder="Document UUID">
<input id="question" placeholder="What is photosynthesis?">
<button onclick="ask()">Ask</button>
<button onclick="quiz()">Quiz (5)</button>
<script>
async function upload(){
  const token=document.getElementById('token').value;
  const f=document.getElementById('pdf').files[0];
  const fd=new FormData(); fd.append('file',f);
  const r=await fetch('/upload',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd});
  document.getElementById('out').innerText=await r.text();
}
async function ask(){
  const token=document.getElementById('token').value;
  const fd=new FormData(); fd.append('doc_id',document.getElementById('docId').value); fd.append('question',document.getElementById('question').value);
  const r=await fetch('/ask',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd});
  document.getElementById('out').innerText=await r.text();
}
async function quiz(){
  const token=document.getElementById('token').value;
  const fd=new FormData(); fd.append('doc_id',document.getElementById('docId').value); fd.append('num',5);
  const r=await fetch('/quiz',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd});
  document.getElementById('out').innerText=await r.text();
}
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE

@app.post("/upload")
async def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    user_id = user.id
    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        raise HTTPException(400, "No text extracted from PDF")

    doc_id = str(uuid.uuid4())
    storage_path = f"{user_id}/{doc_id}.pdf"

    # 1. Upload to Storage (private bucket, user_id/ folder)
    supabase.storage.from_("pdfs").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"}
    )

    # 2. Summarize
    summary = gemini_generate(f"Summarize in 5 bullets simple English + 1 line Swahili:\n{text[:8000]}")

    # 3. Save to DB
    supabase.table("documents").insert({
        "id": doc_id, "user_id": user_id,
        "title": file.filename, "file_path": storage_path,
        "summary": summary
    }).execute()

    # 4. Save chunks
    chunks = [{"document_id": doc_id, "user_id": user_id, "content": c, "chunk_index": i}
              for i, c in enumerate(chunk_text(text))]
    supabase.table("chunks").insert(chunks).execute()

    return {"doc_id": doc_id, "title": file.filename, "summary": summary}

@app.post("/ask")
async def ask(doc_id: str = Form(...), question: str = Form(...), user=Depends(get_current_user)):
    # Only own doc
    doc = supabase.table("documents").select("*").eq("id", doc_id).eq("user_id", user.id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Doc not found or not yours")
    chunks = supabase.table("chunks").select("content").eq("document_id", doc_id).eq("user_id", user.id).order("chunk_index").execute()
    context = "\n".join([c["content"] for c in chunks.data])[:10000]
    ans = gemini_generate(f"Answer ONLY from notes. Notes:{context}\nQ:{question}\nEnglish + 1 line Swahili:")
    return {"answer": ans}

@app.post("/quiz")
async def quiz(doc_id: str = Form(...), num: int = Form(5), user=Depends(get_current_user)):
    doc = supabase.table("documents").select("*").eq("id", doc_id).eq("user_id", user.id).single().execute()
    if not doc.data:
        raise HTTPException(404, "Doc not found or not yours")
    chunks = supabase.table("chunks").select("content").eq("document_id", doc_id).eq("user_id", user.id).order("chunk_index").execute()
    context = "\n".join([c["content"] for c in chunks.data])[:8000]
    q = gemini_generate(f"Create {num} MCQs JSON [{{q,options[4],answer}}]:\n{context}")
    return {"quiz": q}

@app.get("/my-docs")
async def my_docs(user=Depends(get_current_user)):
    res = supabase.table("documents").select("id,title,summary,created_at").eq("user_id", user.id).order("created_at", desc=True).execute()
    return res.data
