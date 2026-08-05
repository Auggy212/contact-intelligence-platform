"""
Unit tests for concrete embedding providers (Phase 6.2).

Focus: the NVIDIA NIM provider (default) behaves correctly against an
OpenAI-compatible endpoint, with the client mocked so no live key/network is
needed. Also verifies the factory now recognises "nvidia", and the semantic
property (paraphrases embed closer than unrelated text) via a fake vector space.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.ai.providers.base import EmbeddingProvider
from app.ai.providers.factory import get_embedding_provider


# ─────────────────────────────────────────────────────────────────────────────
# Factory recognises NVIDIA
# ─────────────────────────────────────────────────────────────────────────────

class TestFactoryNvidia:
    def test_nvidia_selected(self):
        prov = get_embedding_provider("nvidia")
        assert isinstance(prov, EmbeddingProvider)
        assert prov.name == "nvidia"

    def test_nvidia_dimension(self):
        from app.core.config import settings

        prov = get_embedding_provider("nvidia")
        assert prov.dimension == settings.NVIDIA_EMBEDDING_DIM


# ─────────────────────────────────────────────────────────────────────────────
# NVIDIA provider: correct call shape against OpenAI-compatible client (mocked)
# ─────────────────────────────────────────────────────────────────────────────

class TestNvidiaEmbedding:
    def _mock_client_returning(self, vectors: list[list[float]]) -> MagicMock:
        client = MagicMock()
        resp = MagicMock()
        resp.data = [MagicMock(embedding=v) for v in vectors]
        client.embeddings.create.return_value = resp
        return client

    def test_embed_returns_one_vector_per_input(self):
        from app.ai.providers.cloud import NvidiaEmbeddingProvider

        prov = NvidiaEmbeddingProvider()
        fake = self._mock_client_returning([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        with patch.object(prov, "_ensure_client", return_value=fake):
            out = prov.embed(["clause one", "clause two"])
        assert out == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        # Called the OpenAI-compatible embeddings API with the configured model.
        _, kwargs = fake.embeddings.create.call_args
        assert kwargs["input"] == ["clause one", "clause two"]

    def test_embed_one(self):
        from app.ai.providers.cloud import NvidiaEmbeddingProvider

        prov = NvidiaEmbeddingProvider()
        fake = self._mock_client_returning([[1.0, 0.0]])
        with patch.object(prov, "_ensure_client", return_value=fake):
            assert prov.embed_one("hello") == [1.0, 0.0]

    def test_missing_key_gives_clear_error(self):
        from app.ai.providers.cloud import NvidiaEmbeddingProvider
        from app.core.config import settings

        prov = NvidiaEmbeddingProvider()
        original = settings.NVIDIA_API_KEY
        settings.NVIDIA_API_KEY = ""  # type: ignore[assignment]
        try:
            with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
                prov._ensure_client()
        finally:
            settings.NVIDIA_API_KEY = original  # type: ignore[assignment]


# ─────────────────────────────────────────────────────────────────────────────
# Local provider: real semantic behaviour (skipped if sentence-transformers absent)
# ─────────────────────────────────────────────────────────────────────────────

class TestLocalEmbeddingSemantics:
    def test_paraphrase_closer_than_unrelated(self):
        st = pytest.importorskip("sentence_transformers")  # noqa: F841
        from app.ai.providers.local import LocalEmbeddingProvider

        prov = LocalEmbeddingProvider()
        a = prov.embed_one("The vendor shall retain all intellectual property.")
        b = prov.embed_one("IP rights remain with the supplier.")          # paraphrase
        c = prov.embed_one("Payment is due within thirty days of invoice.")  # unrelated

        def cos(x, y):
            dot = sum(i * j for i, j in zip(x, y))
            nx = sum(i * i for i in x) ** 0.5
            ny = sum(j * j for j in y) ** 0.5
            return dot / (nx * ny)

        assert cos(a, b) > cos(a, c)
