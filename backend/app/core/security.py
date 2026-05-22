import httpx
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

# Clerk publishes its JWKS at this endpoint; we cache keys per process.
_JWKS_CACHE: dict | None = None
_CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"


async def _get_clerk_jwks() -> dict:
    global _JWKS_CACHE
    if _JWKS_CACHE is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _CLERK_JWKS_URL,
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
            _JWKS_CACHE = resp.json()
    return _JWKS_CACHE


async def verify_clerk_token(token: str) -> dict:
    """
    Verifies a Clerk-issued JWT and returns the decoded claims.
    Raises AuthenticationError on any failure.
    """
    try:
        jwks = await _get_clerk_jwks()
        # jose extracts kid from header and finds matching key automatically
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc
    except Exception as exc:
        raise AuthenticationError("Token verification failed") from exc


def extract_tenant_id(claims: dict) -> str:
    """
    Clerk stores the active organization ID in the `org_id` claim.
    Falls back to `sub` (user ID) for personal workspace flows.
    """
    org_id = claims.get("org_id") or claims.get("sub")
    if not org_id:
        raise AuthenticationError("No tenant identity in token")
    return org_id


def extract_user_id(claims: dict) -> str:
    user_id = claims.get("sub")
    if not user_id:
        raise AuthenticationError("No user identity in token")
    return user_id


def extract_org_role(claims: dict) -> str | None:
    return claims.get("org_role")
