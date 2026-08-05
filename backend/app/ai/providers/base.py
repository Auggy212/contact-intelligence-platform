"""
Abstract provider interfaces for the pluggable AI layer (Phase 6).

Every AI operation (embedding, LLM completion, OCR) and the vector store go
through one of these interfaces. Concrete implementations live in local.py /
cloud.py and are selected by config in factory.py — so switching from local
models to a hosted API (or to AWS Bedrock later) is a config change, never a
code change. This is what makes the platform laptop-runnable AND cloud-scalable
without a rewrite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Embeddings
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingProvider(ABC):
    """Turns text into dense vectors. One vector per input string."""

    #: short identifier, e.g. "local", "voyage", "openai"
    name: str = "base"

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input, order-preserved."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension this provider produces (fixed per collection)."""
        raise NotImplementedError

    def embed_one(self, text: str) -> list[float]:
        """Convenience for a single string."""
        return self.embed([text])[0]


# ─────────────────────────────────────────────────────────────────────────────
# LLM completion
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LlmResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LlmProvider(ABC):
    """Generates text from a prompt + grounded context."""

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LlmResult:
        """Single-shot completion. Grounding/citation logic lives in the caller."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# OCR
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OcrResult:
    text: str
    #: optional per-block layout info (bbox, page, confidence) for scanned docs
    blocks: list[dict[str, Any]] = field(default_factory=list)


class OcrProvider(ABC):
    """Extracts text (and optional layout) from image-based documents."""

    name: str = "base"

    @abstractmethod
    def extract(self, file_bytes: bytes, *, content_type: str | None = None) -> OcrResult:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Vector store
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VectorHit:
    id: str
    score: float
    payload: dict[str, Any]


class VectorStore(ABC):
    """
    Persists + searches chunk vectors. Implementations (Qdrant, pgvector) must
    enforce a scope filter (project_id / organization_id) on every search so
    tenant isolation holds at the index level, on top of Postgres RLS.
    """

    name: str = "base"

    @abstractmethod
    def ensure_collection(self, dimension: int) -> None:
        """Idempotently create the collection/index for the given vector dim."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, points: list[dict[str, Any]]) -> None:
        """
        Insert/update vectors. Each point:
          {"id": str, "vector": list[float], "payload": {..., organization_id, project_id}}
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        vector: list[float],
        *,
        scope_filter: dict[str, Any],
        limit: int = 10,
    ) -> list[VectorHit]:
        """Nearest-neighbour search, MANDATORY scope_filter applied server-side."""
        raise NotImplementedError

    @abstractmethod
    def delete_scope(self, scope_filter: dict[str, Any]) -> None:
        """Delete all vectors matching a scope (e.g. a deleted project/org)."""
        raise NotImplementedError
