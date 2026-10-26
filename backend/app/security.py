"""Password hashing, JWT creation/verification, and FastAPI auth dependency."""
from __future__ import annotations

import datetime
import logging
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

_ph = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


# ─── Password ────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return an Argon2 hash of the password."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the hashed password."""
    try:
        _ph.verify(hashed, plain)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ─── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str, role: str) -> str:
    """Create a signed JWT for the given user."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "email": email, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns the payload dict or None on failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ─── FastAPI dependency ───────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """
    FastAPI dependency that:
    - Returns None when AUTH_ENABLED=false (unauthenticated demo mode).
    - Validates the Bearer token and returns the payload when auth is enabled.
    - Raises 401 if the token is missing or invalid.
    """
    if not settings.AUTH_ENABLED:
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
