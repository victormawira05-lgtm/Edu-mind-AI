
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="EduMind AI",
    description="Your intelligent AI learning assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    return {
        "message": "Welcome to EduMind AI!",
        "status": "Running successfully"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "application": "EduMind AI"
    }

@app.get("/api/features")
async def features():
    return {
        "features": [
            "AI Learning Assistant",
            "Intelligent Quiz Generator",
            "Academic Performance Analysis",
            "Personalized Revision Plans"
        ]
    }
