"""
User and membership endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, get_user_id, require_admin
from app.models.user import Membership, User
from app.models.organization import Organization
from app.schemas.user import InviteMemberRequest, MembershipOut, UpdateMemberRoleRequest, UserOut
from app.workers.email_tasks import send_invite_email

router = APIRouter(tags=["Users"])


@router.get("/users/me", response_model=UserOut)
async def get_current_user(
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.clerk_user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users", response_model=list[MembershipOut])
async def list_members(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Membership)
        .where(
            Membership.organization_id == uuid.UUID(tenant_id),
            Membership.is_active.is_(True),
        )
        .join(User, User.id == Membership.user_id)
    )
    return result.scalars().all()


@router.post("/users/invite", response_model=MembershipOut, status_code=201, dependencies=[Depends(require_admin)])
async def invite_member(
    data: InviteMemberRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Look up org name for the email
    org_result = await session.execute(
        select(Organization).where(Organization.id == uuid.UUID(tenant_id))
    )
    org = org_result.scalar_one_or_none()
    org_name = org.name if org else "your organization"

    # Find or stub the user record (they may not have signed up yet)
    user_result = await session.execute(
        select(User).where(User.email == data.email)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        # Create a placeholder — they'll complete signup via Clerk
        user = User(
            clerk_user_id=f"pending_{uuid.uuid4().hex}",
            email=data.email,
            full_name=data.email,
            is_active=False,
        )
        session.add(user)
        await session.flush()

    # Check for existing membership
    existing = await session.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == uuid.UUID(tenant_id),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a member of this organization")

    membership = Membership(
        user_id=user.id,
        organization_id=uuid.UUID(tenant_id),
        role=data.role,
        is_active=True,
    )
    session.add(membership)
    await session.flush()

    # Send invite email via Celery (fire-and-forget)
    invite_url = "https://app.contractintelligence.in/accept-invite"
    send_invite_email.delay(data.email, org_name, invite_url)

    return membership


@router.patch("/users/{membership_id}/role", response_model=MembershipOut, dependencies=[Depends(require_admin)])
async def update_member_role(
    membership_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.organization_id == uuid.UUID(tenant_id),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.role = data.role
    await session.flush()
    return membership


@router.delete("/users/{membership_id}", status_code=204, dependencies=[Depends(require_admin)])
async def remove_member(
    membership_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.organization_id == uuid.UUID(tenant_id),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.is_active = False
    await session.flush()
