from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth.dependencies import get_current_user
from core.models import User
from modules.briefing.schemas import BriefingOut
from modules.briefing.service import BriefingService

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.get("/today", response_model=BriefingOut)
async def get_today_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BriefingService(db)
    return await service.get_or_create_today(current_user)
