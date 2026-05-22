import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.checklist import ChecklistRule
from app.schemas.checklist import ChecklistRuleCreate, ChecklistRuleUpdate


class ChecklistService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def create(self, data: ChecklistRuleCreate, user_id: uuid.UUID) -> ChecklistRule:
        rule = ChecklistRule(
            organization_id=self._tenant_id,
            created_by_user_id=user_id,
            rule_code=data.rule_code,
            name=data.name,
            description=data.description,
            severity=data.severity,
            rule_config=data.rule_config,
        )
        self._db.add(rule)
        await self._db.flush()
        return rule

    async def list_enabled(self) -> list[ChecklistRule]:
        result = await self._db.execute(
            select(ChecklistRule).where(
                ChecklistRule.organization_id == self._tenant_id,
                ChecklistRule.is_enabled.is_(True),
            ).order_by(ChecklistRule.rule_code)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[ChecklistRule]:
        result = await self._db.execute(
            select(ChecklistRule).where(
                ChecklistRule.organization_id == self._tenant_id,
            ).order_by(ChecklistRule.rule_code)
        )
        return list(result.scalars().all())

    async def get_by_id(self, rule_id: uuid.UUID) -> ChecklistRule:
        result = await self._db.execute(
            select(ChecklistRule).where(
                ChecklistRule.id == rule_id,
                ChecklistRule.organization_id == self._tenant_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundError("Checklist rule not found")
        return rule

    async def update(self, rule_id: uuid.UUID, data: ChecklistRuleUpdate) -> ChecklistRule:
        rule = await self.get_by_id(rule_id)
        if data.name is not None:
            rule.name = data.name
        if data.description is not None:
            rule.description = data.description
        if data.severity is not None:
            rule.severity = data.severity
        if data.rule_config is not None:
            rule.rule_config = data.rule_config
        if data.is_enabled is not None:
            rule.is_enabled = data.is_enabled
        await self._db.flush()
        return rule

    async def delete(self, rule_id: uuid.UUID) -> None:
        rule = await self.get_by_id(rule_id)
        await self._db.delete(rule)
        await self._db.flush()
