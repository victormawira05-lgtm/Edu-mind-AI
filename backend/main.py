import os, io
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import PyPDF2
from google import genai as google_genai

app = FastAPI(title="EduMind AI", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    client = google_genai.Client(api_key=GEMINI_KEY)
    MODEL_NAME = "gemini-3.8-flash"
else:
    client = None
    MODEL_NAME = None

DOC_STORE = {}

def extract_text_from_pdf(file_bytes):
    pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf.pages[:10]:
        text += (page.extract_text() or "") + "\n"
    return text[:15000]

def gemini_generate(prompt: str):
    if not client:
        raise Exception("GEMINI_API_KEY not set on Render")
    resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return resp.text

HTML_PAGE = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width">
<title>EduMind AI</title>
<style>
body{font-family:system-ui;padding:20px;max-width:600px;margin:auto;background:#f8fafc}
.card{background:white;padding:20px;border-radius:16px;box-shadow:0 4px 12px #0001;margin:15px 0}
button{background:#4f46e5;color:white;border:0;padding:12px 20px;border-radius:10px;width:100%;font-weight:bold}
input{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;margin:8px 0;box-sizing:border-box}
pre{white-space:pre-wrap;background:#f1f5f9;padding:12px;border-radius:10px}
</style></head>
<body>
<h1>🧠 EduMind AI</h1><p>Upload. Learn. Master. LIVE</p>
<div class="card"><h3>1. Upload PDF</h3><input type="file" id="pdf" accept=".pdf"><button onclick="upload()">Upload & Summarize</button><pre id="uploadResult"></pre></div>
<div class="card"><h3>2. Ask Question</h3><input id="docId" placeholder="Doc ID"><input id="question" placeholder="What is photosynthesis?"><button onclick="ask()">Ask EduMind</button><pre id="askResult"></pre></div>
<div class="card"><h3>3. Generate Quiz</h3><button onclick="quiz()">Create Quiz</button><pre id="quizResult"></pre></div>
<script>
async function upload(){
 const f=document.getElementById('pdf').files[0]; if(!f) return alert("Choose PDF");
 const fd=new FormData(); fd.append("file",f);
 document.getElementById('uploadResult').innerText="AI reading...";
 const r=await fetch("/upload",{method:"POST",body:fd}); const j=await r.json();
 document.getElementById('docId').value=j.doc_id||""; document.getElementById('uploadResult').innerText="ID: "+j.doc_id+"\\n\\n"+(j.summary||JSON.stringify(j,null,2));
}
async function ask(){
 const q=document.getElementById('question').value, d=document.getElementById('docId').value;
 if(!q||!d) return alert("Need ID+Q");
 const fd=new FormData(); fd.append("question",q); fd.append("doc_id",d);
 document.getElementById('askResult').innerText="Thinking...";
 const r=await fetch("/ask",{method:"POST",body:fd}); const j=await r.json();
 document.getElementById('askResult').innerText=j.answer||JSON.stringify(j,null,2);
}
async function quiz(){
 const d=document.getElementById('docId').value; if(!d) return alert("Upload first");
 const fd=new FormData(); fd.append("doc_id",d); fd.append("num","3");
 document.getElementById('quizResult').innerText="Generating...";
 const r=await fetch("/generate-quiz",{method:"POST",body:fd}); const j=await r.json();
 document.getElementById('quizResult').innerText=j.quiz||JSON.stringify(j,null,2);
}
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def root(): return HTML_PAGE

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        data = await file.read()
        text = extract_text_from_pdf(data)
        if len(text)<50: raise HTTPException(400, "PDF too small/scanned")
        doc_id = f"DOC{int(datetime.now().timestamp())}"
        DOC_STORE[doc_id]=text
        summary = gemini_generate(f"Summarize in 5 bullets simple English + 1 line Swahili:\\n{text[:8000]}")
        return {"doc_id": doc_id, "summary": summary, "chars": len(text)}
    except Exception as e: raise HTTPException(500, str(e))

@app.post("/ask")
async def ask_q(question: str = Form(...), doc_id: str = Form(...)):
    if doc_id not in DOC_STORE: raise HTTPException(404, "Upload first")
    ans = gemini_generate(f"Answer ONLY from notes. Notes:{DOC_STORE[doc_id][:10000]}\\nQ:{question}\\nEnglish+Swahili:")
    return {"answer": ans}

@app.post("/generate-quiz")
async def gen_quiz(doc_id: str = Form(...), num: int = Form(3)):
    if doc_id not in DOC_STORE: raise HTTPException(404, "Upload first")
    q = gemini_generate(f"Create {num} MCQs JSON [{{q,options[4],answer}}]:\\n{DOC_STORE[doc_id][:8000]}")
    return {"quiz": q}
