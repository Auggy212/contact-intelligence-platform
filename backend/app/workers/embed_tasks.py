"""
Embed task: chunk a parsed document's clauses, embed the chunks, and persist to
Postgres (clause_embeddings) + the vector store. Runs in the "parsing" queue,
after parse_document_task has written the ParsedClause rows.

Celery workers are sync; the async service is driven via asyncio.run().
"""

import asyncio

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.embed_tasks.embed_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def embed_document_task(self, file_id: str, tenant_id: str) -> dict:
    """Embed all chunks for a parsed document. Idempotent (safe to retry)."""
    from app.services.embedding_service import embed_document

    try:
        return asyncio.run(embed_document(file_id, tenant_id))
    except Exception as exc:
        logger.error("embed_task_failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc)
