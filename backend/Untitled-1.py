from pydantic import BaseModel
from fastapi import HTTPException
from ai_engine import ask_edumind
import httpx
class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat")
async def chat(request: ChatRequest):

    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    try:
        answer = await ask_edumind(request.question)

        return {
            "question": request.question,
            "answer": answer,
            "model": "NVIDIA Nemotron via Nebius"
        }

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Nebius API error: HTTP {error.response.status_code}"
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to Nebius."
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )