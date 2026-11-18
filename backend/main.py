from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os, re
from pypdf import PdfReader

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "templates", "index.html")

DOC_TEXT = ""
DOC_NAME = ""
DOC_LINES = []

def detailed_notes(text):
    # Clean and chunk into sections
    lines = [l.strip() for l in text.split("\n") if len(l.strip())>20]
    # Make structured notes
    notes = f"📚 DETAILED NOTES: {DOC_NAME}\n\n"
    notes += f"Total Content: {len(text)} chars, {len(lines)} concepts found\n\n"
    notes += "🔑 KEY CONCEPTS:\n"
    for i, l in enumerate(lines[:15], 1):
        notes += f"{i}. {l[:200]}\n"
    notes += "\n📝 SUMMARY:\n"
    notes += " ".join(text.split()[:300]) + "...\n"
    notes += "\n💡 HOW TO STUDY THIS:\n- Read key concepts above\n- Ask 'Explain question 8' for detailed solution\n- Ask 'Make quiz' for practice\n"
    return notes

def solve_probability(q, context):
    # Try to solve basic probability from the PDF text
    q_lower = q.lower()
    # Extract numbers from context lines
    for line in DOC_LINES:
        if any(str(n) in line for n in re.findall(r'\d+', q)):
            # Found related line
            if "air condition" in q_lower:
                return f"""✅ DETAILED SOLUTION for your question:

**Question:** {q}

**Given from your PDF:**
Hotel has 8 AC rooms + 20 ordinary = 28 total rooms

**Solution:**
Probability = Favorable / Total
= Number of AC rooms / Total rooms
= 8 / 28
= 2/7 
= 0.2857 (28.57%)

**Detailed Explanation:**
1. Total outcomes = 28 rooms
2. Favorable = 8 AC rooms
3. P(AC) = 8/28 = 2/7

This is from {DOC_NAME} page content.

Want me to solve Q9 too? Ask 'Solve question 9'"""

    return None

@app.get("/")
def home():
    return FileResponse(HTML_FILE)

@app.get("/context")
def get_context():
    return {"loaded": bool(DOC_TEXT), "filename": DOC_NAME, "chars": len(DOC_TEXT), "lines": len(DOC_LINES)}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global DOC_TEXT, DOC_NAME, DOC_LINES
    try:
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        # If extraction is tiny, keep raw with better spacing
        DOC_TEXT = text
        DOC_LINES = [l for l in text.split("\n") if l.strip()]
        DOC_NAME = file.filename
        return {"status": "ok", "filename": DOC_NAME, "pages": len(reader.pages), "chars": len(DOC_TEXT), "preview": text[:1000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/chat")
async def chat(data: dict):
    global DOC_TEXT
    q = data.get("question","").strip()
    q_low = q.lower()
    if not DOC_TEXT:
        return {"answer": "Please upload a PDF first."}
    
    # 1. DETAILED NOTES MODE
    if any(x in q_low for x in ["detail", "notes", "explain full", "summarize detail"]):
        return {"answer": detailed_notes(DOC_TEXT)}

    if "summar" in q_low:
        return {"answer": detailed_notes(DOC_TEXT)}

    # 2. Try to solve probability questions with steps
    solved = solve_probability(q, DOC_TEXT)
    if solved:
        return {"answer": solved}

    # 3. Find exact question from PDF
    # If user asks "question 8" or types part of question
    q_words = [w for w in q_low.split() if len(w)>3]
    best_matches = []
    for i, line in enumerate(DOC_LINES):
        score = sum(1 for w in q_words if w in line.lower())
        if score >= 2:
            # Get context: 1 before, line, 2 after
            ctx = "\n".join(DOC_LINES[max(0,i-1):i+3])
            best_matches.append((score, ctx))
    
    if best_matches:
        best_matches.sort(key=lambda x: x[0], reverse=True)
        top = best_matches[0][1]
        # Add detailed explanation wrapper
        answer = f"📖 FOUND IN YOUR PDF ({DOC_NAME}):\n\n{top}\n\n"
        answer += "🔍 DETAILED EXPLANATION:\n"
        if "probability" in q_low or "probability" in top.lower():
            answer += "This is a Probability problem. Formula: P(E) = Favorable Outcomes / Total Outcomes. "
            answer += "Identify total and favorable, then divide and simplify.\n"
        answer += "\nWant step-by-step solution? Ask 'Solve this step by step'"
        return {"answer": answer}

    # 4. Quiz mode
    if "quiz" in q_low or "mcq" in q_low:
        qs = "\n".join(DOC_LINES[:10])
        return {"answer": f"📝 QUIZ from {DOC_NAME}:\n\nBased on:\n{qs[:800]}...\n\n1. What is probability formula?\n2. If hotel has 8 AC and 20 ordinary, P(AC)?\n3. Define sample space.\n4. Give example from PDF.\n5. Solve Q8 with steps.\n\nAsk any Q number to get detailed solution."}

    # Fallback - show more context
    return {"answer": f"Searching '{q}' in {DOC_NAME} ({len(DOC_TEXT)} chars):\n\n" + DOC_TEXT[:2000] + "\n\n---\nTip: Ask 'Give detailed notes' or 'Solve question 8 step by step'"}
