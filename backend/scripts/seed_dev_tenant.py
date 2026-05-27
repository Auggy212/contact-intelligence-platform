"""
Seed the dev/testing database with a test organization, user, subscription,
and default checklist rules.

Run once after migrations:
    python scripts/seed_dev_tenant.py

These UUIDs match the APP_ENV=testing bypass headers in the frontend and
the TenantMiddleware test bypass.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

DEV_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEV_SUB_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")

engine = create_async_engine(settings.DATABASE_URL, echo=False)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Default checklist rules for the dev org (rule_code A-F)
_DEFAULT_RULES = [
    {
        "id": "00000000-0000-0000-0000-000000000101",
        "rule_code": "A",
        "name": "Agreement Duration",
        "description": "Contract duration must be between 12 and 36 months",
        "severity": "high",
        "rule_config": {"min_months": 12, "max_months": 36},
        "is_enabled": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000102",
        "rule_code": "B",
        "name": "Agreement Date",
        "description": "Agreement date should be a future date",
        "severity": "medium",
        "rule_config": {},
        "is_enabled": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000103",
        "rule_code": "C",
        "name": "Dispute Court Jurisdiction",
        "description": "Dispute resolution must be in Mumbai courts",
        "severity": "high",
        "rule_config": {"allowed_cities": ["Mumbai", "mumbai"]},
        "is_enabled": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000104",
        "rule_code": "D",
        "name": "Advance Payment",
        "description": "Advance payment must not exceed 10% of contract value",
        "severity": "high",
        "rule_config": {"max_percent": 10},
        "is_enabled": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000105",
        "rule_code": "E",
        "name": "Contract Value Threshold",
        "description": "Contract value must be below ₹50,00,000 (50 Lakhs)",
        "severity": "critical",
        "rule_config": {"max_value_inr": 5000000},
        "is_enabled": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000106",
        "rule_code": "F",
        "name": "Termination Notice Period",
        "description": "Termination notice must be 1-3 months",
        "severity": "medium",
        "rule_config": {"min_months": 1, "max_months": 3},
        "is_enabled": True,
    },
]


async def seed():
    now = datetime.now(timezone.utc)
    async with Session() as session:
        # Organization
        await session.execute(
            text("""
                INSERT INTO organizations (id, clerk_org_id, name, slug, is_active, created_at, updated_at)
                VALUES (:id, 'dev_test_org', 'Dev Test Organization', 'dev-test-org', true, :now, :now)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": str(DEV_ORG_ID), "now": now},
        )

        # User
        await session.execute(
            text("""
                INSERT INTO users (id, clerk_user_id, email, full_name, is_active, created_at, updated_at)
                VALUES (:id, 'dev_test_user', 'dev@test.local', 'Dev User', true, :now, :now)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": str(DEV_USER_ID), "now": now},
        )

        # Membership (link user to org as owner)
        await session.execute(
            text("""
                INSERT INTO memberships (id, organization_id, user_id, role, is_active, created_at, updated_at)
                VALUES (gen_random_uuid(), :org_id, :user_id, 'owner', true, :now, :now)
                ON CONFLICT (user_id, organization_id) DO NOTHING
            """),
            {"org_id": str(DEV_ORG_ID), "user_id": str(DEV_USER_ID), "now": now},
        )

        # Subscription — lowercase plan/status values to match StrEnum values
        await session.execute(
            text("""
                INSERT INTO subscriptions (id, organization_id, plan, status, created_at, updated_at)
                VALUES (:id, :org_id, 'trial', 'trialing', :now, :now)
                ON CONFLICT (id) DO UPDATE
                  SET plan = 'trial', status = 'trialing', updated_at = :now
            """),
            {"id": str(DEV_SUB_ID), "org_id": str(DEV_ORG_ID), "now": now},
        )

        # Checklist rules
        for rule in _DEFAULT_RULES:
            rule_config_json = json.dumps(rule["rule_config"])
            await session.execute(
                text(f"""
                    INSERT INTO checklist_rules
                        (id, organization_id, rule_code, name, description, severity,
                         rule_config, is_enabled, created_at, updated_at)
                    VALUES
                        (:id, :org_id, :rule_code, :name, :description, :severity,
                         '{rule_config_json}'::jsonb, :is_enabled, :now, :now)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": rule["id"],
                    "org_id": str(DEV_ORG_ID),
                    "rule_code": rule["rule_code"],
                    "name": rule["name"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "is_enabled": rule["is_enabled"],
                    "now": now,
                },
            )

        await session.commit()

    print("Dev tenant seeded successfully.")
    print(f"  Org ID:            {DEV_ORG_ID}")
    print(f"  User ID:           {DEV_USER_ID}")
    print(f"  Sub ID:            {DEV_SUB_ID}")
    print(f"  Checklist rules:   {len(_DEFAULT_RULES)} rules (A–F)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
