import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    data: T
    message: str = "success"


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class TimestampSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
