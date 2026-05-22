# =============================================================================
# Contract Intelligence Platform — Makefile
# =============================================================================
# Prerequisites: Docker Desktop (or Docker Engine + Compose plugin)
#
# FIRST TIME SETUP (any machine, any OS):
#   make setup
#
# DAILY DEVELOPMENT:
#   make dev       — start everything (API, worker, DB, Redis, MinIO, Qdrant)
#   make logs      — tail all service logs
#   make stop      — stop all containers
#
# WHEN COMPANY PROVIDES MANAGED SERVICES (RDS, ElastiCache, S3, etc.):
#   1. Fill in the company connection details in .env
#   2. Comment out the relevant service blocks in docker-compose.yml
#   3. Run: make dev-app   (starts only api + worker, no local infra)
#
# TESTING:
#   make test      — run full test suite inside Docker
#   make test-unit — unit tests only
#
# DATABASE:
#   make migrate           — apply all pending Alembic migrations
#   make migration m="msg" — generate a new migration file
#   make db-shell          — open a psql shell in the DB container
# =============================================================================

.PHONY: help setup dev dev-app dev-detached stop restart logs logs-api \
        logs-worker test test-unit test-integration test-cov \
        migrate migration db-shell db-shell-test shell worker-shell \
        build build-prod clean clean-images seed-law \
        _check_docker _copy_env _build _infra_up _wait_db _migrate _seed_test_db

# Show help by default
help:
	@echo ""
	@echo "  Contract Intelligence Platform"
	@echo ""
	@echo "  First time on any machine:"
	@echo "    make setup"
	@echo ""
	@echo "  Every day:"
	@echo "    make dev"
	@echo ""
	@echo "  Run tests:"
	@echo "    make test"
	@echo ""
	@echo "  Create a migration after model changes:"
	@echo "    make migration m=\"describe your change\""
	@echo ""


# ── First-time Setup ──────────────────────────────────────────────────────────
# Runs in order: check docker → copy env → build images → start infra →
# wait for DB → run migrations → create test DB

setup: _check_docker _copy_env _build _infra_up _wait_db _migrate _seed_test_db
	@echo ""
	@echo "  Setup complete."
	@echo "  Run 'make dev' to start the full development stack."
	@echo ""

_check_docker:
	@docker info > /dev/null 2>&1 || \
		(echo "" && echo "  ERROR: Docker is not running. Start Docker Desktop first." && echo "" && exit 1)

_copy_env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ""; \
		echo "  Copied .env.example -> .env"; \
		echo "  Open .env and fill in any values marked TODO before running services."; \
		echo ""; \
	else \
		echo "  .env already exists — skipping copy."; \
	fi

_build:
	@echo "  Building Docker images..."
	@docker compose build --quiet
	@echo "  Images built."

_infra_up:
	@echo "  Starting infrastructure services..."
	@docker compose up -d db redis minio qdrant
	@docker compose up -d minio-init
	@echo "  Infrastructure started."

_wait_db:
	@echo "  Waiting for Postgres to be ready..."
	@until docker compose exec -T db pg_isready -U cipuser -d cipdb > /dev/null 2>&1; do \
		printf "."; sleep 1; \
	done
	@echo ""
	@echo "  Postgres is ready."

_migrate:
	@echo "  Running database migrations..."
	@docker compose run --rm -e DATABASE_URL=postgresql+asyncpg://cipuser:cippassword@db:5432/cipdb api alembic upgrade head
	@echo "  Migrations applied."

_seed_test_db:
	@echo "  Creating test database..."
	@docker compose exec -T db psql -U cipuser -d cipdb -tc \
		"SELECT 1 FROM pg_database WHERE datname='cipdb_test'" | grep -q 1 || \
		docker compose exec -T db psql -U cipuser -d cipdb -c "CREATE DATABASE cipdb_test"
	@docker compose exec -T db psql -U cipuser -d cipdb_test -c \
		"CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pgcrypto;" > /dev/null 2>&1 || true
	@echo "  Test database ready."


# ── Development ───────────────────────────────────────────────────────────────

dev: _check_docker
	docker compose up

dev-detached: _check_docker
	docker compose up -d
	@echo "  Stack running in background. Use 'make logs' to follow output."

# Use this when company provides managed infra — only starts app + worker
dev-app: _check_docker
	@echo "  Starting app services only (using externally provided infra from .env)..."
	docker compose up api worker beat

stop:
	docker compose stop
	@echo "  All containers stopped. Data volumes are preserved."

restart:
	docker compose restart api worker

logs:
	docker compose logs -f --tail=100

logs-api:
	docker compose logs -f --tail=100 api

logs-worker:
	docker compose logs -f --tail=100 worker


# ── Testing ───────────────────────────────────────────────────────────────────

test: _check_docker
	docker compose run --rm -e APP_ENV=testing api pytest tests/ -q --tb=short

test-unit: _check_docker
	docker compose run --rm -e APP_ENV=testing api pytest tests/unit/ -q --tb=short

test-integration: _check_docker
	docker compose run --rm -e APP_ENV=testing api pytest tests/integration/ -v --tb=short

test-cov: _check_docker
	docker compose run --rm -e APP_ENV=testing api \
		pytest tests/ --cov=app --cov-report=term-missing -q

# Run only the tenant isolation test suite (marked CRITICAL in the plan)
test-isolation: _check_docker
	docker compose run --rm -e APP_ENV=testing api \
		pytest tests/integration/test_tenant_isolation.py -v --tb=short

# Run the golden-set evaluation harness (requires annotated fixtures)
eval: _check_docker
	@echo "  Running golden-set evaluation..."
	docker compose run --rm api python scripts/run_eval_set.py $(ARGS)


# ── Database ──────────────────────────────────────────────────────────────────

migrate: _check_docker
	docker compose run --rm api alembic upgrade head
	@echo "  Migrations applied."

# Usage: make migration m="add payments table"
migration: _check_docker
	@[ -n "$(m)" ] || \
		(echo "ERROR: provide a message — make migration m=\"your change description\"" && exit 1)
	docker compose run --rm api alembic revision --autogenerate -m "$(m)"
	@echo ""
	@echo "  Review the new file in alembic/versions/ then run: make migrate"
	@echo ""

db-shell:
	docker compose exec db psql -U cipuser -d cipdb

db-shell-test:
	docker compose exec db psql -U cipuser -d cipdb_test


# ── Shells ────────────────────────────────────────────────────────────────────

shell:
	docker compose run --rm api bash

worker-shell:
	docker compose run --rm worker bash


# ── Build & Clean ─────────────────────────────────────────────────────────────

build:
	docker compose build

# Build the production image (multi-stage, no dev deps)
build-prod:
	docker build -f docker/Dockerfile -t contract-intelligence-api:latest .
	@echo "  Production image built: contract-intelligence-api:latest"

# Remove containers and volumes (data is lost — use carefully)
clean:
	docker compose down -v --remove-orphans
	@echo "  All containers and volumes removed."

# Also removes locally built images
clean-images:
	docker compose down --rmi local -v --remove-orphans


# ── Law Corpus ────────────────────────────────────────────────────────────────
# Downloads all 6 Indian law PDFs from indiacode.nic.in (public domain,
# Government of India), extracts text, and seeds into Qdrant.
# Run once during initial deployment. Re-run to refresh the corpus.
#
# Usage:
#   make seed-law              — download + seed (full pipeline)
#   make seed-law ARGS="--download-only"   — download + extract only
#   make seed-law ARGS="--seed-only"       — seed already-downloaded files

seed-law: _check_docker
	@echo "  Downloading Indian law PDFs and seeding Qdrant..."
	@echo "  (Qdrant must be running — use 'make dev-detached' first if needed)"
	docker compose run --rm api python scripts/download_law_corpus.py $(ARGS)
	@echo ""
	@echo "  Law corpus ready. indian_law_corpus collection seeded in Qdrant."
