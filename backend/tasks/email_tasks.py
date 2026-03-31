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
        email_rows = await EmailBotService(db).poll_and_process()

        # Post-processing intelligence for each email (best-effort)
        if not email_rows:
            return

        use_llm_tasks = settings.EMAIL_TASK_STRATEGY == "llm"
        use_llm_project = settings.EMAIL_PROJECT_SUGGESTION == "llm"
        use_llm_assoc = settings.TASK_PROJECT_ASSOCIATION == "llm"

        if not (use_llm_tasks or use_llm_project or use_llm_assoc):
            return

        try:
            from modules.llm_gateway.service import LLMGateway
            from modules.email_bot.email_intelligence import (
                extract_tasks_from_email,
                suggest_project_for_email,
            )
            from modules.file_processing.document_intelligence import (
                associate_tasks_to_projects,
            )

            llm = LLMGateway(db)

            for email_row, user_id in email_rows:
                try:
                    created_tasks = []
                    if use_llm_tasks:
                        created_tasks = await extract_tasks_from_email(
                            email_row, user_id, db, llm
                        )

                    if use_llm_project:
                        await suggest_project_for_email(email_row, user_id, db, llm)

                    if use_llm_assoc and created_tasks:
                        await associate_tasks_to_projects(created_tasks, db, llm)

                except Exception as e:
                    logger.warning(
                        "Email intelligence failed for '%s': %s",
                        email_row.subject, e,
                    )
        except Exception as e:
            logger.warning("Email post-processing setup failed: %s", e)
