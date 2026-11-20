# backend/auth.py
import os
from fastapi import HTTPException, Header
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set in .env")

# Service client - bypasses RLS, we enforce user_id manually
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1]
    try:
        # Validates JWT with Supabase Auth
        res = supabase.auth.get_user(token)
        user = res.user
        if not user:
            raise HTTPException(401, "Invalid token")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f"Invalid token: {e}")
