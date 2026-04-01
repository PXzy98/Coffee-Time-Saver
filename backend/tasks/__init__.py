import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so that "core", "modules", etc. are importable
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "coffee_time_saver",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "tasks.file_tasks",
        "tasks.email_tasks",
        "tasks.briefing_tasks",
        "tasks.embedding_tasks",
        "tasks.task_sort_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-emails-every-5-minutes": {
            "task": "tasks.email_tasks.poll_emails",
            "schedule": settings.IMAP_POLL_INTERVAL_SECONDS,
        },
        "generate-daily-briefings": {
            "task": "tasks.briefing_tasks.generate_all_briefings",
            "schedule": crontab(hour=6, minute=0),
        },
        "resort-tasks-daily": {
            "task": "tasks.task_sort_tasks.resort_all_tasks",
            "schedule": crontab(hour=6, minute=5),
        },
    },
)
