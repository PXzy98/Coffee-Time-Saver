from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth.dependencies import get_current_user
from core.models import User, ToolModule

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/registry")
async def list_tools(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ToolModule).where(ToolModule.is_enabled == True).order_by(ToolModule.sort_order)
    )
    tools = result.scalars().all()
    return [
        {
            "slug": t.slug,
            "name_en": t.name_en,
            "name_fr": t.name_fr,
            "description_en": t.description_en,
            "description_fr": t.description_fr,
            "icon": t.icon,
            "api_endpoint": t.api_endpoint,
        }
        for t in tools
    ]
