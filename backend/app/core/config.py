from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # ── Application ───────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    APP_NAME: str = "Contract Intelligence Platform"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = "change-me"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Database ──────────────────────────────────────────────────────────────
    # In Docker Compose: postgresql+asyncpg://cipuser:cippassword@db:5432/cipdb
    # On host machine:   postgresql+asyncpg://cipuser:cippassword@localhost:5432/cipdb
    # Company-provided:  replace entire URL with their connection string
    DATABASE_URL: str = "postgresql+asyncpg://cipuser:cippassword@localhost:5432/cipdb"

    # ── Redis ─────────────────────────────────────────────────────────────────
    # In Docker Compose: redis://redis:6379/0
    # On host machine:   redis://localhost:6379/0
    # Company-provided:  replace with their ElastiCache/Redis URL
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── File Storage ──────────────────────────────────────────────────────────
    # "minio" = local/Docker dev using MinIO (S3-compatible)
    # "s3"    = AWS S3 or any S3-compatible service (company-provided)
    STORAGE_BACKEND: Literal["minio", "s3"] = "minio"

    # MinIO settings (used when STORAGE_BACKEND=minio)
    # In Docker Compose endpoint is "minio:9000", on host it is "localhost:9000"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "contract-intelligence"
    MINIO_SECURE: bool = False

    # AWS S3 settings (used when STORAGE_BACKEND=s3)
    # Also works with any S3-compatible provider (Cloudflare R2, DigitalOcean Spaces)
    # by pointing MINIO_ENDPOINT at their endpoint and keeping STORAGE_BACKEND=minio
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET: str = "contract-intelligence"

    # ── Auth (Clerk) ──────────────────────────────────────────────────────────
    CLERK_SECRET_KEY: str = "sk_test_placeholder"
    CLERK_PUBLISHABLE_KEY: str = "pk_test_placeholder"
    CLERK_WEBHOOK_SECRET: str = "whsec_placeholder"

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = "sk-ant-placeholder"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_OPUS_MODEL: str = "claude-opus-4-7"

    # ── Voyage AI (embeddings) ────────────────────────────────────────────────
    VOYAGE_API_KEY: str = "pa-placeholder"
    VOYAGE_MODEL: str = "voyage-law-2"

    # ── Qdrant (vector database) ──────────────────────────────────────────────
    # In Docker Compose: http://qdrant:6333
    # On host machine:   http://localhost:6333
    # Qdrant Cloud:      https://your-cluster.qdrant.io (set QDRANT_API_KEY too)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_LAW_COLLECTION: str = "indian_law_corpus"

    # ── Pluggable AI providers (Phase 6 — semantic/RAG) ──────────────────────
    # Each capability switches INDEPENDENTLY via env var, no code change.
    # Defaults: NVIDIA NIM embeddings (free tier, retrieval-tuned, OpenAI-compatible)
    # with local bge as an offline fallback.
    #   EMBEDDING_PROVIDER: nvidia | local | voyage | openai
    #   LLM_PROVIDER:       nvidia | groq | gemini | anthropic | bedrock
    #   VECTOR_STORE:       qdrant | pgvector
    EMBEDDING_PROVIDER: Literal["nvidia", "local", "voyage", "openai"] = "nvidia"
    LLM_PROVIDER: Literal["nvidia", "groq", "gemini", "anthropic", "bedrock"] = "groq"
    VECTOR_STORE: Literal["qdrant", "pgvector"] = "qdrant"

    # Master switch for the Phase 6 semantic pipeline (embed-on-upload + search).
    # Kept INDEPENDENT of APP_ENV on purpose: you can run the app in `testing`
    # mode (easy auth) AND still exercise real embeddings by setting this true.
    # The pytest suite forces it FALSE so automated tests never spend API credits.
    ENABLE_EMBEDDINGS: bool = False

    # NVIDIA NIM (build.nvidia.com) — OpenAI-compatible endpoint, key starts nvapi-.
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_EMBEDDING_MODEL: str = "nvidia/nv-embedqa-e5-v5"
    NVIDIA_EMBEDDING_DIM: int = 1024
    NVIDIA_LLM_MODEL: str = "meta/llama-3.3-70b-instruct"

    # Local embedding model (sentence-transformers). bge-small = 384 dims.
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    LOCAL_EMBEDDING_DIM: int = 384

    # Free hosted-API LLM keys (only the chosen provider's key is needed).
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── Billing (Stripe) ──────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = "sk_test_placeholder"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_placeholder"
    STRIPE_WEBHOOK_SECRET: str = "whsec_placeholder"
    STRIPE_PRICE_STARTER: str = "price_placeholder"
    STRIPE_PRICE_PROFESSIONAL: str = "price_placeholder"

    # ── Email ─────────────────────────────────────────────────────────────────
    # "console" = print to stdout (dev mode, no real emails)
    # "resend"  = send via Resend API (staging/production)
    EMAIL_BACKEND: Literal["console", "resend"] = "console"
    RESEND_API_KEY: str = "re_placeholder"
    EMAIL_FROM: str = "noreply@contractintelligence.in"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"

    @property
    def using_real_ai_keys(self) -> bool:
        """True when actual API keys are set (not placeholders)."""
        return (
            not self.ANTHROPIC_API_KEY.startswith("sk-ant-placeholder")
            and not self.VOYAGE_API_KEY.startswith("pa-placeholder")
        )

    @property
    def active_embedding_dim(self) -> int:
        """
        Vector dimension of the CURRENTLY selected embedding provider. Different
        providers produce different dims (nvidia 1024, local bge 384, openai 1536,
        voyage 1024). Used to keep each provider's vectors in its OWN collection so
        switching EMBEDDING_PROVIDER never mixes incompatible dimensions.
        """
        return {
            "nvidia": self.NVIDIA_EMBEDDING_DIM,
            "local": self.LOCAL_EMBEDDING_DIM,
            "openai": 1536,   # text-embedding-3-small
            "voyage": 1024,   # voyage-law-2
        }.get(self.EMBEDDING_PROVIDER, self.NVIDIA_EMBEDDING_DIM)

    @property
    def chunk_collection_name(self) -> str:
        """Qdrant collection for chunk vectors, suffixed by the active dimension so
        e.g. nvidia (1024) and local (384) never collide in one collection."""
        return f"contract_chunks_{self.active_embedding_dim}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
