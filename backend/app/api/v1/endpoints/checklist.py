import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, get_user_id, require_admin
from app.schemas.checklist import ChecklistRuleCreate, ChecklistRuleOut, ChecklistRuleUpdate
from app.services.checklist_service import ChecklistService

router = APIRouter(prefix="/checklist-rules", tags=["Checklist Rules"])


@router.get("", response_model=list[ChecklistRuleOut])
async def list_rules(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ChecklistService(session, uuid.UUID(tenant_id))
    return await svc.list_all()


@router.get("/{rule_id}", response_model=ChecklistRuleOut)
async def get_rule(
    rule_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ChecklistService(session, uuid.UUID(tenant_id))
    return await svc.get_by_id(rule_id)


@router.post("", response_model=ChecklistRuleOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_rule(
    data: ChecklistRuleCreate,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ChecklistService(session, uuid.UUID(tenant_id))
    rule = await svc.create(data, uuid.UUID(user_id))
    from app.services.audit_service import AuditService
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="checklist_rule.create",
        resource_type="ChecklistRule",
        resource_id=rule.id,
        metadata={"rule_code": rule.rule_code, "name": rule.name},
    )
    return rule


@router.patch("/{rule_id}", response_model=ChecklistRuleOut, dependencies=[Depends(require_admin)])
async def update_rule(
    rule_id: uuid.UUID,
    data: ChecklistRuleUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ChecklistService(session, uuid.UUID(tenant_id))
    rule = await svc.update(rule_id, data)
    from app.services.audit_service import AuditService
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="checklist_rule.update",
        resource_type="ChecklistRule",
        resource_id=rule_id,
    )
    return rule


@router.delete("/{rule_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_rule(
    rule_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ChecklistService(session, uuid.UUID(tenant_id))
    await svc.delete(rule_id)
    from app.services.audit_service import AuditService
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="checklist_rule.delete",
        resource_type="ChecklistRule",
        resource_id=rule_id,
    )
