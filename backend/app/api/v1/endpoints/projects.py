import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_storage, get_tenant_id, get_user_id
from app.integrations.storage_client import StorageClient
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import ProjectService
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    from app.services.audit_service import AuditService

    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    project = await svc.update(project_id, data)

    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="project.update",
        resource_type="Project",
        resource_id=project_id,
        metadata={k: v for k, v in data.model_dump().items() if v is not None},
    )

    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    storage: StorageClient = Depends(get_storage),
):
    from app.services.audit_service import AuditService

    svc = ProjectService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))

    # Capture project name before deletion for audit metadata
    project = await svc.get_by_id(project_id)
    project_name = project.name

    storage_keys = await svc.delete(project_id)

    # Write audit entry AFTER the cascade delete but still within the same transaction
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="project.delete",
        resource_type="Project",
        resource_id=project_id,
        metadata={
            "project_name": project_name,
            "files_deleted": len(storage_keys),
        },
    )

    # Delete files from MinIO/S3 — best-effort, after DB work is flushed
    for key in storage_keys:
        try:
            await storage.delete(key)
        except Exception:
            logger.warning("storage_delete_failed", key=key)
