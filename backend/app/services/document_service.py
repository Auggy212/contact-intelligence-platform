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

    def _storage_key(self, project_id: uuid.UUID, file_role: FileRole, filename: str) -> str:
        return STORAGE_KEY_PATTERN.format(
            tenant_id=str(self._tenant_id),
            project_id=str(project_id),
            file_role=file_role.value,
            filename=filename,
        )

    async def upload(
        self,
        project_id: uuid.UUID,
        file_role: FileRole,
        filename: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> ProjectFile:
        if mime_type not in SUPPORTED_MIME_TYPES:
            from app.core.exceptions import ValidationError
            raise ValidationError(f"Unsupported file type: {mime_type}")

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
