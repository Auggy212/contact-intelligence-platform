# =============================================================================
# Contract Intelligence Platform — Celery Worker Dockerfile
# =============================================================================
# Used by docker-compose.yml for the "worker" and "beat" services.
# NOTE: --pool=solo is NOT used here — that flag is Windows-only.
#       Inside Linux containers, normal multiprocessing works correctly.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# App code is mounted as a volume at runtime via docker-compose volumes.

CMD ["celery", "-A", "app.workers.celery_app", "worker", \
     "--loglevel=info", "--concurrency=4", "-Q", "parsing,agents,email"]
