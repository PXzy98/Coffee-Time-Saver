"""
pytest fixtures shared across all tests.

Two fixture scopes:
- Unit tests:  no database needed — import and call functions directly.
- Integration tests: require a real PostgreSQL+pgvector instance.

Set TEST_DATABASE_URL env var to enable integration tests, e.g.:
    TEST_DATABASE_URL=postgresql+asyncpg://cts:cts_password@localhost:5432/cts_test pytest
"""
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator

# ── Database (integration only) ───────────────────────────────────────────────

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cts:cts_password@localhost:5432/cts_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create tables once per session, drop them after."""
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration test")

    from sqlalchemy.ext.asyncio import create_async_engine
    from core.database import Base
    import core.models  # noqa: ensure all models are registered

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator:
    """Per-test async session, rolled back after each test."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_db(db_session):
    """Session with roles + a test admin user already inserted."""
    from core.models import Role, User, UserRole
    from core.auth.password import hash_password
    import uuid

    admin_role = Role(name="admin")
    pm_role = Role(name="pm")
    db_session.add_all([admin_role, pm_role])
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=hash_password("testpass"),
        display_name="Test Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await db_session.commit()

    return {"user": user, "admin_role": admin_role, "pm_role": pm_role}
