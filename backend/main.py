from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os, traceback
from pypdf import PdfReader

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "templates", "index.html")

DOC_TEXT = ""
DOC_NAME = ""
DOC_LINES = []
USE_AI = False
client = None
INIT_ERROR = ""

try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
        USE_AI = True
        INIT_ERROR = "AI ready"
    else:
        INIT_ERROR = "No API key found"
except Exception as e:
    INIT_ERROR = str(e)

def ai_simplify(text, user_q):
    if not USE_AI or not client:
        return f"OFFLINE MODE - Reason: {INIT_ERROR}"
    try:
        prompt = f"You are EduMind AI, a friendly tutor for students in Kenya. User uploaded {DOC_NAME}. User asks: '{user_q}'. Text from PDF: {text[:3500]}. Give a SUPER SIMPLE explanation: short bullets, simple English, real-life example from Kenya, step-by-step for math. If user asks simplify, do ELI12 style."
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=900)
        return resp.choices[0].message.content
    except Exception as e:
        return f"OPENAI ERROR: {str(e)}\n\nTrace: {traceback.format_exc()[:500]}\n\nFix: Check billing at platform.openai.com/account/billing, and key is valid."

def offline_simplify(text, q):
    s = f"Offline simplified notes from {DOC_NAME}:\n"
    for l in text.split("\n")[:15]:
        if len(l.strip())>10:
            s += "- " + l[:220] + "\n"
    return s

@app.get("/")
def home():
    return FileResponse(HTML_FILE)

@app.get("/context")
def get_context():
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT), "ai_enabled": USE_AI, "init_error": INIT_ERROR}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global DOC_TEXT, DOC_NAME, DOC_LINES
    reader = PdfReader(file.file)
    text = ""
    for p in reader.pages:
        t = p.extract_text()
        if t: text += t + "\n"
    DOC_TEXT = text
    DOC_LINES = [l for l in text.split("\n") if l.strip()]
    DOC_NAME = file.filename
    return {"status":"ok","filename":DOC_NAME,"pages":len(reader.pages),"chars":len(DOC_TEXT),"ai":USE_AI}

@app.post("/chat")
async def chat(data: dict):
    q = data.get("question","").strip()
    if not DOC_TEXT:
        return {"answer": "Please upload a PDF first."}
    q_words = [w for w in q.lower().split() if len(w)>3]
    relevant = ""
    for line in DOC_LINES:
        if any(w in line.lower() for w in q_words):
            relevant += line + "\n"
            if len(relevant) > 2000: break
    ctx = relevant if relevant else DOC_TEXT[:2500]
    ans = ai_simplify(ctx, q)
    return {"answer": ans}
