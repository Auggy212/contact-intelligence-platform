"""
Local (on-box) provider implementations.

Currently: local embeddings via sentence-transformers (bge). The model is loaded
LAZILY on first embed() so importing this module (and constructing the provider
in the factory) stays cheap and side-effect-free — important for tests and for
the factory's config-selection logic.
"""

from __future__ import annotations

from app.ai.providers.base import EmbeddingProvider
from app.core.config import settings


class LocalEmbeddingProvider(EmbeddingProvider):
    """sentence-transformers embeddings (default: BAAI/bge-small-en-v1.5, 384-dim)."""

    name = "local"

    def __init__(self, model_name: str | None = None, dim: int | None = None) -> None:
        self._model_name = model_name or settings.LOCAL_EMBEDDING_MODEL
        self._dim = dim if dim is not None else settings.LOCAL_EMBEDDING_DIM
        self._model = None  # lazy — loaded on first embed()

    def _ensure_model(self):
        if self._model is None:
            # Imported here so the dependency is only required when actually
            # embedding locally (not when the factory merely constructs this).
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        # normalize_embeddings=True → cosine similarity works directly.
        vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [v.tolist() for v in vectors]

    @property
    def dimension(self) -> int:
        return self._dim
