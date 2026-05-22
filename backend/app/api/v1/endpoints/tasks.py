import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, get_user_id, require_reviewer_or_above
from app.schemas.task import ClauseFlagOut, ReviewFlagRequest, TaskOut, TaskTriggerRequest
from app.services.task_service import TaskService
from app.workers.agent_tasks import run_agent_task

router = APIRouter(tags=["Tasks & Findings"])


@router.post("/projects/{project_id}/tasks", response_model=list[TaskOut], status_code=202)
async def trigger_tasks(
    project_id: uuid.UUID,
    data: TaskTriggerRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_reviewer_or_above),
):
    # Quota check: verify tenant hasn't hit their monthly contract limit
    from app.services.billing_service import BillingService
    from app.core.database import get_db_no_rls
    if not getattr(session, "_skip_quota", False):
        billing = BillingService(session)
        await billing.check_task_quota(uuid.UUID(tenant_id))

    svc = TaskService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))

    # Resolve file IDs for this project, keyed by file_role value
    from app.models.project import ProjectFile
    from app.core.constants import TaskType
    from sqlalchemy import select
    files_result = await session.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    # FileRole: A=template, B=proposed, C=vendor_reply
    files = {f.file_role.value: str(f.id) for f in files_result.scalars().all()}

    def _file_ids_for_task(task_type: TaskType) -> list[uuid.UUID]:
        """Route the correct ordered file list to each task type."""
        if task_type == TaskType.TEMPLATE_COMPARISON:
            # Needs template A then proposed B
            return [uuid.UUID(fid) for fid in [files.get("A"), files.get("B")] if fid]
        elif task_type == TaskType.VENDOR_DIFF:
            # Needs proposed B then vendor reply C
            return [uuid.UUID(fid) for fid in [files.get("B"), files.get("C")] if fid]
        else:
            # LAW_VALIDATION and CHECKLIST_VALIDATION: operate on proposed B
            proposed = files.get("B")
            return [uuid.UUID(proposed)] if proposed else []

    from app.services.audit_service import AuditService
    audit_svc = AuditService(session)

    tasks = []
    for task_type in data.task_types:
        input_file_ids = _file_ids_for_task(task_type)
        task = await svc.create_task(project_id, task_type, input_file_ids)
        run_agent_task.delay(str(task.id), tenant_id)
        await audit_svc.log(
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            action="task.create",
            resource_type="AnalysisTask",
            resource_id=task.id,
            metadata={"project_id": str(project_id), "task_type": task_type.value},
        )
        tasks.append(task)

    return tasks


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task_status(
    task_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = TaskService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.get_by_id(task_id)


@router.get("/projects/{project_id}/findings", response_model=list[ClauseFlagOut])
async def list_findings(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    flag_type: str | None = None,
    severity: str | None = None,
    min_risk_score: int | None = None,
    reviewer_status: str | None = None,
):
    from app.models.clause import ClauseFlag
    from sqlalchemy import select
    query = select(ClauseFlag).where(
        ClauseFlag.project_id == project_id,
        ClauseFlag.organization_id == uuid.UUID(tenant_id),
    )
    if flag_type:
        query = query.where(ClauseFlag.flag_type == flag_type)
    if severity:
        query = query.where(ClauseFlag.severity == severity)
    if min_risk_score is not None:
        query = query.where(ClauseFlag.risk_score >= min_risk_score)
    if reviewer_status:
        query = query.where(ClauseFlag.reviewer_status == reviewer_status)
    query = query.order_by(ClauseFlag.severity, ClauseFlag.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


@router.patch("/findings/{flag_id}/review", response_model=ClauseFlagOut)
async def review_finding(
    flag_id: uuid.UUID,
    data: ReviewFlagRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_reviewer_or_above),
):
    from app.models.clause import ClauseFlag, ParsedClause
    from app.core.exceptions import NotFoundError
    from sqlalchemy import select
    result = await session.execute(
        select(ClauseFlag).where(
            ClauseFlag.id == flag_id,
            ClauseFlag.organization_id == uuid.UUID(tenant_id),
        )
    )
    flag = result.scalar_one_or_none()
    if not flag:
        raise NotFoundError("Finding not found")

    flag.reviewer_status = data.status
    flag.reviewer_note = data.note
    flag.reviewed_by_user_id = uuid.UUID(user_id)

    # When a finding is approved, save the clause text to the Clause Library
    # so future reviews can reference pre-approved language.
    if data.status == "approved":
        clause_result = await session.execute(
            select(ParsedClause).where(ParsedClause.id == flag.clause_id)
        )
        clause = clause_result.scalar_one_or_none()
        if clause and clause.body_text:
            from app.services.library_service import ClauseLibraryService
            from app.schemas.library import ClauseLibraryCreate
            lib_svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
            await lib_svc.create(
                ClauseLibraryCreate(
                    title=flag.title,
                    body_text=clause.body_text,
                    category=flag.flag_type,
                    status="approved",
                ),
                uuid.UUID(user_id),
            )

    await session.flush()

    from app.services.audit_service import AuditService
    await AuditService(session).log(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action=f"finding.{data.status}",
        resource_type="ClauseFlag",
        resource_id=flag.id,
        metadata={"flag_type": flag.flag_type, "note": data.note},
    )

    return flag
