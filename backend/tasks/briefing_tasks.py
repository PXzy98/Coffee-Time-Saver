import asyncio
import logging

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.briefing_tasks.generate_all_briefings")
def generate_all_briefings() -> None:
    asyncio.run(_generate_all_async())


async def _generate_all_async() -> None:
    from core.database import AsyncSessionLocal
    from modules.briefing.service import BriefingService
    from sqlalchemy import select
    from core.models import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.is_active == True))
        users = result.scalars().all()
        service = BriefingService(db)
        for user in users:
            try:
                await service.get_or_create_today(user)
            except Exception as e:
                logger.error("Briefing generation failed for user %s: %s", user.id, e)
