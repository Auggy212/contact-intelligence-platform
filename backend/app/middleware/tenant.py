from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import extract_tenant_id, extract_user_id, verify_clerk_token

logger = get_logger(__name__)

# Paths that bypass JWT verification
_PUBLIC_PATHS = {
    "/health",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/webhooks/stripe",
    "/api/v1/webhooks/clerk",
}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Validates the Clerk JWT on every request, extracts tenant_id and user_id,
    and stores them on request.state for downstream use.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Test bypass: accept plain header identity when running in test environment
        if settings.is_testing:
            test_tenant = request.headers.get("X-Test-Tenant-Id")
            test_user = request.headers.get("X-Test-User-Id")
            if test_tenant and test_user:
                request.state.tenant_id = test_tenant
                request.state.user_id = test_user
                request.state.org_role = "org:admin"
                request.state.jwt_claims = {}
                return await call_next(request)
            # No test headers → 401 (unauthenticated)
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            claims = await verify_clerk_token(token)
        except Exception as exc:
            logger.warning("jwt_verification_failed", error=str(exc))
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        request.state.tenant_id = extract_tenant_id(claims)
        request.state.user_id = extract_user_id(claims)
        request.state.org_role = claims.get("org_role")
        request.state.jwt_claims = claims

        import structlog
        structlog.contextvars.bind_contextvars(
            tenant_id=request.state.tenant_id,
            user_id=request.state.user_id,
            path=request.url.path,
            method=request.method,
        )

        return await call_next(request)
