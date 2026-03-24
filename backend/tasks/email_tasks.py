import asyncio
import logging

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.email_tasks.poll_emails")
def poll_emails() -> None:
    asyncio.run(_poll_emails_async())


async def _poll_emails_async() -> None:
    from config import settings
    if not settings.IMAP_HOST:
        return
    from core.database import AsyncSessionLocal
    from modules.email_bot.service import EmailBotService

    async with AsyncSessionLocal() as db:
        await EmailBotService(db).poll_and_process()
