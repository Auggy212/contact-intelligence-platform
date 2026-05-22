import voyageai

from app.core.config import settings
from app.core.exceptions import AIError
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: voyageai.AsyncClient | None = None


def get_voyage_client() -> voyageai.AsyncClient:
    global _client
    if _client is None:
        _client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
    return _client


async def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embeds a list of texts using voyage-law-2.
    input_type: "document" for indexing, "query" for search queries.
    Returns list of 1024-dimensional float vectors.
    """
    if not texts:
        return []

    client = get_voyage_client()
    try:
        result = await client.embed(
            texts,
            model=settings.VOYAGE_MODEL,
            input_type=input_type,
        )
        logger.debug("voyage_embed", count=len(texts), model=settings.VOYAGE_MODEL)
        return result.embeddings
    except Exception as exc:
        logger.error("voyage_embed_error", error=str(exc))
        raise AIError(f"Voyage embedding error: {exc}") from exc


async def embed_query(query: str) -> list[float]:
    """Convenience wrapper for single query embedding."""
    embeddings = await embed_texts([query], input_type="query")
    return embeddings[0]
