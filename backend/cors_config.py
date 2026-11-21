from __future__ import annotations

import os
from typing import List


def get_allowed_origins() -> List[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if origins:
        return origins
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
    if env in {"prod", "production"}:
        return []
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
