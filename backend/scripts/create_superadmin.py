"""
Creates the first superadmin organization and seeds its checklist rules.
Run once after the first deployment or on a fresh local dev setup.

Usage: python scripts/create_superadmin.py
"""

import asyncio
import uuid


async def main():
    from app.core.database import get_db_no_rls
    from app.models.billing import Subscription
    from app.models.organization import Organization
    from sqlalchemy import select

    print("Creating superadmin organization ...")

    async for session in get_db_no_rls():
        # Check if already exists
        result = await session.execute(
            select(Organization).where(Organization.slug == "superadmin")
        )
        if result.scalar_one_or_none():
            print("Superadmin org already exists.")
            return

        org = Organization(
            clerk_org_id="superadmin-clerk-org",
            name="Superadmin",
            slug="superadmin",
            is_active=True,
        )
        session.add(org)
        await session.flush()

        # Create trial subscription
        sub = Subscription(organization_id=org.id)
        session.add(sub)
        await session.commit()

        print(f"Created org: {org.id}")

    # Seed default checklist rules for the new org
    from scripts.seed_checklist_rules import seed_for_org
    await seed_for_org(str(org.id))


if __name__ == "__main__":
    asyncio.run(main())
