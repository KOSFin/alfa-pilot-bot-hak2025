"""Common pydantic schema utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    """Base schema with shared config."""

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class TimestampedSchema(BaseSchema):
    """Schema that includes creation timestamp."""

    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseSchema):
    """Generic pagination response."""

    items: list[Dict[str, Any]]
    total: int
    page: int
    size: int
