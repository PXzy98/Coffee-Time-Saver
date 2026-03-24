from datetime import date, datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from core.models import Task, Project, ProjectMember, Document, Email, AuditLog, User


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self, user: User) -> dict:
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)

        # Active projects
        proj_result = await self.db.execute(
            select(func.count()).select_from(Project).where(
                or_(
                    Project.owner_id == user.id,
                    Project.id.in_(
                        select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
                    ),
                ),
                Project.status == "active",
            )
        )
        active_projects = proj_result.scalar_one()

        # Overdue tasks
        overdue_result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user.id,
                Task.is_completed == False,
                Task.due_date < today,
            )
        )
        overdue_tasks = overdue_result.scalar_one()

        # Pending tasks
        pending_result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user.id,
                Task.is_completed == False,
            )
        )
        pending_tasks = pending_result.scalar_one()

        # Files processed today
        files_result = await self.db.execute(
            select(func.count()).select_from(Document).where(
                Document.uploaded_by == user.id,
                Document.status == "completed",
                Document.created_at >= today_start,
            )
        )
        files_today = files_result.scalar_one()

        # Unread emails
        emails_result = await self.db.execute(
            select(func.count()).select_from(Email).where(Email.processed == False)
        )
        unread_emails = emails_result.scalar_one()

        # Recent activity (last 20 audit entries)
        activity_result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
        activity = activity_result.scalars().all()

        return {
            "metrics": {
                "active_projects": active_projects,
                "overdue_tasks": overdue_tasks,
                "pending_tasks": pending_tasks,
                "files_processed_today": files_today,
                "unread_emails": unread_emails,
            },
            "recent_activity": [
                {
                    "action": a.action,
                    "entity_type": a.entity_type,
                    "entity_id": a.entity_id,
                    "created_at": a.created_at,
                }
                for a in activity
            ],
        }
