import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PLAN_LIMITS, FileRole, ProjectStatus, SubscriptionPlan
from app.core.exceptions import NotFoundError, QuotaExceededError
from app.models.billing import Subscription
from app.models.project import Project, ProjectFile
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def _check_project_quota(self) -> None:
        """Raises QuotaExceededError if tenant has hit their monthly project limit."""
        result = await self._db.execute(
            select(Subscription).where(Subscription.organization_id == self._tenant_id)
        )
        sub = result.scalar_one_or_none()
        plan = sub.plan if sub else SubscriptionPlan.TRIAL
        limit = PLAN_LIMITS[plan]["projects_per_month"]

        if limit == -1:
            return

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        count_result = await self._db.execute(
            select(func.count(Project.id)).where(
                Project.organization_id == self._tenant_id,
                Project.created_at >= month_start,
            )
        )
        count = count_result.scalar_one()
        if count >= limit:
            raise QuotaExceededError(
                f"Monthly project limit of {limit} reached. Please upgrade your plan."
            )

    async def create(self, data: ProjectCreate) -> Project:
        await self._check_project_quota()
        project = Project(
            organization_id=self._tenant_id,
            workspace_id=data.workspace_id,
            created_by_user_id=self._user_id,
            name=data.name,
            description=data.description,
        )
        self._db.add(project)
        await self._db.flush()
        return project

    async def list_all(self, skip: int = 0, limit: int = 20) -> list[Project]:
        result = await self._db.execute(
            select(Project)
            .where(Project.organization_id == self._tenant_id)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, project_id: uuid.UUID) -> Project:
        result = await self._db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == self._tenant_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def update(self, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        project = await self.get_by_id(project_id)
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.status is not None:
            project.status = data.status
        await self._db.flush()
        return project

    async def delete(self, project_id: uuid.UUID) -> None:
        project = await self.get_by_id(project_id)
        await self._db.delete(project)
        await self._db.flush()
