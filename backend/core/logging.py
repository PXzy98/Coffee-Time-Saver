import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.models import AuditLog

logger = logging.getLogger("coffee_time_saver")


async def audit_log(
    db: AsyncSession,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    user_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Write a structured audit log entry to the database."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    logger.info(
        "AUDIT action=%s entity_type=%s entity_id=%s user_id=%s",
        action, entity_type, entity_id, user_id,
    )
