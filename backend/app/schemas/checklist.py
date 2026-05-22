import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChecklistRuleCreate(BaseModel):
    rule_code: str = Field(..., max_length=16, description="Short code like 'G', 'NOTICE_90', etc.")
    name: str = Field(..., max_length=256)
    description: str | None = None
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    rule_config: dict[str, Any] = Field(..., description="Must include 'type' key.")
    is_enabled: bool = True

    @field_validator("rule_config")
    @classmethod
    def config_must_have_type(cls, v: dict) -> dict:
        if "type" not in v:
            raise ValueError(
                "rule_config must include a 'type' key "
                "(e.g. 'numeric_range', 'string_allowlist', 'boolean_present', 'date_future')"
            )
        return v


class ChecklistRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=256)
    description: str | None = None
    severity: str | None = Field(None, pattern="^(critical|high|medium|low)$")
    rule_config: dict[str, Any] | None = None
    is_enabled: bool | None = None

    @field_validator("rule_config")
    @classmethod
    def config_must_have_type(cls, v: dict | None) -> dict | None:
        if v is not None and "type" not in v:
            raise ValueError("rule_config must include a 'type' key")
        return v


class ChecklistRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    rule_code: str
    name: str
    description: str | None
    severity: str
    rule_config: dict[str, Any]
    is_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
