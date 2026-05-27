"""
Debug endpoints — only available when APP_ENV=testing.

Provides a direct DB inspection view of clauses and findings so developers
and demo reviewers can verify that parsing and analysis ran correctly.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_session, get_tenant_id
from app.core.config import settings

router = APIRouter(prefix="/debug", tags=["Debug (testing only)"])


def _require_testing() -> None:
    if not settings.is_testing:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/clauses/{project_id}")
async def debug_clauses(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
):
    """
    Returns all parsed clauses for a project, grouped by file_id.
    Use this to verify document parsing produced sensible results.
    """
    _require_testing()

    from app.models.clause import ParsedClause
    from app.models.project import ProjectFile

    files_result = await session.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = {str(f.id): f for f in files_result.scalars().all()}

    clauses_result = await session.execute(
        select(ParsedClause)
        .where(ParsedClause.project_id == project_id)
        .order_by(ParsedClause.file_id, ParsedClause.paragraph_index)
        .limit(limit)
        .offset(offset)
    )
    clauses = clauses_result.scalars().all()

    count_result = await session.execute(
        select(func.count()).where(ParsedClause.project_id == project_id)
    )
    total = count_result.scalar_one()

    grouped: dict[str, list] = {}
    for c in clauses:
        fid = str(c.file_id)
        if fid not in grouped:
            pf = files.get(fid)
            grouped[fid] = {
                "file_id": fid,
                "filename": pf.original_filename if pf else "unknown",
                "file_role": pf.file_role if pf else "?",
                "parse_status": pf.parse_status if pf else "?",
                "clauses": [],
            }
        grouped[fid]["clauses"].append({
            "id": str(c.id),
            "clause_number": c.clause_number,
            "heading": c.heading,
            "body_text": c.body_text[:300] + ("…" if len(c.body_text or "") > 300 else ""),
            "paragraph_index": c.paragraph_index,
            "has_tracked_insertion": c.has_tracked_insertion,
            "has_tracked_deletion": c.has_tracked_deletion,
            "has_strikethrough": c.has_strikethrough,
        })

    return {
        "project_id": str(project_id),
        "total_clauses": total,
        "showing": len(clauses),
        "offset": offset,
        "files": list(grouped.values()),
    }


@router.get("/findings/{project_id}")
async def debug_findings(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Returns all analysis findings (ClauseFlags) for a project.
    Grouped by task / agent type for easy review.
    """
    _require_testing()

    from app.models.clause import ClauseFlag
    from app.models.task import AnalysisTask

    tasks_result = await session.execute(
        select(AnalysisTask).where(AnalysisTask.project_id == project_id)
    )
    tasks = {str(t.id): t for t in tasks_result.scalars().all()}

    flags_result = await session.execute(
        select(ClauseFlag)
        .where(ClauseFlag.project_id == project_id)
        .order_by(ClauseFlag.task_id, ClauseFlag.severity)
    )
    flags = flags_result.scalars().all()

    grouped: dict[str, dict] = {}
    for f in flags:
        tid = str(f.task_id)
        if tid not in grouped:
            task = tasks.get(tid)
            grouped[tid] = {
                "task_id": tid,
                "task_type": task.task_type if task else "unknown",
                "task_status": task.status if task else "unknown",
                "findings": [],
            }
        grouped[tid]["findings"].append({
            "id": str(f.id),
            "flag_type": f.flag_type,
            "severity": f.severity,
            "title": f.title,
            "description": (f.description or "")[:300],
            "recommendation": (f.recommendation or "")[:200],
            "risk_score": f.risk_score,
            "confidence": f.confidence,
            "law_act_name": f.law_act_name,
            "law_section_number": f.law_section_number,
            "reviewer_status": f.reviewer_status,
        })

    total_findings = len(flags)
    severity_counts: dict[str, int] = {}
    for f in flags:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    return {
        "project_id": str(project_id),
        "total_findings": total_findings,
        "severity_breakdown": severity_counts,
        "tasks": list(grouped.values()),
    }


@router.get("/projects")
async def debug_projects(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Lists all projects and their file upload status for the dev tenant."""
    _require_testing()

    from app.models.project import Project, ProjectFile
    from sqlalchemy import select

    projects_result = await session.execute(
        select(Project).where(Project.organization_id == uuid.UUID(tenant_id))
    )
    projects = projects_result.scalars().all()

    out = []
    for p in projects:
        files_result = await session.execute(
            select(ProjectFile).where(ProjectFile.project_id == p.id)
        )
        files = files_result.scalars().all()
        out.append({
            "id": str(p.id),
            "name": p.name,
            "status": p.status,
            "files": [
                {
                    "id": str(f.id),
                    "filename": f.original_filename,
                    "file_role": f.file_role,
                    "parse_status": f.parse_status,
                    "mime_type": f.mime_type,
                }
                for f in files
            ],
        })

    return {"tenant_id": tenant_id, "projects": out}


@router.get("/subscription")
async def debug_subscription(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Shows subscription and usage record for the dev tenant."""
    _require_testing()
    from app.services.billing_service import BillingService
    billing = BillingService(session)
    sub = await billing.get_subscription(uuid.UUID(tenant_id))
    if not sub:
        return {"error": "no subscription found", "tenant_id": tenant_id}
    return {
        "tenant_id": tenant_id,
        "plan": sub.plan,
        "status": sub.status,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "current_period_start": str(sub.current_period_start) if sub.current_period_start else None,
        "current_period_end": str(sub.current_period_end) if sub.current_period_end else None,
    }
