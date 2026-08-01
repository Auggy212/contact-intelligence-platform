import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        tenant_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        model_version: str | None = None,
        prompt_version: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            organization_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=metadata,
            model_version=model_version,
            prompt_version=prompt_version,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(entry)
        await self._db.flush()
        return entry

    async def list_for_tenant(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        action_filter: str | None = None,
        resource_id: uuid.UUID | None = None,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.organization_id == tenant_id)
        if action_filter:
            query = query.where(AuditLog.action == action_filter)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars().all())
