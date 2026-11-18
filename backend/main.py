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

@app.get("/")
def home():
    return FileResponse(HTML_FILE)

@app.get("/context")
def get_context():
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT)}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global DOC_TEXT, DOC_NAME
    try:
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages[:50]:
            t = page.extract_text()
            if t:
                text += t + "\n"
        DOC_TEXT = text[:200000]
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
        return {"answer": "Ask something like: Summarize..."}
    if "summar" in q:
        return {"answer": "SUMMARY of "+DOC_NAME+":\n\n"+DOC_TEXT[:1500]}
    lines = DOC_TEXT.split("\n")
    matches = [l for l in lines if any(w in l.lower() for w in q.split() if len(w)>3)][:8]
    if matches:
        return {"answer": "Found in PDF:\n\n" + "\n---\n".join(matches)}
    return {"answer": "I searched '"+q+"' - here's start:\n\n"+DOC_TEXT[:1200]}
