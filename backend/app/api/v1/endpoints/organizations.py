import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, require_admin
from app.schemas.organization import OrganizationOut, OrganizationUpdate, WorkspaceCreate, WorkspaceOut, WorkspaceUpdate
from app.services.organization_service import OrganizationService, WorkspaceService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/me", response_model=OrganizationOut)
async def get_my_organization(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = OrganizationService(session)
    org = await svc.get_by_clerk_id(tenant_id)
    if not org:
        from app.core.exceptions import not_found
        raise not_found("Organization")
    return org


@router.patch("/me", response_model=OrganizationOut, dependencies=[Depends(require_admin)])
async def update_my_organization(
    data: OrganizationUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = OrganizationService(session)
    org = await svc.get_by_clerk_id(tenant_id)
    return await svc.update(org.id, data)


# ── Workspaces ────────────────────────────────────────────────────────────────

@router.get("/me/workspaces", response_model=list[WorkspaceOut])
async def list_workspaces(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = WorkspaceService(session, uuid.UUID(tenant_id))
    return await svc.list_all()


@router.post("/me/workspaces", response_model=WorkspaceOut, status_code=201)
async def create_workspace(
    data: WorkspaceCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = WorkspaceService(session, uuid.UUID(tenant_id))
    return await svc.create(data)


@router.patch("/me/workspaces/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = WorkspaceService(session, uuid.UUID(tenant_id))
    return await svc.update(workspace_id, data)
