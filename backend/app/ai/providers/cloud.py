"""
Hosted-API provider implementations (embeddings + LLMs).

All clients are constructed LAZILY on first use, so the factory can instantiate
these to check config selection without needing API keys or network access
(critical for tests and offline runs). A provider only requires its key when a
call is actually made.

Providers:
  Embeddings: Voyage (voyage-law-2), OpenAI (text-embedding-3-small)
  LLM:        Groq (default, free tier), Gemini (free tier), Anthropic, Bedrock
"""

from __future__ import annotations

from app.ai.providers.base import EmbeddingProvider, LlmProvider, LlmResult
from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Embedding providers
# ─────────────────────────────────────────────────────────────────────────────

class VoyageEmbeddingProvider(EmbeddingProvider):
    name = "voyage"
    _DIM = 1024  # voyage-law-2

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            import voyageai

            self._client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        result = client.embed(texts, model=settings.VOYAGE_MODEL, input_type="document")
        return result.embeddings

    @property
    def dimension(self) -> int:
        return self._DIM


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"
    _DIM = 1536  # text-embedding-3-small

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        resp = client.embeddings.create(model=settings.OPENAI_EMBEDDING_MODEL, input=texts)
        return [d.embedding for d in resp.data]

    @property
    def dimension(self) -> int:
        return self._DIM


class NvidiaEmbeddingProvider(EmbeddingProvider):
    """
    NVIDIA NIM embeddings (build.nvidia.com) — the default.

    NVIDIA exposes an OpenAI-COMPATIBLE endpoint, so we reuse the OpenAI client
    pointed at NVIDIA's base URL with an nvapi- key. The model (nv-embedqa-*) is
    retrieval-tuned, which is exactly what a RAG pipeline wants. Free tier for
    dev/demo; swap to a paid tier or another provider via env only.
    """

    name = "nvidia"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            if not settings.NVIDIA_API_KEY:
                raise RuntimeError(
                    "NVIDIA_API_KEY is not set. Get a free key at build.nvidia.com "
                    "(starts with 'nvapi-') and add it to backend/.env."
                )
            from openai import OpenAI

            self._client = OpenAI(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
            )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        # NVIDIA retrieval models need input_type ("passage" for indexed docs).
        resp = client.embeddings.create(
            model=settings.NVIDIA_EMBEDDING_MODEL,
            input=texts,
            extra_body={"input_type": "passage", "truncate": "END"},
        )
        return [d.embedding for d in resp.data]

    def embed_query(self, text: str) -> list[float]:
        """Query-side embedding — NVIDIA retrieval models use input_type='query'."""
        client = self._ensure_client()
        resp = client.embeddings.create(
            model=settings.NVIDIA_EMBEDDING_MODEL,
            input=[text],
            extra_body={"input_type": "query", "truncate": "END"},
        )
        return resp.data[0].embedding

    @property
    def dimension(self) -> int:
        return settings.NVIDIA_EMBEDDING_DIM


# ─────────────────────────────────────────────────────────────────────────────
# LLM providers
# ─────────────────────────────────────────────────────────────────────────────

class GroqLlmProvider(LlmProvider):
    """Groq — free tier, very fast (default LLM)."""

    name = "groq"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LlmResult:
        client = self._ensure_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        usage = resp.usage
        return LlmResult(
            text=resp.choices[0].message.content or "",
            model=settings.GROQ_MODEL,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
        )


class NvidiaLlmProvider(LlmProvider):
    """NVIDIA NIM LLM (e.g. Llama-3.3-70B) via the OpenAI-compatible endpoint."""

    name = "nvidia"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            if not settings.NVIDIA_API_KEY:
                raise RuntimeError(
                    "NVIDIA_API_KEY is not set. Get a free key at build.nvidia.com "
                    "(starts with 'nvapi-') and add it to backend/.env."
                )
            from openai import OpenAI

            self._client = OpenAI(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
            )
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LlmResult:
        client = self._ensure_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=settings.NVIDIA_LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        usage = resp.usage
        return LlmResult(
            text=resp.choices[0].message.content or "",
            model=settings.NVIDIA_LLM_MODEL,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
        )


class GeminiLlmProvider(LlmProvider):
    """Google Gemini — free tier, large context window."""

    name = "gemini"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._client = genai.GenerativeModel(settings.GEMINI_MODEL)
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LlmResult:
        model = self._ensure_client()
        full = f"{system}\n\n{prompt}" if system else prompt
        resp = model.generate_content(
            full,
            generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        return LlmResult(text=resp.text or "", model=settings.GEMINI_MODEL)


class AnthropicLlmProvider(LlmProvider):
    """Anthropic Claude — production quality."""

    name = "anthropic"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LlmResult:
        client = self._ensure_client()
        resp = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        return LlmResult(
            text=text,
            model=settings.ANTHROPIC_MODEL,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )


class BedrockLlmProvider(LlmProvider):
    """
    AWS Bedrock (Claude via AWS) — the production/AWS switch. Same model family
    as Anthropic, different endpoint. Wired lazily; requires boto3 + AWS creds.
    """

    name = "bedrock"

    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client("bedrock-runtime")
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LlmResult:
        import json

        client = self._ensure_client()
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system or "",
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = client.invoke_model(modelId=settings.ANTHROPIC_MODEL, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        text = "".join(b.get("text", "") for b in payload.get("content", []))
        return LlmResult(text=text, model=settings.ANTHROPIC_MODEL)
