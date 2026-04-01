import asyncio
import logging
import sys
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.briefing_tasks.generate_all_briefings")
def generate_all_briefings() -> None:
    import sys
    from pathlib import Path
    _bd = str(Path(__file__).resolve().parent.parent)
    if _bd not in sys.path:
        sys.path.insert(0, _bd)
    asyncio.run(_generate_all_async())


async def _generate_all_async() -> None:
    import sys
    from pathlib import Path
    _bd = str(Path(__file__).resolve().parent.parent)
    if _bd not in sys.path:
        sys.path.insert(0, _bd)
    from core.database import engine, AsyncSessionLocal
    await engine.dispose()
    await engine.dispose()  # Reset connection pool for this event loop
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
