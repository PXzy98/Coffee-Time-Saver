import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.auth.dependencies import get_current_user, require_role
from core.models import User, LLMConfig, UserRole, Role
from core.logging import audit_log
from config import settings as app_settings
from modules.settings.schemas import (
    LLMConfigOut, LLMConfigCreate, LLMConfigUpdate,
    EmailBotConfigOut, EmailBotConfigUpdate,
    UserAdminOut, UserRoleUpdate,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# LLM Config
# ---------------------------------------------------------------------------

@router.get("/llm/active")
async def get_active_llm_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently active LLM config (available to all authenticated users)."""
    # Try name="primary" first (same logic as LLMGateway)
    result = await db.execute(
        select(LLMConfig).where(LLMConfig.name == "primary", LLMConfig.is_active == True)
    )
    config = result.scalar_one_or_none()
    if config is None:
        # Fall back to any active config
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.is_active == True).limit(1)
        )
        config = result.scalar_one_or_none()
    if config is None:
        return {"config": None}
    return {"config": LLMConfigOut.model_validate(config)}


@router.get("/llm", response_model=list[LLMConfigOut])
async def list_llm_configs(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMConfig))
    return result.scalars().all()


@router.post("/llm", response_model=LLMConfigOut, status_code=201)
async def create_llm_config(
    body: LLMConfigCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    config = LLMConfig(**body.model_dump())
    # Ensure only one config is active at a time
    if config.is_active:
        from sqlalchemy import update as sa_update
        await db.execute(sa_update(LLMConfig).values(is_active=False))
    db.add(config)
    await db.commit()
    await db.refresh(config)
    await audit_log(db, action="settings.llm.create", entity_type="llm_config",
                    entity_id=str(config.id), user_id=current_user.id)
    return config


@router.put("/llm/{config_id}", response_model=LLMConfigOut)
async def update_llm_config(
    config_id: int,
    body: LLMConfigUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMConfig).where(LLMConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="LLM config not found")
    update_data = body.model_dump(exclude_none=True)
    for key, val in update_data.items():
        setattr(config, key, val)
    # Ensure only one config is active at a time
    if update_data.get("is_active"):
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(LLMConfig)
            .where(LLMConfig.id != config_id)
            .values(is_active=False)
        )
    await db.commit()
    await db.refresh(config)
    await audit_log(db, action="settings.llm.update", entity_type="llm_config",
                    entity_id=str(config_id), user_id=current_user.id)
    return config


@router.post("/llm/test")
async def test_llm_config(
    body: LLMConfigUpdate,
    config_id: Optional[int] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Test an LLM connection. If config_id is provided, use stored config from DB."""
    from modules.llm_gateway.providers.openai_provider import OpenAIProvider
    from modules.llm_gateway.providers.claude_provider import ClaudeProvider
    from modules.llm_gateway.providers.ollama_provider import OllamaProvider
    from modules.llm_gateway.schemas import LLMRequest, Message

    if config_id is not None:
        result = await db.execute(select(LLMConfig).where(LLMConfig.id == config_id))
        test_config = result.scalar_one_or_none()
        if test_config is None:
            raise HTTPException(status_code=404, detail="LLM config not found")
    else:
        from core.models import LLMConfig as LLMConfigModel
        test_config = LLMConfigModel(
            name="test",
            provider=body.provider or "openai",
            api_url=body.api_url or "",
            api_key=body.api_key,
            model=body.model or "gpt-4o-mini",
        )

    providers = {"openai": OpenAIProvider(), "claude": ClaudeProvider(), "ollama": OllamaProvider()}
    provider = providers.get(test_config.provider, OpenAIProvider())
    request = LLMRequest(messages=[Message(role="user", content="Say 'ok'")], max_tokens=5)
    try:
        response = await provider.complete(request, test_config)
        return {"status": "ok", "response": response.content[:100]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ---------------------------------------------------------------------------
# Email Bot Config
# ---------------------------------------------------------------------------

@router.get("/email-status")
async def get_email_status(current_user: User = Depends(get_current_user)):
    """Return email bot configuration and live connection status. Available to all authenticated users."""
    import asyncio
    import imaplib

    configured = bool(app_settings.IMAP_HOST and app_settings.IMAP_USER)
    if not configured:
        return {"configured": False, "connected": False}

    def _test_imap():
        try:
            conn = imaplib.IMAP4_SSL(app_settings.IMAP_HOST, app_settings.IMAP_PORT)
            conn.login(app_settings.IMAP_USER, app_settings.IMAP_PASSWORD)
            conn.logout()
            return True
        except Exception:
            return False

    loop = asyncio.get_event_loop()
    connected = await loop.run_in_executor(None, _test_imap)
    return {"configured": True, "connected": connected}


@router.get("/email", response_model=EmailBotConfigOut)
async def get_email_config(current_user: User = Depends(require_role("admin"))):
    return EmailBotConfigOut(
        imap_host=app_settings.IMAP_HOST,
        imap_port=app_settings.IMAP_PORT,
        imap_user=app_settings.IMAP_USER,
        imap_folder=app_settings.IMAP_FOLDER,
        poll_interval_seconds=app_settings.IMAP_POLL_INTERVAL_SECONDS,
    )


@router.put("/email")
async def update_email_config(
    body: EmailBotConfigUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Email bot config is managed via environment variables.
    This endpoint documents the expected values; a restart is required after changes."""
    await audit_log(db, action="settings.email.update", user_id=current_user.id,
                    details=body.model_dump(exclude_none=True, exclude={"imap_password"}))
    return {"detail": "Email config noted. Update your .env and restart the service."}


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserAdminOut])
async def list_users(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.user_roles).selectinload(UserRole.role))
    )
    users = result.scalars().all()
    return [
        UserAdminOut(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            is_active=u.is_active,
            roles=[ur.role.name for ur in u.user_roles],
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_user_roles(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Clear existing roles
    for ur in list(user.user_roles):
        await db.delete(ur)
    await db.flush()

    # Assign new roles
    for role_name in body.roles:
        role_result = await db.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id))

    await db.commit()
    await db.refresh(user)

    await audit_log(db, action="admin.user.roles_updated", entity_type="user",
                    entity_id=str(user_id), user_id=current_user.id,
                    details={"new_roles": body.roles})

    return UserAdminOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=body.roles,
    )
