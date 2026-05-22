import uuid

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.organization import Organization, Workspace
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, WorkspaceCreate, WorkspaceUpdate


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, data: OrganizationCreate) -> Organization:
        slug = slugify(data.name)
        existing = await self._db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Organization with slug '{slug}' already exists")

        org = Organization(
            clerk_org_id=data.clerk_org_id,
            name=data.name,
            slug=slug,
            logo_url=data.logo_url,
        )
        self._db.add(org)
        await self._db.flush()
        return org

    async def get_by_id(self, org_id: uuid.UUID) -> Organization:
        result = await self._db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError(f"Organization {org_id} not found")
        return org

    async def get_by_clerk_id(self, clerk_org_id: str) -> Organization | None:
        result = await self._db.execute(
            select(Organization).where(Organization.clerk_org_id == clerk_org_id)
        )
        return result.scalar_one_or_none()

    async def update(self, org_id: uuid.UUID, data: OrganizationUpdate) -> Organization:
        org = await self.get_by_id(org_id)
        if data.name is not None:
            org.name = data.name
        if data.logo_url is not None:
            org.logo_url = data.logo_url
        await self._db.flush()
        return org


class WorkspaceService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def create(self, data: WorkspaceCreate) -> Workspace:
        ws = Workspace(
            organization_id=self._tenant_id,
            name=data.name,
            description=data.description,
        )
        self._db.add(ws)
        await self._db.flush()
        return ws

    async def list_all(self) -> list[Workspace]:
        result = await self._db.execute(
            select(Workspace).where(
                Workspace.organization_id == self._tenant_id,
                Workspace.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, ws_id: uuid.UUID) -> Workspace:
        result = await self._db.execute(
            select(Workspace).where(
                Workspace.id == ws_id,
                Workspace.organization_id == self._tenant_id,
            )
        )
        ws = result.scalar_one_or_none()
        if not ws:
            raise NotFoundError(f"Workspace {ws_id} not found")
        return ws

    async def update(self, ws_id: uuid.UUID, data: WorkspaceUpdate) -> Workspace:
        ws = await self.get_by_id(ws_id)
        if data.name is not None:
            ws.name = data.name
        if data.description is not None:
            ws.description = data.description
        await self._db.flush()
        return ws
