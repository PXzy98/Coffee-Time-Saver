from abc import ABC, abstractmethod
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import User
from core.auth.password import verify_password


class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, db: AsyncSession, **credentials) -> Optional[User]:
        """Verify credentials and return the matching User, or None."""


class LocalAuthProvider(AuthProvider):
    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email, User.is_active == True))
        user = result.scalar_one_or_none()
        if user is None or user.password_hash is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
