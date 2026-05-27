import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import STORAGE_KEY_PATTERN, FileRole
from app.core.exceptions import NotFoundError
from app.integrations.storage_client import StorageClient
from app.models.project import ProjectFile
from app.parsers.normalizer import SUPPORTED_MIME_TYPES, parse_document


class DocumentService:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageClient,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self._db = db
        self._storage = storage
        self._tenant_id = tenant_id
        self._user_id = user_id

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Make filename safe for use in S3/MinIO object keys and presigned URLs.
        Replaces spaces and special characters (except . - _) with underscores.
        """
        name = filename.strip()
        # Separate extension so we don't mangle it
        if "." in name:
            base, ext = name.rsplit(".", 1)
            safe_base = re.sub(r"[^\w\-]", "_", base)
            safe_ext = re.sub(r"[^\w]", "", ext)
            name = f"{safe_base}.{safe_ext}"
        else:
            name = re.sub(r"[^\w\-]", "_", name)
        # Collapse multiple underscores
        name = re.sub(r"_+", "_", name)
        return name or "document"

    def _storage_key(self, project_id: uuid.UUID, file_role: FileRole, filename: str) -> str:
        safe_filename = self._sanitize_filename(filename)
        return STORAGE_KEY_PATTERN.format(
            tenant_id=str(self._tenant_id),
            project_id=str(project_id),
            file_role=file_role.value,
            filename=safe_filename,
        )

    @staticmethod
    def _resolve_mime(mime_type: str, filename: str) -> str:
        """
        Browsers sometimes send wrong MIME types for DOCX/PDF.
        Fall back to filename extension so uploads never fail on MIME alone.
        """
        if mime_type in SUPPORTED_MIME_TYPES:
            return mime_type
        name_lower = filename.lower()
        if name_lower.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if name_lower.endswith(".pdf"):
            return "application/pdf"
        return mime_type  # will be rejected below

    async def upload(
        self,
        project_id: uuid.UUID,
        file_role: FileRole,
        filename: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> ProjectFile:
        # Normalise MIME type before validation — browsers often lie
        mime_type = self._resolve_mime(mime_type, filename)

        if mime_type not in SUPPORTED_MIME_TYPES:
            from app.core.exceptions import ValidationError
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
            raise ValidationError(
                f"'{filename}' has an unsupported file type (.{ext}). "
                "Only .docx (Word) and .pdf files are accepted. "
                "Please convert your document and try again."
            )

        # Reject duplicate role upload — one file per role per project
        existing = await self._db.execute(
            select(ProjectFile).where(
                ProjectFile.project_id == project_id,
                ProjectFile.organization_id == self._tenant_id,
                ProjectFile.file_role == file_role,
            )
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate is not None:
            from app.core.exceptions import ValidationError
            role_label = {"A": "Template (A)", "B": "Proposed Draft (B)", "C": "Vendor Reply (C)"}
            label = role_label.get(file_role.value, file_role.value)
            raise ValidationError(
                f"A file is already uploaded as '{label}' in this project "
                f"('{duplicate.original_filename}'). "
                "Each project slot can only hold one file. "
                "If you want to replace it, please delete the existing file first."
            )

        storage_key = self._storage_key(project_id, file_role, filename)
        await self._storage.upload(storage_key, file_bytes, content_type=mime_type)

        pf = ProjectFile(
            project_id=project_id,
            organization_id=self._tenant_id,
            uploaded_by_user_id=self._user_id,
            file_role=file_role,
            original_filename=filename,
            storage_key=storage_key,
            file_size_bytes=len(file_bytes),
            mime_type=mime_type,
            parse_status="pending",
        )
        self._db.add(pf)
        await self._db.flush()
        return pf

    async def get_by_id(self, file_id: uuid.UUID) -> ProjectFile:
        result = await self._db.execute(
            select(ProjectFile).where(
                ProjectFile.id == file_id,
                ProjectFile.organization_id == self._tenant_id,
            )
        )
        pf = result.scalar_one_or_none()
        if not pf:
            raise NotFoundError("File not found")
        return pf

    async def list_for_project(self, project_id: uuid.UUID) -> list[ProjectFile]:
        result = await self._db.execute(
            select(ProjectFile).where(
                ProjectFile.project_id == project_id,
                ProjectFile.organization_id == self._tenant_id,
            )
        )
        return list(result.scalars().all())

    async def download_bytes(self, file_id: uuid.UUID) -> tuple[ProjectFile, bytes]:
        pf = await self.get_by_id(file_id)
        data = await self._storage.download(pf.storage_key)
        return pf, data

    async def get_presigned_url(self, file_id: uuid.UUID, expires: int = 3600) -> str:
        pf = await self.get_by_id(file_id)
        return await self._storage.presigned_url(pf.storage_key, expires)
