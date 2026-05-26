"""
backend/routes/auth_route.py
-----------------------------
Login, logout, token refresh, and user management endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import (
    create_access_token, create_refresh_token,
    verify_password, decode_token, require_any_staff
)
from audit.audit_log import log_action
from database import get_db
from models.sql_models import User, TokenBlacklist
from models.schemas import LoginRequest, TokenResponse, UserResponse
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and return JWT access + refresh tokens."""
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    access_token = create_access_token(user.id, user.username, user.role, user.department_id)
    refresh_token = create_refresh_token(user.id)

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",
    )

    await log_action(db, "LOGIN", user.id, user.role)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_any_staff),
):
    """Blacklist current JWT and clear refresh cookie."""
    blacklisted = TokenBlacklist(jti=user.jti)
    db.add(blacklisted)
    response.delete_cookie("refresh_token", path="/api/auth")
    await log_action(db, "LOGOUT", user.user_id, user.role)
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Use refresh token cookie to issue new access token."""
    refresh = request.cookies.get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    payload = decode_token(refresh)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    new_access = create_access_token(user.id, user.username, user.role, user.department_id)
    return TokenResponse(
        access_token=new_access,
        token_type="bearer",
        role=user.role,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(require_any_staff)):
    """Return current user profile."""
    return UserResponse(id=user.user_id, username=user.username, role=user.role, department_id=user.department_id)
