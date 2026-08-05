import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, get_user_id, require_reviewer_or_above
from app.schemas.task import ClauseFlagOut, ReviewFlagRequest, TaskOut, TaskTriggerRequest
from app.services.retrieval_service import get_hybrid_retriever
from app.services.task_service import TaskService
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    from app.services.billing_service import BillingService
    from app.core.constants import TaskType
    from app.models.project import ProjectFile
    from app.services.audit_service import AuditService
    from sqlalchemy import select

    billing = BillingService(session)
    await billing.check_task_quota(uuid.UUID(tenant_id))

    svc = TaskService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))

    # Resolve file IDs for this project, keyed by file_role string ("A", "B", "C").
    # Order by parse_status (completed first) then created_at DESC so that if duplicate
    # uploads exist for a role, we always use the most recently completed one.
    from sqlalchemy import case
    files_result = await session.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(
            case({"completed": 0}, value=ProjectFile.parse_status, else_=1),
            ProjectFile.created_at.desc(),
        )
    )
    # First file seen per role wins (completed + newest first).
    files: dict[str, str] = {}
    for f in files_result.scalars().all():
        role = f.file_role if isinstance(f.file_role, str) else str(f.file_role)
        if role not in files:           # first = completed + newest; skip duplicates
            files[role] = str(f.id)

    _TASK_REQUIRED_FILES = {
        TaskType.TEMPLATE_COMPARISON: ("A", "B"),
        TaskType.VENDOR_DIFF: ("B", "C"),
        TaskType.LAW_VALIDATION: ("B",),
        TaskType.CHECKLIST_VALIDATION: ("B",),
    }
    _ROLE_NAMES = {"A": "Template (A)", "B": "Proposed Draft (B)", "C": "Vendor Reply (C)"}

    def _file_ids_for_task(task_type: TaskType) -> list[uuid.UUID]:
        if task_type == TaskType.TEMPLATE_COMPARISON:
            return [uuid.UUID(fid) for fid in [files.get("A"), files.get("B")] if fid]
        elif task_type == TaskType.VENDOR_DIFF:
            return [uuid.UUID(fid) for fid in [files.get("B"), files.get("C")] if fid]
        else:
            proposed = files.get("B")
            return [uuid.UUID(proposed)] if proposed else []

    # Validate required files are present before creating any tasks
    from app.core.exceptions import ValidationError as _VE
    for task_type in data.task_types:
        missing = [
            _ROLE_NAMES[role]
            for role in _TASK_REQUIRED_FILES.get(task_type, ())
            if role not in files
        ]
        if missing:
            raise _VE(
                f"Cannot run '{task_type.value}': "
                f"the following required file(s) have not been uploaded yet: "
                f"{', '.join(missing)}. "
                "Please upload them first from the Documents tab."
            )

    # ── Purge previous runs for the same task types before creating new ones ──
    # This ensures re-runs replace results rather than accumulate duplicate findings.
    from app.models.task import AnalysisTask as _AT, TaskResult as _TR
    from app.models.clause import ClauseFlag as _CF
    from app.core.constants import TaskType as _TT
    from sqlalchemy import delete

    existing_tasks_result = await session.execute(
        select(_AT).where(
            _AT.project_id == project_id,
            _AT.task_type.in_([t.value for t in data.task_types]),
        )
    )
    existing_tasks = existing_tasks_result.scalars().all()
    if existing_tasks:
        old_task_ids = [t.id for t in existing_tasks]
        await session.execute(delete(_CF).where(_CF.task_id.in_(old_task_ids)))
        await session.execute(delete(_TR).where(_TR.task_id.in_(old_task_ids)))
        await session.execute(delete(_AT).where(_AT.id.in_(old_task_ids)))
        await session.flush()

    audit_svc = AuditService(session)
    tasks = []

    from app.core.config import settings
    for task_type in data.task_types:
        input_file_ids = _file_ids_for_task(task_type)
        task = await svc.create_task(project_id, task_type, input_file_ids)

        if settings.is_testing:
            await _run_agent_inline(task, tenant_id, session)
        else:
            from app.workers.agent_tasks import run_agent_task
            run_agent_task.delay(str(task.id), tenant_id)

        await audit_svc.log(
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            action="task.create",
            resource_type="AnalysisTask",
            resource_id=task.id,
            metadata={"project_id": str(project_id), "task_type": task_type.value},
        )

        # Refresh to load DB-generated timestamps before Pydantic serialization
        await session.refresh(task)
        tasks.append(task)

    return tasks


async def _run_agent_inline(task, tenant_id: str, session: AsyncSession) -> None:
    """Run agent synchronously within the current DB session (testing/demo mode)."""
    import uuid as _uuid
    from app.models.task import TaskResult, AnalysisTask
    from app.models.clause import ParsedClause, ClauseFlag
    from app.core.constants import TaskType, TaskStatus
    from app.agents import (
        TemplateComparisonAgent,
        VendorDiffAgent,
        LawValidatorAgent,
        ChecklistValidatorAgent,
    )
    from sqlalchemy import select

    task.status = TaskStatus.RUNNING
    await session.flush()

    try:
        clauses_result = await session.execute(
            select(ParsedClause).where(ParsedClause.project_id == task.project_id)
        )
        all_clauses = clauses_result.scalars().all()

        def clauses_for_file(file_id: str) -> list[dict]:
            return [
                {
                    "id": str(c.id),
                    "clause_number": c.clause_number,
                    "heading": c.heading,
                    "body_text": c.body_text,
                    "paragraph_index": c.paragraph_index,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "has_tracked_insertion": c.has_tracked_insertion,
                    "has_tracked_deletion": c.has_tracked_deletion,
                    "has_strikethrough": c.has_strikethrough,
                    "has_comment": c.has_comment,
                    "change_metadata": c.change_metadata or {},
                }
                for c in all_clauses
                if str(c.file_id) == file_id
            ]

        file_ids = [str(fid) for fid in (task.input_file_ids or [])]
        context: dict = {
            "project_id": str(task.project_id),
            "tenant_id": tenant_id,
        }

        if task.task_type == TaskType.TEMPLATE_COMPARISON:
            context["clauses_a"] = clauses_for_file(file_ids[0]) if len(file_ids) > 0 else []
            context["clauses_b"] = clauses_for_file(file_ids[1]) if len(file_ids) > 1 else []
            agent = TemplateComparisonAgent()

        elif task.task_type == TaskType.VENDOR_DIFF:
            context["clauses_b"] = clauses_for_file(file_ids[0]) if len(file_ids) > 0 else []
            context["clauses_c"] = clauses_for_file(file_ids[1]) if len(file_ids) > 1 else []
            agent = VendorDiffAgent()

        elif task.task_type == TaskType.LAW_VALIDATION:
            context["clauses"] = clauses_for_file(file_ids[0]) if file_ids else []
            agent = LawValidatorAgent()

        elif task.task_type == TaskType.CHECKLIST_VALIDATION:
            from app.models.checklist import ChecklistRule
            rules_result = await session.execute(
                select(ChecklistRule).where(
                    ChecklistRule.organization_id == _uuid.UUID(tenant_id),
                    ChecklistRule.is_enabled.is_(True),
                )
            )
            rules = [
                {
                    "rule_code": r.rule_code,
                    "name": r.name,
                    "severity": r.severity,
                    "rule_config": r.rule_config,
                }
                for r in rules_result.scalars().all()
            ]
            target_clauses = clauses_for_file(file_ids[0]) if file_ids else []
            context["full_text"] = "\n\n".join(c["body_text"] for c in target_clauses)
            context["rules"] = rules
            agent = ChecklistValidatorAgent()

        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

        result_data = await agent.run(context)

        valid_clause_ids = {str(c.id) for c in all_clauses}
        for finding in result_data.get("findings", []):
            source_id = finding.get("source_clause_id")
            if source_id and source_id in valid_clause_ids:
                clause_uuid = _uuid.UUID(source_id)
            elif all_clauses:
                target_file_id = file_ids[0] if file_ids else None
                fallback = next(
                    (c for c in all_clauses if str(c.file_id) == target_file_id),
                    all_clauses[0],
                )
                clause_uuid = fallback.id
            else:
                continue

            # value_changes may arrive as dataclass instances — store plain dicts
            # so JSONB round-trips (mirrors the Celery worker path).
            raw_vc = finding.get("value_changes") or []
            vc_list = [
                v.__dict__ if hasattr(v, "__dict__") else v
                for v in raw_vc
            ] if raw_vc else None

            flag = ClauseFlag(
                clause_id=clause_uuid,
                task_id=task.id,
                project_id=task.project_id,
                organization_id=_uuid.UUID(tenant_id),
                flag_type=finding["flag_type"],
                severity=finding["severity"],
                title=finding["title"],
                description=finding["description"],
                recommendation=finding.get("recommendation"),
                source_clause_id=_uuid.UUID(source_id) if source_id and source_id in valid_clause_ids else None,
                confidence=finding.get("confidence"),
                reasoning_trace=finding.get("reasoning_trace"),
                risk_score=finding.get("risk_score"),
                clause_type=finding.get("clause_type"),
                value_changes=vc_list,
                law_act_name=finding.get("law_act_name"),
                law_section_number=finding.get("law_section_number"),
                law_retrieved_text=finding.get("law_retrieved_text"),
                law_jurisdiction=finding.get("law_jurisdiction"),
                # These two were missing here — the reason the Fixes tab was
                # always empty in testing/demo mode (this inline path is what
                # actually runs, not the Celery worker).
                suggestion=finding.get("suggestion"),
                priority=finding.get("priority"),
            )
            session.add(flag)

        tr = TaskResult(
            task_id=task.id,
            organization_id=_uuid.UUID(tenant_id),
            raw_output=result_data,
            token_usage=result_data.get("token_usage"),
        )
        session.add(tr)

        task.status = TaskStatus.COMPLETED
        task.model_version = result_data.get("model_version")
        task.prompt_version = result_data.get("prompt_version")
        await session.flush()

    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.error_message = str(exc)[:1024]
        await session.flush()
        raise


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task_status(
    task_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = TaskService(session, uuid.UUID(tenant_id), uuid.UUID(user_id))
    return await svc.get_by_id(task_id)


@router.get("/projects/{project_id}/tasks-list", response_model=list[TaskOut])
async def list_project_tasks(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from app.models.task import AnalysisTask
    from sqlalchemy import select
    result = await session.execute(
        select(AnalysisTask)
        .where(
            AnalysisTask.project_id == project_id,
            AnalysisTask.organization_id == uuid.UUID(tenant_id),
        )
        .order_by(AnalysisTask.created_at.desc())
    )
    return result.scalars().all()


@router.get("/projects/{project_id}/clauses/{clause_id}")
async def get_clause(
    project_id: uuid.UUID,
    clause_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from app.models.clause import ParsedClause
    from app.core.exceptions import NotFoundError
    from sqlalchemy import select
    result = await session.execute(
        select(ParsedClause).where(
            ParsedClause.id == clause_id,
            ParsedClause.project_id == project_id,
            ParsedClause.organization_id == uuid.UUID(tenant_id),
        )
    )
    clause = result.scalar_one_or_none()
    if not clause:
        raise NotFoundError("Clause not found")
    return {
        "id": str(clause.id),
        "heading": clause.heading,
        "clause_number": clause.clause_number,
        "body_text": clause.body_text,
        "paragraph_index": clause.paragraph_index,
        "has_tracked_insertion": clause.has_tracked_insertion,
        "has_tracked_deletion": clause.has_tracked_deletion,
        "has_strikethrough": clause.has_strikethrough,
        "has_comment": clause.has_comment,
    }


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


@router.get("/projects/{project_id}/findings/{flag_id}/similar")
async def find_similar_clauses(
    project_id: uuid.UUID,
    flag_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    limit: int = 5,
):
    """
    Semantically-related clauses IN THE SAME CONTRACT for a finding (Phase 6).

    Powers the 'Related clauses' panel in the finding detail sheet: uses the
    finding's clause text as a query, runs hybrid retrieval scoped to this
    project, and returns related clauses — excluding the finding's own clause.
    Requires ENABLE_EMBEDDINGS (there are no vectors to search otherwise).
    """
    from sqlalchemy import select

    from app.core.config import settings
    from app.core.exceptions import NotFoundError, ValidationError
    from app.models.clause import ClauseFlag, ParsedClause

    # The finding must exist and belong to this tenant/project.
    flag = (await session.execute(
        select(ClauseFlag).where(
            ClauseFlag.id == flag_id,
            ClauseFlag.project_id == project_id,
            ClauseFlag.organization_id == uuid.UUID(tenant_id),
        )
    )).scalar_one_or_none()
    if not flag:
        raise NotFoundError("Finding not found")

    if not settings.ENABLE_EMBEDDINGS:
        raise ValidationError(
            "Semantic features are disabled. Set ENABLE_EMBEDDINGS=true and re-upload "
            "the document so its clauses get embedded."
        )

    # Query text = the finding's clause body (fall back to the finding title).
    clause = (await session.execute(
        select(ParsedClause).where(ParsedClause.id == flag.clause_id)
    )).scalar_one_or_none()
    query_text = (clause.body_text if clause else None) or flag.title

    scope = {"organization_id": tenant_id, "project_id": str(project_id)}
    retriever = get_hybrid_retriever(session)
    # over-fetch by one so we can drop the clause's own chunk and still fill `limit`
    hits = await retriever.retrieve(query_text, scope_filter=scope, limit=limit + 1)

    self_clause_id = str(flag.clause_id)
    results = []
    for h in hits:
        hit_clause_id = str((h.get("payload") or {}).get("clause_id", ""))
        if hit_clause_id == self_clause_id:
            continue  # exclude the finding's own clause
        results.append({
            "clause_id": hit_clause_id,
            "chunk_text": h["chunk_text"],
            "score": h["score"],
        })
        if len(results) >= limit:
            break

    return {"finding_id": str(flag_id), "count": len(results), "results": results}


@router.get("/projects/{project_id}/modifications")
async def list_modifications(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Return all findings that carry a suggested modification, for the
    Modifications summary report. Grouped by priority (must_fix / should_fix /
    optional) and ordered by risk within each group.
    """
    from app.models.clause import ClauseFlag
    from sqlalchemy import select, func

    result = await session.execute(
        select(ClauseFlag).where(
            ClauseFlag.project_id == project_id,
            ClauseFlag.organization_id == uuid.UUID(tenant_id),
            ClauseFlag.suggestion.isnot(None),
            # Exclude JSONB `null` (findings that ran through the suggestion path
            # but produced no concrete fix) — only real suggestion objects.
            func.jsonb_typeof(ClauseFlag.suggestion) == "object",
        )
    )
    flags = result.scalars().all()

    _prio_order = {"must_fix": 0, "should_fix": 1, "optional": 2}
    items = [
        {
            "id": str(f.id),
            "clause_id": str(f.clause_id),
            "flag_type": f.flag_type,
            "severity": f.severity,
            "priority": f.priority or "should_fix",
            "title": f.title,
            "clause_type": f.clause_type,
            "risk_score": f.risk_score,
            "suggestion": f.suggestion,
            "reviewer_status": f.reviewer_status,
        }
        for f in flags
    ]
    items.sort(
        key=lambda x: (_prio_order.get(x["priority"], 1), -(x["risk_score"] or 0))
    )

    counts = {"must_fix": 0, "should_fix": 0, "optional": 0}
    for it in items:
        counts[it["priority"]] = counts.get(it["priority"], 0) + 1

    return {
        "project_id": str(project_id),
        "total": len(items),
        "counts": counts,
        "modifications": items,
    }


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

    if data.status == "approved":
        clause_result = await session.execute(
            select(ParsedClause).where(ParsedClause.id == flag.clause_id)
        )
        clause = clause_result.scalar_one_or_none()
        if clause and clause.body_text:
            try:
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
            except Exception:
                # Clause library requires Voyage AI keys — skip silently in demo mode
                logger.warning("clause_library_skip", flag_id=str(flag.id), reason="library indexing unavailable in demo mode")

    await session.flush()
    await session.refresh(flag)

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
