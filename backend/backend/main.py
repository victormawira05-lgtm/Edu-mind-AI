import os
import json
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import google.generativeai as genai

# ===== CONFIG - SUPPORTS BOTH OLD AND NEW ENV NAMES =====
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_PROJECT_URL") or ""
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON") or ""
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or ""
ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"

print(f"STARTUP: SUPABASE_URL set = {bool(SUPABASE_URL)}")
print(f"STARTUP: SUPABASE_KEY set = {bool(SUPABASE_KEY)}")
print(f"STARTUP: GEMINI_API_KEY set = {bool(GEMINI_API_KEY)}")
print(f"STARTUP: ALLOW_DEV_AUTH = {ALLOW_DEV_AUTH}")

# Only create client if we have values - prevents crash
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("STARTUP: Supabase connected ✅")
    except Exception as e:
        print(f"STARTUP: Supabase failed: {e}")
        supabase = None
else:
    print("STARTUP: ⚠️ Supabase NOT connected - Add SUPABASE_URL + SUPABASE_ANON_KEY in Render")

# Gemini - only configure if key exists
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None
    print("STARTUP: ⚠️ GEMINI_API_KEY missing")

app = FastAPI(title="Edu-mind AI")

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== AUTH HELPER =====
def check_auth(authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    if ALLOW_DEV_AUTH and authorization == "Bearer dev":
        return {"user_id": x_dev_user_id or "vic-demo", "mode": "dev"}
    if authorization and authorization.startswith("Bearer eyJ"):
        return {"user_id": "supabase-user", "mode": "supabase"}
    if ALLOW_DEV_AUTH:
        return {"user_id": "vic-demo", "mode": "dev"}
    raise HTTPException(status_code=401, detail="Missing Bearer authentication token")

def require_supabase():
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase not connected. Add SUPABASE_URL + SUPABASE_ANON_KEY in Render Env Vars and redeploy.")
    return supabase

def require_gemini():
    if model is None:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY missing in Render Env Vars.")
    return model

# ===== MODELS =====
class AskRequest(BaseModel):
    question: str
    mode: str = "notes"  # "notes" or "general"

class SummarizeRequest(BaseModel):
    pass

# ===== HELPER: GET PDF TEXT =====
def get_unit_context(unit_code: str, limit: int = 25000):
    if supabase is None:
        return ""
    try:
        res = supabase.table("documents").select("text_content").eq("unit_code", unit_code).execute()
        context = "\n\n".join([d["text_content"] or "" for d in res.data])
        return context[:limit]
    except Exception as e:
        print(f"get_unit_context error: {e}")
        return ""

# ===== HEALTH =====
@app.get("/")
def health():
    return {
        "status": "Edu-mind AI Live",
        "dev_auth": ALLOW_DEV_AUTH,
        "supabase_connected": supabase is not None,
        "gemini_connected": model is not None,
        "missing": [
            k for k, v in {
                "SUPABASE_URL": SUPABASE_URL,
                "SUPABASE_ANON_KEY": SUPABASE_KEY,
                "GEMINI_API_KEY": GEMINI_API_KEY
            }.items() if not v
        ]
    }

@app.get("/context")
def context_check():
    return {"message": "context endpoint working", "supabase": supabase is not None}

# ===== 1. UPLOAD PDF =====
@app.post("/api/units/{unit_code}/documents")
async def upload_document(
    unit_code: str,
    file: UploadFile = File(...),
    category: str = Form("lecture_notes"),
    authorization: str = Header(None),
    x_dev_user_id: str = Header(None)
):
    check_auth(authorization, x_dev_user_id)
    db = require_supabase()

    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    pages = len(doc)
    doc.close()

    db.table("documents").insert({
        "unit_code": unit_code,
        "filename": file.filename,
        "category": category,
        "text_content": text
    }).execute()

    return {"message": "Uploaded successfully", "filename": file.filename, "pages": pages, "chars": len(text)}

# ===== 2. LIST PDFs =====
@app.get("/api/units/{unit_code}/documents")
async def list_documents(unit_code: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    db = require_supabase()
    res = db.table("documents").select("id,filename,category,created_at").eq("unit_code", unit_code).execute()
    return res.data

# ===== 3. ASK - HYBRID: NOTES + GENERAL AI (BOTH KEPT) =====
@app.post("/api/units/{unit_code}/ask")
async def ask_hybrid(unit_code: str, body: AskRequest, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    ai = require_gemini()

    if body.mode == "notes":
        context = get_unit_context(unit_code)
        if not context:
            return {"answer": "No lecture notes uploaded yet for this unit. Please upload a PDF first, or use Ask AI Online.", "source": "notes"}
        prompt = f"""
        You are a tutor for {unit_code}.
        Answer ONLY using these lecture notes. If not in notes, say "Not in your notes, but here is general explanation" then give general answer.
        Give step-by-step, simple English, exam-style answer.
        LECTURE NOTES: {context}
        QUESTION: {body.question}
        """
    else:
        # GENERAL AI SEARCH - OLD FEATURE KEPT
        prompt = f"""
        You are an expert tutor for {unit_code}.
        Answer in detail, step-by-step, with examples and formulas.
        QUESTION: {body.question}
        """

    resp = ai.generate_content(prompt)
    return {"answer": resp.text, "source": body.mode}

# ===== 4. SUMMARIZE FROM PDF =====
@app.post("/api/units/{unit_code}/summarize")
async def summarize_pdf(unit_code: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    ai = require_gemini()
    context = get_unit_context(unit_code)
    if not context:
        return {"summary": "No notes uploaded yet. Upload a PDF first."}
    prompt = f"""
    Summarize these lecture notes for exam revision.
    Format: 1) 10 Key Points 2) Key Formulas 3) 3 Likely Exam Questions
    Notes: {context}
    """
    resp = ai.generate_content(prompt)
    return {"summary": resp.text}

# ===== 5. QUIZ FROM PDF =====
@app.post("/api/units/{unit_code}/quiz")
async def quiz_from_pdf(unit_code: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    ai = require_gemini()
    context = get_unit_context(unit_code)
    if not context:
        return {"quiz": []}
    prompt = f"""
    From these notes, create 5 MCQs.
    Return ONLY valid JSON: [{{"question": "...", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "..."}}]
    Notes: {context}
    """
    resp = ai.generate_content(prompt)
    text = resp.text.replace("```json", "").replace("```", "").strip()
    try:
        quiz = json.loads(text)
    except:
        quiz = []
    return {"quiz": quiz}

# ===== 6. DELETE PDF =====
@app.delete("/api/units/{unit_code}/documents/{doc_id}")
async def delete_doc(unit_code: str, doc_id: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    db = require_supabase()
    db.table("documents").delete().eq("id", doc_id).execute()
    return {"message": "Deleted"}
