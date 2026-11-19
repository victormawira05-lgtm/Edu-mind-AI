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
client = None
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
        USE_AI = True
        print("AI ON")
except Exception as e:
    print(e)

def ai_simplify(text, user_q):
    if not USE_AI or not client:
        return None
    try:
        prompt = f"You are EduMind AI tutor. PDF: {DOC_NAME}. User asks: {user_q}. Text: {text[:4000]}. Give SUPER SIMPLE explanation with bullets, real-life analogy, step-by-step if math. Format: SIMPLE EXPLANATION, Example, 3 Points to Remember."
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=800)
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"

def offline_simplify(text, q):
    s = f"SIMPLIFIED from {DOC_NAME}:\n\n"
    for l in text.split("\n")[:10]:
        if len(l.strip())>10:
            s+=f"• {l[:200]}\n"
    s+="\nExample: 8 AC / 28 total = 2/7 chance\nAdd OPENAI_API_KEY for better AI."
    return s

@app.get("/")
def home():
    return FileResponse(HTML_FILE)

@app.get("/context")
def get_context():
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT), "ai_enabled": USE_AI}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global DOC_TEXT, DOC_NAME, DOC_LINES
    reader = PdfReader(file.file)
    text=""
    for p in reader.pages:
        t=p.extract_text()
        if t: text+=t+"\n"
    DOC_TEXT=text
    DOC_LINES=[l for l in text.split("\n") if l.strip()]
    DOC_NAME=file.filename
    return {"status":"ok","filename":DOC_NAME,"pages":len(reader.pages),"chars":len(DOC_TEXT),"ai":USE_AI}

@app.post("/chat")
async def chat(data: dict):
    q=data.get("question","").strip()
    if not DOC_TEXT:
        return {"answer":"Please upload PDF first."}
    q_low=q.lower()
    q_words=[w for w in q_low.split() if len(w)>3]
    relevant=""
    for line in DOC_LINES:
        if any(w in line.lower() for w in q_words):
            relevant+=line+"\n"
            if len(relevant)>1500: break
    ctx=relevant if relevant else DOC_TEXT[:2000]
    if USE_AI:
        ai=ai_simplify(ctx,q)
        if ai: return {"answer":ai+"\n\n---\nPowered by GPT-4o-mini"}
    return {"answer": offline_simplify(ctx,q)}
