ai_engine.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEBIUS_API_KEY")
BASE_URL = os.getenv("NEBIUS_BASE_URL")
MODEL = os.getenv("NEBIUS_MODEL")


async def ask_edumind(question: str):

    if not API_KEY or not BASE_URL or not MODEL:
        raise RuntimeError("Nebius configuration is incomplete.")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are EduMind AI, an intelligent educational "
                    "assistant. Explain difficult concepts simply, "
                    "give practical examples and guide students "
                    "step by step."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.5,
        "max_tokens": 1000
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{BASE_URL.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]
