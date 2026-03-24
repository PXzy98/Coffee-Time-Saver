from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth.dependencies import get_current_user, get_user_roles
from core.models import User
from core.logging import audit_log
from modules.auth.schemas import (
    LoginRequest, TokenResponse, RefreshRequest,
    AccessTokenResponse, UserResponse,
)
from modules.auth.service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    tokens = await service.login(body.email, body.password)
    await audit_log(db, action="auth.login", entity_type="user", entity_id=body.email,
                    ip_address=request.client.host if request.client else None)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.refresh(body.refresh_token)
    return AccessTokenResponse(**result)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await audit_log(db, action="auth.logout", entity_type="user", entity_id=str(current_user.id),
                    user_id=current_user.id)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        preferred_lang=current_user.preferred_lang,
        roles=get_user_roles(current_user),
    )
