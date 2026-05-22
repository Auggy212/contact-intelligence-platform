import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

# NullPool in testing: each per-test asyncio loop gets a fresh connection.
# os.environ is checked directly because database.py is imported before the
# conftest can patch the settings singleton in APP_ENV=testing mode.
_is_testing = os.environ.get("APP_ENV") == "testing"
_engine_kwargs: dict = (
    {"poolclass": NullPool}
    if _is_testing
    else {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async DB session with the RLS tenant context already set.
    Every query inside this session is automatically scoped to tenant_id via RLS.
    """
    async with AsyncSessionLocal() as session:
        # SET does not support parameterized binding — must interpolate inline.
        # tenant_id is a validated UUID string from Clerk JWT claims (safe to embed).
        await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_no_rls() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a session WITHOUT RLS context. Use only for:
    - Superadmin operations
    - Webhook handlers that create org records before tenant exists
    - Migrations and seed scripts
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
