"""
Provider factory — the single config-driven switch.

Given a provider key (or falling back to the configured default), returns the
right concrete implementation. This is the ONLY place that knows the mapping
from config value → class, so switching providers is a one-line env change.
"""

from __future__ import annotations

from app.ai.providers.base import EmbeddingProvider, LlmProvider, VectorStore
from app.core.config import settings


def get_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    key = (name or settings.EMBEDDING_PROVIDER).lower()
    if key == "nvidia":
        from app.ai.providers.cloud import NvidiaEmbeddingProvider

        return NvidiaEmbeddingProvider()
    if key == "local":
        from app.ai.providers.local import LocalEmbeddingProvider

        return LocalEmbeddingProvider()
    if key == "voyage":
        from app.ai.providers.cloud import VoyageEmbeddingProvider

        return VoyageEmbeddingProvider()
    if key == "openai":
        from app.ai.providers.cloud import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {key!r}")


def get_llm_provider(name: str | None = None) -> LlmProvider:
    key = (name or settings.LLM_PROVIDER).lower()
    if key == "nvidia":
        from app.ai.providers.cloud import NvidiaLlmProvider

        return NvidiaLlmProvider()
    if key == "groq":
        from app.ai.providers.cloud import GroqLlmProvider

        return GroqLlmProvider()
    if key == "gemini":
        from app.ai.providers.cloud import GeminiLlmProvider

        return GeminiLlmProvider()
    if key == "anthropic":
        from app.ai.providers.cloud import AnthropicLlmProvider

        return AnthropicLlmProvider()
    if key == "bedrock":
        from app.ai.providers.cloud import BedrockLlmProvider

        return BedrockLlmProvider()
    raise ValueError(f"Unknown LLM provider: {key!r}")


def get_vector_store(name: str | None = None) -> VectorStore:
    key = (name or settings.VECTOR_STORE).lower()
    # Dimension-scoped collection: each embedding provider's vectors live in their
    # own collection (contract_chunks_1024, _384, …) so switching EMBEDDING_PROVIDER
    # never mixes incompatible dimensions in one index.
    collection = settings.chunk_collection_name
    if key == "qdrant":
        from app.ai.vector_store import QdrantVectorStore

        return QdrantVectorStore(collection=collection)
    if key == "pgvector":
        from app.ai.vector_store import PgVectorStore

        return PgVectorStore()
    raise ValueError(f"Unknown vector store: {key!r}")
