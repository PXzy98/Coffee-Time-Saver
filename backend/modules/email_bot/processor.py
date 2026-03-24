import re
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Email, EmailAttachment, Document, Task
from modules.file_processing.service import _get_parser

logger = logging.getLogger("coffee_time_saver")

_ACTION_RE = re.compile(
    r"(?:please|action|todo|follow.?up|next step)[:\s]+(.+?)(?:\.|$)",
    re.IGNORECASE,
)


def _extract_action_items(text: str) -> list[str]:
    return [m.group(1).strip() for m in _ACTION_RE.finditer(text)][:5]


class EmailProcessor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process(self, raw: dict, user_id) -> None:
        # Deduplicate
        if raw.get("message_id"):
            from sqlalchemy import select
            result = await self.db.execute(
                select(Email).where(Email.message_id == raw["message_id"])
            )
            if result.scalar_one_or_none():
                return  # Already processed

        received_at = None
        if raw.get("received_at"):
            try:
                from email.utils import parsedate_to_datetime
                received_at = parsedate_to_datetime(raw["received_at"])
            except Exception:
                received_at = datetime.now(timezone.utc)

        email_row = Email(
            message_id=raw.get("message_id"),
            from_address=raw.get("from_address"),
            to_addresses=raw.get("to_addresses", []),
            cc_addresses=raw.get("cc_addresses", []),
            subject=raw.get("subject"),
            body_text=raw.get("body_text"),
            body_html=raw.get("body_html"),
            received_at=received_at,
            processed=False,
        )
        self.db.add(email_row)
        await self.db.flush()

        # Process attachments through file pipeline
        for att in raw.get("attachments", []):
            if not att.get("data"):
                continue
            parser = _get_parser(att.get("mime_type", ""), att["filename"])
            try:
                full_text = await parser.parse(att["data"], att["filename"])
            except Exception as e:
                logger.warning("Failed to parse email attachment %s: %s", att["filename"], e)
                full_text = ""

            doc = Document(
                uploaded_by=user_id,
                filename=att["filename"],
                mime_type=att.get("mime_type"),
                file_size_bytes=len(att["data"]),
                full_text=full_text,
                status="pending",
                source="email",
            )
            self.db.add(doc)
            await self.db.flush()

            att_row = EmailAttachment(
                email_id=email_row.id,
                document_id=doc.id,
                filename=att["filename"],
                mime_type=att.get("mime_type"),
                file_size_bytes=len(att["data"]),
            )
            self.db.add(att_row)

            # Dispatch ingestion
            from tasks.file_tasks import process_file
            process_file.delay(str(doc.id))

        # Extract action items as tasks
        body = raw.get("body_text", "") or ""
        actions = _extract_action_items(body)
        for action_title in actions:
            task = Task(
                user_id=user_id,
                title=action_title[:500],
                source="email",
                description=f"From email: {raw.get('subject', '')}",
            )
            self.db.add(task)

        email_row.processed = True
        await self.db.commit()
