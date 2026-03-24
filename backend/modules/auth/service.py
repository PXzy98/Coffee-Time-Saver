import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.models import User, UserRole
from core.auth.providers import LocalAuthProvider
from core.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from core.auth.dependencies import get_user_roles
from fastapi import HTTPException, status


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._local_auth = LocalAuthProvider()

    async def login(self, email: str, password: str) -> dict:
        user = await self._local_auth.authenticate(self.db, email=email, password=password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        roles = await self._get_roles(user.id)
        return {
            "access_token": create_access_token(user.id, roles),
            "refresh_token": create_refresh_token(user.id),
        }

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user_id = uuid.UUID(payload["sub"])
        roles = await self._get_roles(user_id)
        return {"access_token": create_access_token(user_id, roles)}

    async def _get_roles(self, user_id: uuid.UUID) -> list[str]:
        result = await self.db.execute(
            select(UserRole).options(selectinload(UserRole.role)).where(UserRole.user_id == user_id)
        )
        return [ur.role.name for ur in result.scalars().all()]
