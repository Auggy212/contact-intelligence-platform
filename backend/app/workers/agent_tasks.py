"""
Agent task: runs one AI agent for a given task_id.
Propagates tenant_id through every DB call inside the task.
Runs in the "agents" Celery queue.
"""

import asyncio
import uuid

from app.workers.celery_app import celery_app
from app.core.constants import TaskStatus, TaskType
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.agent_tasks.run_agent_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_agent_task(self, task_id: str, tenant_id: str) -> dict:
    try:
        return asyncio.run(_run_agent_async(task_id, tenant_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _run_agent_async(task_id: str, tenant_id: str) -> dict:
    from app.core.database import get_db
    from app.models.task import AnalysisTask, TaskResult
    from app.models.clause import ParsedClause, ClauseFlag
    from app.agents import (
        TemplateComparisonAgent,
        VendorDiffAgent,
        LawValidatorAgent,
        ChecklistValidatorAgent,
    )
    from sqlalchemy import select

    async for session in get_db(tenant_id):
        # Load the task (RLS-scoped to tenant)
        result = await session.execute(
            select(AnalysisTask).where(
                AnalysisTask.id == uuid.UUID(task_id),
                AnalysisTask.organization_id == uuid.UUID(tenant_id),
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            logger.error("agent_task_not_found", task_id=task_id)
            return {"error": "task_not_found"}

        task.status = TaskStatus.RUNNING
        task.celery_task_id = str(uuid.uuid4())  # placeholder — real ID set below
        await session.flush()

        try:
            # Load all parsed clauses for this project
            clauses_result = await session.execute(
                select(ParsedClause).where(ParsedClause.project_id == task.project_id)
            )
            all_clauses = clauses_result.scalars().all()

            def clauses_for_file(file_id: str) -> list[dict]:
                """Return clause dicts for a specific file_id."""
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

            file_ids = task.input_file_ids or []
            context = {
                "project_id": str(task.project_id),
                "tenant_id": tenant_id,
            }

            if task.task_type == TaskType.TEMPLATE_COMPARISON:
                # file_ids[0] = template A, file_ids[1] = proposed draft B
                context["clauses_a"] = clauses_for_file(file_ids[0]) if len(file_ids) > 0 else []
                context["clauses_b"] = clauses_for_file(file_ids[1]) if len(file_ids) > 1 else []
                agent = TemplateComparisonAgent()

            elif task.task_type == TaskType.VENDOR_DIFF:
                # file_ids[0] = proposed draft B, file_ids[1] = vendor reply C
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
                        ChecklistRule.organization_id == uuid.UUID(tenant_id),
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
                full_text = "\n\n".join(c["body_text"] for c in target_clauses)
                context["full_text"] = full_text
                context["rules"] = rules
                agent = ChecklistValidatorAgent()

            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            result_data = await agent.run(context)

            # Build a map of clause IDs that actually exist in this project
            valid_clause_ids = {str(c.id) for c in all_clauses}

            # Persist findings as ClauseFlag rows
            for finding in result_data.get("findings", []):
                source_id = finding.get("source_clause_id")
                # Only persist if source_clause_id is a real, loaded clause
                if source_id and source_id in valid_clause_ids:
                    clause_uuid = uuid.UUID(source_id)
                elif all_clauses:
                    # Use first clause of target file as a safe fallback reference
                    target_file_id = file_ids[0] if file_ids else None
                    fallback = next(
                        (c for c in all_clauses if str(c.file_id) == target_file_id),
                        all_clauses[0],
                    )
                    clause_uuid = fallback.id
                else:
                    continue  # No clauses at all — skip this finding

                flag = ClauseFlag(
                    clause_id=clause_uuid,
                    task_id=task.id,
                    project_id=task.project_id,
                    organization_id=uuid.UUID(tenant_id),
                    flag_type=finding["flag_type"],
                    severity=finding["severity"],
                    title=finding["title"],
                    description=finding["description"],
                    recommendation=finding.get("recommendation"),
                    source_clause_id=uuid.UUID(source_id) if source_id and source_id in valid_clause_ids else None,
                    confidence=finding.get("confidence"),
                    reasoning_trace=finding.get("reasoning_trace"),
                    risk_score=finding.get("risk_score"),
                    law_act_name=finding.get("law_act_name"),
                    law_section_number=finding.get("law_section_number"),
                    law_retrieved_text=finding.get("law_retrieved_text"),
                    law_jurisdiction=finding.get("law_jurisdiction"),
                )
                session.add(flag)

            # Persist task result
            tr = TaskResult(
                task_id=task.id,
                organization_id=uuid.UUID(tenant_id),
                raw_output=result_data,
                token_usage=result_data.get("token_usage"),
            )
            session.add(tr)

            task.status = TaskStatus.COMPLETED
            task.model_version = result_data.get("model_version")
            task.prompt_version = result_data.get("prompt_version")
            await session.flush()

            # Increment usage counters: 1 contract processed + AI tokens consumed
            from app.services.billing_service import BillingService
            from app.core.database import get_db_no_rls
            token_usage = result_data.get("token_usage", {}) or {}
            total_tokens = (
                token_usage.get("input_tokens", 0) + token_usage.get("output_tokens", 0)
            )
            async for billing_session in get_db_no_rls():
                billing = BillingService(billing_session)
                await billing.increment_usage(
                    uuid.UUID(tenant_id),
                    contracts=1,
                    ai_tokens=total_tokens,
                )
                await billing_session.commit()

            findings_count = len(result_data.get("findings", []))
            logger.info("agent_task_complete", task_id=task_id, findings=findings_count)
            return {"task_id": task_id, "findings": findings_count}

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)[:1024]
            await session.flush()
            logger.error("agent_task_failed", task_id=task_id, error=str(exc))
            raise
