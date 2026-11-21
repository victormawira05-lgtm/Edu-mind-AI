from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: Optional[str] = None


def _decode_supabase_jwt(token: str) -> AuthenticatedUser:
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication verifier is not configured.",
        )
    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    user_id = payload.get("sub")
    if not user_id or not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
        )
    return AuthenticatedUser(user_id=user_id, email=payload.get("email"))


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_dev_user_id: Optional[str] = Header(default=None, alias="X-Dev-User-Id"),
) -> AuthenticatedUser:
    if (
        os.getenv("ALLOW_DEV_AUTH_BYPASS", "").lower() == "true"
        and x_dev_user_id
        and x_dev_user_id.strip()
    ):
        return AuthenticatedUser(user_id=x_dev_user_id.strip())

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty Bearer token.",
        )
    return _decode_supabase_jwt(token)


def verify_owner(resource_owner_id: str, current_user: AuthenticatedUser) -> None:
    if resource_owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
