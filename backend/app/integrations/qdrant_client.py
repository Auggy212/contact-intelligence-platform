from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.core.constants import EMBEDDING_DIMENSIONS
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
    return _client


def tenant_collection_name(tenant_id: str) -> str:
    """Each tenant gets their own Qdrant collection for their Clause Library."""
    return f"clause_library_{tenant_id.replace('-', '_')}"


async def ensure_collection(collection_name: str) -> None:
    client = get_qdrant_client()
    exists = await client.collection_exists(collection_name)
    if not exists:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE,
            ),
        )
        logger.info("qdrant_collection_created", collection=collection_name)


async def upsert_vectors(
    collection_name: str,
    points: list[dict],  # [{"id": str, "vector": list[float], "payload": dict}]
) -> None:
    client = get_qdrant_client()
    await ensure_collection(collection_name)
    structs = [
        PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {}))
        for p in points
    ]
    await client.upsert(collection_name=collection_name, points=structs)
    logger.debug("qdrant_upsert", collection=collection_name, count=len(structs))


async def search_vectors(
    collection_name: str,
    query_vector: list[float],
    top_k: int = 5,
    score_threshold: float = 0.75,
) -> list[dict]:
    client = get_qdrant_client()
    results = await client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
    )
    return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results.points]


async def delete_vector(collection_name: str, point_id: str) -> None:
    from qdrant_client.models import PointIdsList
    client = get_qdrant_client()
    await client.delete(
        collection_name=collection_name,
        points_selector=PointIdsList(points=[point_id]),
    )
