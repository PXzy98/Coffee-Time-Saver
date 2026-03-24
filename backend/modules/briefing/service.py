import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from core.models import DailyBriefing, Task, Email, User

logger = logging.getLogger("coffee_time_saver")


class TemplateBriefingStrategy:
    """Phase 1: Generate briefing from structured template."""

    async def generate(self, user: User, db: AsyncSession) -> tuple[str, str]:
        today = date.today()

        # Gather tasks
        tasks_result = await db.execute(
            select(Task).where(Task.user_id == user.id, Task.is_completed == False)
            .order_by(Task.sort_score.desc().nullslast()).limit(10)
        )
        tasks = tasks_result.scalars().all()

        overdue = [t for t in tasks if t.due_date and t.due_date < today]
        due_today = [t for t in tasks if t.due_date == today]

        # Gather unread emails
        emails_result = await db.execute(
            select(Email).where(Email.processed == False).order_by(Email.received_at.desc()).limit(5)
        )
        emails = emails_result.scalars().all()

        def build_en() -> str:
            lines = [f"# Daily Briefing — {today.strftime('%B %d, %Y')}\n"]
            if overdue:
                lines.append("## Overdue Tasks")
                for t in overdue:
                    lines.append(f"- ⚠ {t.title} (due {t.due_date})")
                lines.append("")
            if due_today:
                lines.append("## Due Today")
                for t in due_today:
                    lines.append(f"- {t.title}")
                lines.append("")
            if tasks:
                lines.append("## Today's Priorities")
                for t in tasks[:5]:
                    lines.append(f"- {t.title}")
                lines.append("")
            if emails:
                lines.append("## Unread Emails")
                for e in emails:
                    lines.append(f"- From {e.from_address}: {e.subject or '(no subject)'}")
                lines.append("")
            if not tasks and not emails:
                lines.append("No pending tasks or emails. You're all caught up!")
            return "\n".join(lines)

        def build_fr() -> str:
            lines = [f"# Résumé quotidien — {today.strftime('%d %B %Y')}\n"]
            if overdue:
                lines.append("## Tâches en retard")
                for t in overdue:
                    lines.append(f"- ⚠ {t.title} (échéance {t.due_date})")
                lines.append("")
            if due_today:
                lines.append("## À faire aujourd'hui")
                for t in due_today:
                    lines.append(f"- {t.title}")
                lines.append("")
            if tasks:
                lines.append("## Priorités du jour")
                for t in tasks[:5]:
                    lines.append(f"- {t.title}")
                lines.append("")
            if emails:
                lines.append("## Courriels non lus")
                for e in emails:
                    lines.append(f"- De {e.from_address} : {e.subject or '(sans objet)'}")
                lines.append("")
            if not tasks and not emails:
                lines.append("Aucune tâche ni courriel en attente. Tout est à jour !")
            return "\n".join(lines)

        return build_en(), build_fr()


class LLMBriefingStrategy:
    """Phase 2: LLM-generated narrative briefing."""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def generate(self, user: User, db: AsyncSession) -> tuple[str, str]:
        # Build context then ask LLM to generate bilingual briefing
        template_strategy = TemplateBriefingStrategy()
        en, fr = await template_strategy.generate(user, db)

        from modules.llm_gateway.schemas import LLMRequest, Message
        request_en = LLMRequest(
            messages=[
                Message(role="system", content="You are a professional PM assistant. Rewrite the following daily briefing as a concise, friendly narrative in English."),
                Message(role="user", content=en),
            ],
            config_name="primary",
            max_tokens=800,
        )
        request_fr = LLMRequest(
            messages=[
                Message(role="system", content="Vous êtes un assistant PM professionnel. Réécrivez le résumé quotidien suivant sous forme de récit concis et amical en français."),
                Message(role="user", content=fr),
            ],
            config_name="primary",
            max_tokens=800,
        )
        try:
            resp_en = await self.llm.complete(request_en)
            resp_fr = await self.llm.complete(request_fr)
            return resp_en.content, resp_fr.content
        except Exception as e:
            logger.warning("LLM briefing failed, using template: %s", e)
            return en, fr


class BriefingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_today(self, user: User) -> DailyBriefing:
        today = date.today()
        result = await self.db.execute(
            select(DailyBriefing).where(DailyBriefing.user_id == user.id, DailyBriefing.date == today)
        )
        briefing = result.scalar_one_or_none()
        if briefing:
            return briefing

        strategy = self._get_strategy()
        content_en, content_fr = await strategy.generate(user, self.db)

        briefing = DailyBriefing(
            user_id=user.id,
            date=today,
            content_en=content_en,
            content_fr=content_fr,
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(briefing)
        await self.db.commit()
        await self.db.refresh(briefing)
        return briefing

    def _get_strategy(self):
        if settings.BRIEFING_STRATEGY == "llm":
            from modules.llm_gateway.service import LLMGateway
            llm = LLMGateway(self.db)
            return LLMBriefingStrategy(llm)
        return TemplateBriefingStrategy()
