"""
Seeds the 6 default Indian law checklist rules for every organization
that doesn't already have them.

Run: python scripts/seed_checklist_rules.py <org_id>
Or:  python scripts/seed_checklist_rules.py --all
"""

import asyncio
import sys
import uuid

DEFAULT_RULES = [
    {
        "rule_code": "A",
        "name": "Agreement Duration",
        "description": "Contract duration must be between 12 and 36 months",
        "severity": "critical",
        "rule_config": {"min_months": 12, "max_months": 36},
        "is_default": True,
    },
    {
        "rule_code": "B",
        "name": "Agreement Date",
        "description": "Agreement date must be a future date (not past or today)",
        "severity": "critical",
        "rule_config": {},
        "is_default": True,
    },
    {
        "rule_code": "C",
        "name": "Dispute Settlement Court",
        "description": "Dispute resolution must be in Mumbai, Maharashtra",
        "severity": "high",
        "rule_config": {"allowed_cities": ["mumbai"]},
        "is_default": True,
    },
    {
        "rule_code": "D",
        "name": "Advance Payment Cap",
        "description": "Advance payment cannot exceed 10% of total project value",
        "severity": "high",
        "rule_config": {"max_percent": 10},
        "is_default": True,
    },
    {
        "rule_code": "E",
        "name": "Contract Value Limit",
        "description": "Contract value must be below INR 50 Lakhs (₹50,00,000)",
        "severity": "medium",
        "rule_config": {"max_value_inr": 5_000_000},
        "is_default": True,
    },
    {
        "rule_code": "F",
        "name": "Termination Notice Period",
        "description": "Termination notice must be between 1 and 3 months",
        "severity": "critical",
        "rule_config": {"min_months": 1, "max_months": 3},
        "is_default": True,
    },
]


async def seed_for_org(org_id: str) -> None:
    from app.core.database import get_db_no_rls
    from app.models.checklist import ChecklistRule
    from sqlalchemy import select

    print(f"Seeding checklist rules for org {org_id} ...")

    async for session in get_db_no_rls():
        for rule_data in DEFAULT_RULES:
            existing = await session.execute(
                select(ChecklistRule).where(
                    ChecklistRule.organization_id == uuid.UUID(org_id),
                    ChecklistRule.rule_code == rule_data["rule_code"],
                )
            )
            if existing.scalar_one_or_none():
                print(f"  Rule {rule_data['rule_code']} already exists, skipping.")
                continue

            rule = ChecklistRule(
                organization_id=uuid.UUID(org_id),
                **rule_data,
            )
            session.add(rule)

        await session.commit()
        print(f"  Done. {len(DEFAULT_RULES)} default rules seeded for org {org_id}.")


async def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/seed_checklist_rules.py <org_id> [<org_id> ...]")
        print("       python scripts/seed_checklist_rules.py --all")
        sys.exit(1)

    if args[0] == "--all":
        from app.core.database import get_db_no_rls
        from app.models.organization import Organization
        from sqlalchemy import select
        async for session in get_db_no_rls():
            result = await session.execute(select(Organization).where(Organization.is_active.is_(True)))
            orgs = result.scalars().all()
            for org in orgs:
                await seed_for_org(str(org.id))
    else:
        for org_id in args:
            await seed_for_org(org_id)


if __name__ == "__main__":
    asyncio.run(main())
