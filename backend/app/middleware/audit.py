import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with duration, status, tenant, and user."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            tenant_id=getattr(request.state, "tenant_id", None),
            user_id=getattr(request.state, "user_id", None),
        )
        return response
