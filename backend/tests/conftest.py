"""
Shared test fixtures for all test suites.

Unit tests use cipdb_test (isolated). Integration tests use the main cipdb
with test org rows seeded and cleaned up per session. The app's real DB engine
is used so FK constraints and the full schema are always available.

Tenant isolation: the TenantMiddleware test bypass is activated by patching
settings.APP_ENV = "testing" before the app is imported.
"""

import os
import uuid
from collections.abc import AsyncGenerator

# Set APP_ENV before any app module is imported so database.py picks it up
# at module load time (NullPool) and middleware uses the test bypass.
os.environ["APP_ENV"] = "testing"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Also patch the settings singleton (loaded by earlier imports) to testing mode.
from app.core.config import settings as _settings
_settings.APP_ENV = "testing"  # type: ignore[assignment]

from app.core.config import settings
from app.core.database import Base, get_db_no_rls
from app.main import app

# ── Test DB for unit tests (uses cipdb_test) ──────────────────────────────────
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/cipdb", "/cipdb_test")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# ── Stable test tenant IDs (constant across the session) ──────────────────────
TENANT_A_ID = str(uuid.uuid4())
TENANT_B_ID = str(uuid.uuid4())
USER_A_ID = str(uuid.uuid4())
USER_B_ID = str(uuid.uuid4())


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create cipdb_test schema for unit tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_integration_orgs():
    """
    Seed test org rows in the main cipdb so integration test HTTP requests
    (which hit the app's real DB engine) satisfy FK constraints.
    Cleaned up at session teardown.
    """
    from sqlalchemy import delete
    from app.models.organization import Organization
    from app.models.project import Project

    org_ids: list[uuid.UUID] = []

    async for session in get_db_no_rls():
        for tenant_id_str in (TENANT_A_ID, TENANT_B_ID):
            tid = uuid.UUID(tenant_id_str)
            existing = await session.get(Organization, tid)
            if not existing:
                org = Organization(
                    id=tid,
                    clerk_org_id=f"test_{tenant_id_str[:8]}",
                    name=f"Test Org {tenant_id_str[:8]}",
                    slug=f"test-{tenant_id_str[:8]}",
                )
                session.add(org)
                org_ids.append(tid)
        # Explicit commit so the rows are visible to the app's own DB connections
        await session.commit()

    yield

    # Cleanup in dependency order: children before parents
    async for session in get_db_no_rls():
        for tid in org_ids:
            await session.execute(delete(Project).where(Project.organization_id == tid))
        await session.commit()
        for tid in org_ids:
            await session.execute(delete(Organization).where(Organization.id == tid))
        await session.commit()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Session on cipdb_test for unit tests."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


def _make_headers(tenant_id: str, user_id: str) -> dict:
    """
    Mock auth headers trusted by TenantMiddleware when APP_ENV=testing.
    """
    return {
        "X-Test-Tenant-Id": tenant_id,
        "X-Test-User-Id": user_id,
        "Authorization": "Bearer test-token",
    }


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def tenant_a_headers() -> dict:
    return _make_headers(TENANT_A_ID, USER_A_ID)


@pytest.fixture
def tenant_b_headers() -> dict:
    return _make_headers(TENANT_B_ID, USER_B_ID)
