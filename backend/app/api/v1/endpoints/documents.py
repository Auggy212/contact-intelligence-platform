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
    filename = (file.filename or "").strip()
    if not filename:
        from app.core.exceptions import ValidationError
        raise ValidationError("No filename received. Please select a file before uploading.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        from app.core.exceptions import ValidationError
        raise ValidationError(f"The file '{filename}' is empty. Please upload a valid .docx or .pdf file.")

    if len(file_bytes) > _MAX_SIZE_BYTES:
        size_mb = len(file_bytes) / 1_048_576
        from app.core.exceptions import ValidationError
        raise ValidationError(
            f"'{filename}' is {size_mb:.1f} MB, which exceeds the {_MAX_SIZE_BYTES // 1_048_576} MB limit. "
            "Please compress the file or split it into smaller parts."
        )

    svc = DocumentService(session, storage, uuid.UUID(tenant_id), uuid.UUID(user_id))
    pf = await svc.upload(
        project_id=project_id,
        file_role=file_role,
        filename=filename or "document",
        file_bytes=file_bytes,
        mime_type=file.content_type or "application/octet-stream",
    )

    # In testing mode, parse inline (no Voyage/Qdrant calls, instant completion)
    from app.core.config import settings
    if settings.is_testing:
        from app.parsers.normalizer import parse_document as _parse_doc
        from app.parsers.normalizer import ParseError as _ParseError
        from app.models.clause import ParsedClause
        file_bytes = await storage.download(pf.storage_key)
        try:
            parsed = _parse_doc(file_bytes, pf.original_filename, pf.mime_type)
        except _ParseError as exc:
            pf.parse_status = "failed"
            await session.flush()
            from app.core.exceptions import ValidationError
            raise ValidationError(
                f"Could not read '{pf.original_filename}'. "
                "Make sure it is a valid, non-password-protected .docx or .pdf file. "
                f"Detail: {exc}"
            ) from exc
        if not parsed["clauses"]:
            pf.parse_status = "failed"
            await session.flush()
            from app.core.exceptions import ValidationError
            raise ValidationError(
                f"No text content could be extracted from '{pf.original_filename}'. "
                "The file may be a scanned image PDF or an empty document. "
                "Please upload a text-based document."
            )
        for clause_data in parsed["clauses"]:
            pc = ParsedClause(
                file_id=pf.id,
                project_id=pf.project_id,
                organization_id=pf.organization_id,
                clause_number=(clause_data.get("clause_number") or "")[:64] or None,
                heading=(clause_data.get("heading") or "")[:500] or None,
                body_text=clause_data["body_text"],
                paragraph_index=clause_data["paragraph_index"],
                char_start=clause_data["char_start"],
                char_end=clause_data["char_end"],
                has_tracked_insertion=clause_data["has_tracked_insertion"],
                has_tracked_deletion=clause_data["has_tracked_deletion"],
                has_strikethrough=clause_data["has_strikethrough"],
                has_comment=clause_data["has_comment"],
                change_metadata=clause_data.get("change_metadata", {}),
                embedding=None,
            )
            session.add(pc)
        pf.parse_status = "completed"
        await session.flush()
    else:
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


@router.delete("/{file_id}", status_code=204)
async def delete_document(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    storage: StorageClient = Depends(get_storage),
):
    from sqlalchemy import delete as sql_delete
    from app.models.clause import ParsedClause
    from app.services.audit_service import AuditService
    from app.core.logging import get_logger
    _logger = get_logger(__name__)

    svc = DocumentService(session, storage, uuid.UUID(tenant_id), uuid.UUID(user_id))
    pf = await svc.get_by_id(file_id)

    storage_key = pf.storage_key
    original_filename = pf.original_filename
    file_role = pf.file_role

    # Delete parsed clauses for this file first (FK)
    await session.execute(sql_delete(ParsedClause).where(ParsedClause.file_id == file_id))
    await session.delete(pf)
    await session.flush()

    # Audit the deletion
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action="document.delete",
        resource_type="ProjectFile",
        resource_id=file_id,
        metadata={
            "project_id": str(project_id),
            "file_role": file_role if isinstance(file_role, str) else str(file_role),
            "filename": original_filename,
        },
    )

    # Remove from storage (best-effort)
    try:
        await storage.delete(storage_key)
    except Exception:
        _logger.warning("storage_delete_failed", key=storage_key)


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


@router.get("/{file_id}/content")
async def get_document_content(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    storage: StorageClient = Depends(get_storage),
):
    """
    Stream the ORIGINAL uploaded file bytes, untouched, for in-browser preview.
    Used by the Verify view so the user sees their exact uploaded document
    (no regeneration, no modification). Streaming through the API avoids
    MinIO/S3 CORS issues that would block a direct presigned-URL fetch.
    """
    from fastapi.responses import Response

    svc = DocumentService(session, storage, uuid.UUID(tenant_id), uuid.UUID(user_id))
    pf, data = await svc.download_bytes(file_id)
    return Response(
        content=data,
        media_type=pf.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{pf.original_filename}"',
            # Allow the rendered bytes to be cached briefly by the browser
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/{file_id}/clauses")
async def list_file_clauses(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Return all parsed clauses for a single file in one call, ordered by
    position in the document. Used by the Verify view to map each finding's
    clause_id to its text so it can be located and highlighted in the
    rendered document.
    """
    from sqlalchemy import select
    from app.models.clause import ParsedClause

    result = await session.execute(
        select(ParsedClause)
        .where(
            ParsedClause.file_id == file_id,
            ParsedClause.project_id == project_id,
            ParsedClause.organization_id == uuid.UUID(tenant_id),
        )
        .order_by(ParsedClause.paragraph_index)
    )
    clauses = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "heading": c.heading,
            "clause_number": c.clause_number,
            "body_text": c.body_text,
            "paragraph_index": c.paragraph_index,
            "has_tracked_insertion": c.has_tracked_insertion,
            "has_tracked_deletion": c.has_tracked_deletion,
            "has_strikethrough": c.has_strikethrough,
            "has_comment": c.has_comment,
        }
        for c in clauses
    ]
