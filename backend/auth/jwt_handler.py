"""
backend/auth/jwt_handler.py
----------------------------
RS256 JWT authentication with:
  - Access tokens (15 min)
  - Refresh tokens (7 days, httpOnly cookie)
  - Token blacklist for logout
  - Role claims embedded in JWT payload

Key generation (run once):
  openssl genrsa -out backend/keys/private.pem 2048
  openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem
"""

import os
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings

# ── Password hashing (bcrypt direct — avoids passlib/bcrypt version conflicts) ───────
_bcrypt_rounds = 12

def hash_password(password: str) -> str:
    """Hash password using bcrypt directly."""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_bcrypt_rounds)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── Load RSA keys ─────────────────────────────────────────────────────────────
def _load_key(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(
            f"JWT key not found at {path}. "
            "Generate with:\n"
            "  openssl genrsa -out backend/keys/private.pem 2048\n"
            "  openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem"
        )
    return p.read_text()

try:
    _PRIVATE_KEY = _load_key(settings.JWT_PRIVATE_KEY_PATH)
    _PUBLIC_KEY  = _load_key(settings.JWT_PUBLIC_KEY_PATH)
    _ALGORITHM   = "RS256"
except RuntimeError:
    # Fallback to HS256 with a secret for development (not production)
    import secrets
    _PRIVATE_KEY = secrets.token_hex(32)
    _PUBLIC_KEY  = _PRIVATE_KEY
    _ALGORITHM   = "HS256"
    import logging
    logging.getLogger(__name__).warning(
        "⚠️  RSA keys not found — using HS256 DEVELOPMENT fallback. "
        "Generate RSA keys for production."
    )


# ── Token creation ────────────────────────────────────────────────────────────
def create_access_token(user_id: int, username: str, role: str, department_id: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "dept": department_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=_ALGORITHM)


# ── Token verification ────────────────────────────────────────────────────────
def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, _PUBLIC_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Bearer extractor ──────────────────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Container for authenticated user context."""
    def __init__(self, user_id: int, username: str, role: str, department_id: Optional[int], jti: str):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.department_id = department_id
        self.jti = jti


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    request: Request = None,
) -> CurrentUser:
    """FastAPI dependency — extracts and validates the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    # Check blacklist (DB check done in rbac.py to avoid circular imports)
    return CurrentUser(
        user_id=int(payload["sub"]),
        username=payload.get("username", ""),
        role=payload.get("role", ""),
        department_id=payload.get("dept"),
        jti=payload.get("jti", ""),
    )


def require_role(*allowed_roles: str):
    """Dependency factory — restricts endpoint to specific roles."""
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}. Your role: {user.role}",
            )
        return user
    return _check


# Convenience dependencies
require_ceo = require_role("ceo")
require_ceo_or_finance = require_role("ceo", "finance")
require_any_staff = require_role("ceo", "dept_head", "finance")
