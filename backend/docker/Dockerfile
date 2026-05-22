# =============================================================================
# Contract Intelligence Platform — Production Dockerfile
# =============================================================================
# Multi-stage build: builder installs all deps, final image is minimal.
# Platform: linux/amd64 (works on x86 servers, AWS, GCP, Azure).
# =============================================================================

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System libraries needed to compile Python packages (lxml, asyncpg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtualenv so the final stage can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

COPY . .

# ── Stage 2: production runtime ───────────────────────────────────────────────
FROM python:3.11-slim

# Runtime system libraries only (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtualenv from builder (all Python packages)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

# Healthcheck so orchestrators (Docker, Kubernetes) know when the app is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
