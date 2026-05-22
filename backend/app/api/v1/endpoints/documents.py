import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_storage, get_tenant_id, get_user_id
from app.core.constants import FileRole
from app.integrations.storage_client import StorageClient
from app.schemas.project import DocumentUploadResponse, ProjectFileOut
from app.services.document_service import DocumentService
from app.workers.parse_tasks import parse_document_task

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["Documents"])

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    project_id: uuid.UUID,
    file_role: FileRole = Form(...),
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    storage: StorageClient = Depends(get_storage),
):
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_SIZE_BYTES:
        from app.core.exceptions import bad_request
        raise bad_request(f"File exceeds maximum size of {_MAX_SIZE_BYTES // 1_048_576} MB")

    svc = DocumentService(session, storage, uuid.UUID(tenant_id), uuid.UUID(user_id))
    pf = await svc.upload(
        project_id=project_id,
        file_role=file_role,
        filename=file.filename or "document",
        file_bytes=file_bytes,
        mime_type=file.content_type or "application/octet-stream",
    )

    # Enqueue background parse
    parse_document_task.delay(str(pf.id), tenant_id)

    # Audit log
    from app.services.audit_service import AuditService
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="document.upload",
        resource_type="ProjectFile",
        resource_id=pf.id,
        metadata={"project_id": str(project_id), "file_role": file_role.value, "filename": file.filename},
    )

    return DocumentUploadResponse(
        file_id=pf.id,
        storage_key=pf.storage_key,
        parse_status=pf.parse_status,
    )


@router.get("", response_model=list[ProjectFileOut])
async def list_documents(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    storage: StorageClient = Depends(get_storage),
):
    svc = DocumentService(session, storage, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.list_for_project(project_id)


@router.get("/{file_id}/download-url")
async def get_download_url(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    storage: StorageClient = Depends(get_storage),
):
    svc = DocumentService(session, storage, uuid.UUID(tenant_id), uuid.UUID(user_id))
    url = await svc.get_presigned_url(file_id)
    return {"download_url": url}
