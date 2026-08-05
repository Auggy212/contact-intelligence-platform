"""
Unit tests for the pluggable AI provider layer (Phase 6.1).

Verifies:
  - the abstract interfaces exist with the expected contract
  - the factory selects the correct implementation from config
  - switching a provider is config-only (no code change)
"""

import pytest

from app.ai.providers import base
from app.ai.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
    get_vector_store,
)


# ─────────────────────────────────────────────────────────────────────────────
# Interfaces exist with the expected contract
# ─────────────────────────────────────────────────────────────────────────────

class TestInterfaces:
    def test_embedding_provider_interface(self):
        assert hasattr(base.EmbeddingProvider, "embed")
        assert hasattr(base.EmbeddingProvider, "dimension")

    def test_llm_provider_interface(self):
        assert hasattr(base.LlmProvider, "complete")

    def test_ocr_provider_interface(self):
        assert hasattr(base.OcrProvider, "extract")

    def test_vector_store_interface(self):
        for m in ("upsert", "search", "ensure_collection", "delete_scope"):
            assert hasattr(base.VectorStore, m)

    def test_interfaces_are_abstract(self):
        # Abstract base classes cannot be instantiated directly.
        with pytest.raises(TypeError):
            base.EmbeddingProvider()  # type: ignore[abstract]


# ─────────────────────────────────────────────────────────────────────────────
# Factory selects the right implementation from config
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbeddingFactory:
    def test_local_is_default(self):
        prov = get_embedding_provider("local")
        assert isinstance(prov, base.EmbeddingProvider)
        assert prov.name == "local"

    def test_voyage_selected(self):
        prov = get_embedding_provider("voyage")
        assert prov.name == "voyage"

    def test_openai_selected(self):
        prov = get_embedding_provider("openai")
        assert prov.name == "openai"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_embedding_provider("does-not-exist")


class TestLlmFactory:
    def test_groq_is_default(self):
        prov = get_llm_provider("groq")
        assert isinstance(prov, base.LlmProvider)
        assert prov.name == "groq"

    def test_gemini_selected(self):
        assert get_llm_provider("gemini").name == "gemini"

    def test_anthropic_selected(self):
        assert get_llm_provider("anthropic").name == "anthropic"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_llm_provider("nope")


class TestVectorStoreFactory:
    def test_qdrant_is_default(self):
        store = get_vector_store("qdrant")
        assert isinstance(store, base.VectorStore)
        assert store.name == "qdrant"

    def test_pgvector_selected(self):
        assert get_vector_store("pgvector").name == "pgvector"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_vector_store("nope")

    def test_collection_is_dimension_scoped(self):
        # Each embedding provider's vectors must land in its own dimension-scoped
        # collection so nvidia (1024) and local (384) never collide.
        from app.core.config import settings

        original = settings.EMBEDDING_PROVIDER
        try:
            settings.EMBEDDING_PROVIDER = "nvidia"  # type: ignore[assignment]
            assert get_vector_store("qdrant")._collection == \
                f"contract_chunks_{settings.NVIDIA_EMBEDDING_DIM}"
            settings.EMBEDDING_PROVIDER = "local"  # type: ignore[assignment]
            assert get_vector_store("qdrant")._collection == \
                f"contract_chunks_{settings.LOCAL_EMBEDDING_DIM}"
        finally:
            settings.EMBEDDING_PROVIDER = original  # type: ignore[assignment]


class TestConfigDriven:
    def test_factory_reads_settings_default(self):
        # With no explicit arg, factory falls back to the configured default.
        from app.core.config import settings

        prov = get_embedding_provider()
        assert prov.name == settings.EMBEDDING_PROVIDER
