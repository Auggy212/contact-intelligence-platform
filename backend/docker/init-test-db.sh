#!/bin/sh
# Runs inside the Dockerfile.dev container after DB is healthy.
# 1. Applies all Alembic migrations to cipdb
# 2. Creates cipdb_test with vector and pgcrypto extensions
set -e

echo "==> Running Alembic migrations on cipdb..."
alembic upgrade head
echo "    Migrations applied."

echo "==> Creating test database cipdb_test..."
python - <<'PYEOF'
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        "postgresql://cipuser:cippassword@db:5432/cipdb"
    )
    rows = await conn.fetch(
        "SELECT 1 FROM pg_database WHERE datname = 'cipdb_test'"
    )
    if not rows:
        # CREATE DATABASE cannot run inside a transaction block
        await conn.execute("COMMIT")
        await conn.execute("CREATE DATABASE cipdb_test")
        print("    Created cipdb_test")
    else:
        print("    cipdb_test already exists")
    await conn.close()

    conn2 = await asyncpg.connect(
        "postgresql://cipuser:cippassword@db:5432/cipdb_test"
    )
    await conn2.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn2.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    await conn2.close()
    print("    Extensions installed in cipdb_test")

asyncio.run(main())
PYEOF

echo "==> Setup complete."
