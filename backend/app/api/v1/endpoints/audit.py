import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, require_admin
from app.schemas.audit import AuditLogOut
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


@router.get("", response_model=list[AuditLogOut], dependencies=[Depends(require_admin)])
async def get_audit_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AuditService(session)
    return await svc.list_for_tenant(
        uuid.UUID(tenant_id),
        skip=skip,
        limit=limit,
        action_filter=action,
    )
