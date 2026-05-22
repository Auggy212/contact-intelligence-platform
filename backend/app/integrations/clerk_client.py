import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://api.clerk.com/v1"


async def invite_organization_member(
    clerk_org_id: str,
    email: str,
    role: str,
) -> dict:
    """Sends a Clerk organization invitation email."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BASE_URL}/organizations/{clerk_org_id}/invitations",
            headers={
                "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "email_address": email,
                "role": role,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("clerk_invitation_sent", org=clerk_org_id, email=email, role=role)
        return resp.json()


async def get_clerk_user(clerk_user_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BASE_URL}/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
