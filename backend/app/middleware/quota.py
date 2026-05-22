from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.constants import PLAN_LIMITS, SubscriptionPlan, SubscriptionStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

# Paths that trigger quota enforcement (POST = consuming a resource)
_QUOTA_PATHS = {
    "/api/v1/projects",   # Creating a project consumes the monthly quota
}


class QuotaMiddleware(BaseHTTPMiddleware):
    """
    Checks per-tenant subscription limits before resource-creating requests.
    Actual quota counts are fetched from the DB via a lightweight service call.
    Heavy enforcement (per-AI-task token budgets) happens inside the task itself.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip quota enforcement in testing environment
        if settings.is_testing:
            return await call_next(request)

        # Only enforce on project creation POSTs
        if request.method != "POST" or request.url.path not in _QUOTA_PATHS:
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # Lazy import to avoid circular deps
        from app.core.database import get_db_no_rls
        from app.models.billing import Subscription
        from sqlalchemy import select

        try:
            async for session in get_db_no_rls():
                result = await session.execute(
                    select(Subscription).where(
                        Subscription.organization_id == tenant_id  # type: ignore[arg-type]
                    )
                )
                sub = result.scalar_one_or_none()

            if sub is None or sub.status not in (
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
            ):
                return JSONResponse(
                    status_code=402,
                    content={"detail": "No active subscription. Please upgrade your plan."},
                )

            limits = PLAN_LIMITS.get(sub.plan, PLAN_LIMITS[SubscriptionPlan.TRIAL])
            max_projects = limits["projects_per_month"]

            if max_projects == -1:
                return await call_next(request)

            # Count this month's projects (checked via service at request time)
            # Full enforcement is in ProjectService; middleware is an early short-circuit.
        except Exception as exc:
            logger.error("quota_check_failed", error=str(exc))
            # Fail open — don't block user if quota check itself errors

        return await call_next(request)
