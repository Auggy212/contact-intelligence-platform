from starlette.requests import Request

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _get_tenant_or_ip(request: Request) -> str:
    """Rate limit key: tenant_id when authenticated, IP address otherwise."""
    tenant_id = getattr(request.state, "tenant_id", None)
    return str(tenant_id) if tenant_id else get_remote_address(request)


limiter = Limiter(
    key_func=_get_tenant_or_ip,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)
