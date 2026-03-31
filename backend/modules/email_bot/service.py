import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from core.models import Email, User
from modules.email_bot.imap_client import IMAPClient
from modules.email_bot.processor import EmailProcessor

logger = logging.getLogger("coffee_time_saver")


class EmailBotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def poll_and_process(self) -> list[tuple[Email, any]]:
        """Poll IMAP, process emails, return list of (Email, user_id) for post-processing."""
        if not settings.IMAP_HOST:
            logger.info("IMAP not configured — skipping email poll")
            return []

        client = IMAPClient(
            host=settings.IMAP_HOST,
            port=settings.IMAP_PORT,
            user=settings.IMAP_USER,
            password=settings.IMAP_PASSWORD,
            folder=settings.IMAP_FOLDER,
            auth_method=settings.IMAP_AUTH_METHOD,
            oauth_access_token=settings.IMAP_OAUTH_ACCESS_TOKEN,
            oauth_refresh_token=settings.IMAP_OAUTH_REFRESH_TOKEN,
            oauth_client_id=settings.IMAP_OAUTH_CLIENT_ID,
            oauth_client_secret=settings.IMAP_OAUTH_CLIENT_SECRET,
            oauth_token_url=settings.IMAP_OAUTH_TOKEN_URL,
        )

        # Get a system user to own imported emails (first admin)
        result = await self.db.execute(
            select(User).where(User.is_active == True).limit(1)
        )
        owner = result.scalar_one_or_none()
        if owner is None:
            logger.warning("No users found — cannot process emails")
            return []

        try:
            raw_emails = client.fetch_unseen()
            logger.info("Email bot: fetched %d unseen emails", len(raw_emails))
        except Exception as e:
            logger.error("IMAP fetch failed: %s", e)
            return []

        processed: list[tuple[Email, any]] = []
        processor = EmailProcessor(self.db)
        for raw in raw_emails:
            try:
                email_row = await processor.process(raw, owner.id)
                if email_row is not None:
                    processed.append((email_row, owner.id))
            except Exception as e:
                logger.error("Failed to process email %s: %s", raw.get("message_id"), e)

        # Push WebSocket notification
        from core.websocket import manager
        await manager.publish(None, {"type": "dashboard.refresh", "payload": {}})

        return processed
