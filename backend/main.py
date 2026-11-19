from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pypdf import PdfReader

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "templates", "index.html")

DOC_TEXT = ""
DOC_NAME = ""
DOC_LINES = []
USE_AI = False
AI_TYPE = ""

try:
    import google.generativeai as genai
    gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gem_key:
        genai.configure(api_key=gem_key)
        USE_AI = True
        AI_TYPE = "Gemini FREE"
        print("Gemini ready")
    else:
        AI_TYPE = "No GEMINI_API_KEY - offline"
except Exception as e:
    AI_TYPE = str(e)

def ai_simplify(text, user_q):
    if not USE_AI:
        return f"Offline mode - {AI_TYPE}\n" + offline_simplify(text, user_q)
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"You are EduMind AI tutor for Kenyan students. User uploaded {DOC_NAME}. User asks: {user_q}. PDF text: {text[:4000]}. Give SUPER SIMPLE explanation: bullets, simple English, Kenyan example, step-by-step for math. If user says simplify, do ELI12."
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"GEMINI ERROR: {e}\n\nOffline fallback:\n" + offline_simplify(text, user_q)

def offline_simplify(text, q):
    s = f"Simplified notes from {DOC_NAME}:\n"
    for l in text.split("\n")[:12]:
        if len(l.strip())>10:
            s += "- " + l[:220] + "\n"
    s += "\nExample: 8 AC out of 28 total = 2/7 chance"
    return s

@app.get("/")
def home():
    return FileResponse(HTML_FILE)

@app.get("/context")
def get_context():
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT), "ai_enabled": USE_AI, "ai_type": AI_TYPE}

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
        return {"answer": "Please upload PDF first."}
    q_words = [w for w in q.lower().split() if len(w)>3]
    relevant = ""
    for line in DOC_LINES:
        if any(w in line.lower() for w in q_words):
            relevant += line + "\n"
            if len(relevant) > 2500: break
    ctx = relevant if relevant else DOC_TEXT[:3000]
    return {"answer": ai_simplify(ctx, q)}
