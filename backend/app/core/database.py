import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Use NullPool when:
#  - APP_ENV=testing  : each pytest creates a new event loop
#  - Celery worker    : each task runs in a new event loop (new_event_loop per task)
#                       so the engine must not cache connections across loops
_use_null_pool = os.environ.get("APP_ENV") == "testing" or os.environ.get("CELERY_WORKER") == "1"

_engine_kwargs: dict = (
    {"poolclass": NullPool}
    if _use_null_pool
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
    async with AsyncSessionLocal() as session:
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
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
