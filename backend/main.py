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

def ai_simplify(text, user_q):
    try:
        from google import genai
        gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not gem_key:
            return "No GEMINI_API_KEY found in Render Environment. Add it."
        client = genai.Client(api_key=gem_key)
        
        prompt = f"You are EduMind AI, friendly tutor. PDF: {DOC_NAME}. User asks: {user_q}. Text: {text[:4000]}. Give SUPER SIMPLE explanation with bullets, Kenyan example, step-by-step if math. ELI12 style."
        
        # Try models in order - newest first as Google suggests
        models_to_try = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
        
        last_error = ""
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return f"[{model_name}]\n\n" + response.text
            except Exception as e:
                last_error = str(e)
                if "404" not in str(e) and "not found" not in str(e).lower():
                    # If not a model-not-found error, break
                    return f"GEMINI ERROR with {model_name}: {e}"
                continue
        
        return f"All models failed. Last error: {last_error}\n\nFallback:\n" + offline_simplify(text, user_q)
        
    except Exception as e:
        return f"Setup error: {e}\n" + offline_simplify(text, user_q)

def offline_simplify(text, q):
    s = f"Simplified notes from {DOC_NAME}:\n"
    for l in text.split("\n")[:15]:
        if len(l.strip())>10:
            s += "- " + l[:220] + "\n"
    return s

@app.get("/")
def home():
    return FileResponse(HTML_FILE)

@app.get("/context")
def get_context():
    key_exists = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT), "has_key": key_exists}

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
    return {"status":"ok","filename":DOC_NAME,"pages":len(reader.pages),"chars":len(DOC_TEXT)}

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
            if len(relevant) > 3000: break
    ctx = relevant if relevant else DOC_TEXT[:3500]
    return {"answer": ai_simplify(ctx, q)}
