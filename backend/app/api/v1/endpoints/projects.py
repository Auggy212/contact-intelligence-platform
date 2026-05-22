import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, get_user_id
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    data: ProjectCreate,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.create(data)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.list_all(skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.get_by_id(project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.update(project_id, data)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    await svc.delete(project_id)
