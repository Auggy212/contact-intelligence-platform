"""
FastAPI dependency functions — shared across all endpoint modules.
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthorizationError, forbidden
from app.core.constants import Role
from app.integrations.storage_client import StorageClient, get_storage_client


def get_tenant_id(request: Request) -> str:
    return request.state.tenant_id


def get_user_id(request: Request) -> str:
    return request.state.user_id


def get_org_role(request: Request) -> str | None:
    return getattr(request.state, "org_role", None)


async def get_session(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db(tenant_id):
        yield session


def get_storage() -> StorageClient:
    return get_storage_client()


def require_admin(role: str | None = Depends(get_org_role)):
    if role != "org:admin":
        raise forbidden()


def require_reviewer_or_above(role: str | None = Depends(get_org_role)):
    if role not in ("org:admin", "org:reviewer"):
        raise forbidden()
