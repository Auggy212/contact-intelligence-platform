from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "contract-intelligence-api"}


@router.get("/health/db")
async def health_db():
    """Deep health check: DB, Redis, Qdrant, and MinIO."""
    from app.core.database import get_db_no_rls
    from app.core.redis import get_redis
    from app.core.config import settings

    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        async for session in get_db_no_rls():
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    # Redis
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # Qdrant
    try:
        from app.integrations.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {exc}"

    # MinIO / S3 — instantiating the client checks connectivity (bucket_exists on init)
    try:
        from app.integrations.storage_client import get_storage_client
        get_storage_client()
        checks["storage"] = "ok"
    except Exception as exc:
        checks["storage"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
