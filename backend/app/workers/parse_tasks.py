"""
Parse task: download a file from storage, parse it, persist clauses to DB + Qdrant.
Runs in the "parsing" Celery queue.

Celery workers are sync; async code must use asyncio.run().
"""

import asyncio
import uuid

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.parse_tasks.parse_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def parse_document_task(self, file_id: str, tenant_id: str) -> dict:
    """
    Downloads a ProjectFile, parses it into clauses, persists to DB + Qdrant.
    Returns summary dict with clause count.
    """
    try:
        return asyncio.run(_parse_document_async(file_id, tenant_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _parse_document_async(file_id: str, tenant_id: str) -> dict:
    from app.core.database import get_db
    from app.integrations.storage_client import get_storage_client
    from app.integrations.voyage_client import embed_texts
    from app.integrations.qdrant_client import ensure_collection, tenant_collection_name, upsert_vectors
    from app.models.project import ProjectFile
    from app.models.clause import ParsedClause
    from app.parsers.normalizer import parse_document
    from sqlalchemy import select

    storage = get_storage_client()
    collection_name = tenant_collection_name(tenant_id)

    async for session in get_db(tenant_id):
        result = await session.execute(
            select(ProjectFile).where(ProjectFile.id == uuid.UUID(file_id))
        )
        pf = result.scalar_one_or_none()
        if not pf:
            logger.error("parse_task_file_not_found", file_id=file_id)
            return {"error": "file_not_found"}

        pf.parse_status = "processing"
        await session.flush()

        try:
            from app.core.config import settings
            file_bytes = await storage.download(pf.storage_key)
            parsed = parse_document(file_bytes, pf.original_filename, pf.mime_type)

            clauses = parsed["clauses"]

            # Skip embeddings + Qdrant when running in testing mode (no real API keys)
            if settings.is_testing:
                for clause_data in clauses:
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
            else:
                texts = [c["body_text"] for c in clauses]
                embeddings = await embed_texts(texts) if texts else []

                qdrant_points = []
                for clause_data, embedding in zip(clauses, embeddings):
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
                        embedding=embedding,
                    )
                    session.add(pc)
                    await session.flush()

                    qdrant_points.append({
                        "id": str(pc.id),
                        "vector": embedding,
                        "payload": {
                            "file_id": str(pf.id),
                            "project_id": str(pf.project_id),
                            "organization_id": str(pf.organization_id),
                            "clause_number": clause_data.get("clause_number"),
                            "heading": clause_data.get("heading"),
                            "paragraph_index": clause_data["paragraph_index"],
                        },
                    })

                if qdrant_points:
                    await ensure_collection(collection_name)
                    await upsert_vectors(collection_name, qdrant_points)

            pf.parse_status = "completed"
            await session.flush()

            logger.info("parse_task_complete", file_id=file_id, clauses=len(clauses))
            return {"file_id": file_id, "clauses_parsed": len(clauses)}

        except Exception as exc:
            pf.parse_status = "failed"
            await session.flush()
            logger.error("parse_task_failed", file_id=file_id, error=str(exc))
            raise
