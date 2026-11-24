import os
import json
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import google.generativeai as genai

# ===== CONFIG =====
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

app = FastAPI(title="Edu-mind AI")

# ===== CORS - ALLOW YOUR FRONTEND =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== AUTH HELPER - KEEPS DEV + REAL LOGIN WORKING =====
def check_auth(authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    # Demo mode: allow Bearer dev
    if ALLOW_DEV_AUTH and authorization == "Bearer dev":
        return {"user_id": x_dev_user_id or "vic-demo", "mode": "dev"}
    # Real Supabase token
    if authorization and authorization.startswith("Bearer eyJ"):
        return {"user_id": "supabase-user", "mode": "supabase"}
    # If ALLOW_DEV_AUTH is true, also allow no auth for testing
    if ALLOW_DEV_AUTH:
        return {"user_id": "vic-demo", "mode": "dev"}
    raise HTTPException(status_code=401, detail="Missing Bearer authentication token")

# ===== MODELS =====
class AskRequest(BaseModel):
    question: str
    mode: str = "notes"  # "notes" or "general"

# ===== HELPER: GET PDF TEXT =====
def get_unit_context(unit_code: str, limit: int = 25000):
    res = supabase.table("documents").select("text_content").eq("unit_code", unit_code).execute()
    context = "\n\n".join([d["text_content"] or "" for d in res.data])
    return context[:limit]

@app.get("/")
def health():
    return {"status": "Edu-mind AI Live", "dev_auth": ALLOW_DEV_AUTH}

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
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    pages = len(doc)
    doc.close()

    supabase.table("documents").insert({
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
    res = supabase.table("documents").select("id,filename,category,created_at").eq("unit_code", unit_code).execute()
    return res.data

# ===== 3. ASK - HYBRID: NOTES + GENERAL AI (BOTH KEPT) =====
@app.post("/api/units/{unit_code}/ask")
async def ask_hybrid(unit_code: str, body: AskRequest, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)

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
        # GENERAL AI SEARCH - YOUR OLD FEATURE
        prompt = f"""
        You are an expert tutor for {unit_code}.
        Answer in detail, step-by-step, with examples and formulas.
        QUESTION: {body.question}
        """

    resp = model.generate_content(prompt)
    return {"answer": resp.text, "source": body.mode}

# ===== 4. SUMMARIZE FROM PDF =====
@app.post("/api/units/{unit_code}/summarize")
async def summarize_pdf(unit_code: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    context = get_unit_context(unit_code)
    if not context:
        return {"summary": "No notes uploaded yet. Upload a PDF first."}
    prompt = f"""
    Summarize these lecture notes for exam revision.
    Format: 1) 10 Key Points 2) Key Formulas 3) 3 Likely Exam Questions
    Notes: {context}
    """
    resp = model.generate_content(prompt)
    return {"summary": resp.text}

# ===== 5. QUIZ FROM PDF =====
@app.post("/api/units/{unit_code}/quiz")
async def quiz_from_pdf(unit_code: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    context = get_unit_context(unit_code)
    if not context:
        return {"quiz": []}
    prompt = f"""
    From these notes, create 5 MCQs.
    Return ONLY valid JSON: [{{"question": "...", "options": ["A","B","C","D"], "correct_index": 0, "explanation": "..."}}]
    Notes: {context}
    """
    resp = model.generate_content(prompt)
    text = resp.text.replace("```json", "").replace("```", "").strip()
    try:
        quiz = json.loads(text)
    except:
        quiz = []
    return {"quiz": quiz}

# ===== 6. DELETE PDF (optional) =====
@app.delete("/api/units/{unit_code}/documents/{doc_id}")
async def delete_doc(unit_code: str, doc_id: str, authorization: str = Header(None), x_dev_user_id: str = Header(None)):
    check_auth(authorization, x_dev_user_id)
    supabase.table("documents").delete().eq("id", doc_id).execute()
    return {"message": "Deleted"}
