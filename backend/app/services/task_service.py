import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TaskStatus, TaskType
from app.core.exceptions import NotFoundError
from app.models.task import AnalysisTask, TaskResult


class TaskService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def create_task(
        self,
        project_id: uuid.UUID,
        task_type: TaskType,
        input_file_ids: list[uuid.UUID],
    ) -> AnalysisTask:
        task = AnalysisTask(
            project_id=project_id,
            organization_id=self._tenant_id,
            triggered_by_user_id=self._user_id,
            task_type=task_type,
            status=TaskStatus.QUEUED,
            input_file_ids=[str(fid) for fid in input_file_ids],
        )
        self._db.add(task)
        await self._db.flush()
        return task

    async def get_by_id(self, task_id: uuid.UUID) -> AnalysisTask:
        result = await self._db.execute(
            select(AnalysisTask).where(
                AnalysisTask.id == task_id,
                AnalysisTask.organization_id == self._tenant_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError("Task not found")
        return task

    async def list_for_project(self, project_id: uuid.UUID) -> list[AnalysisTask]:
        result = await self._db.execute(
            select(AnalysisTask).where(
                AnalysisTask.project_id == project_id,
                AnalysisTask.organization_id == self._tenant_id,
            ).order_by(AnalysisTask.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        task_id: uuid.UUID,
        status: TaskStatus,
        celery_task_id: str | None = None,
        error_message: str | None = None,
    ) -> AnalysisTask:
        task = await self.get_by_id(task_id)
        task.status = status
        if celery_task_id:
            task.celery_task_id = celery_task_id
        if error_message:
            task.error_message = error_message
        await self._db.flush()
        return task

    async def save_result(
        self,
        task_id: uuid.UUID,
        raw_output: dict,
        token_usage: dict | None = None,
    ) -> TaskResult:
        result_row = TaskResult(
            task_id=task_id,
            organization_id=self._tenant_id,
            raw_output=raw_output,
            token_usage=token_usage,
        )
        self._db.add(result_row)
        await self._db.flush()
        return result_row
