"""Knowledge base related schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import BaseSchema


class DocumentSource(BaseSchema):
    """Metadata about uploaded document."""

    id: str
    title: str
    description: Optional[str] = None
    category: str = Field(default="general")
    owner_id: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    content_type: str = Field(default="application/octet-stream")
    original_filename: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    checksum: Optional[str] = None
    status: str = Field(default="indexed")


class KnowledgeIngestRequest(BaseSchema):
    """Request to ingest text into knowledge base."""

    text: str
    source_id: str
    metadata: dict | None = None


class KnowledgeSearchHit(BaseSchema):
    """Search hit from knowledge base."""

    id: str
    score: float
    text: str
    metadata: dict | None = None


class KnowledgeSearchResponse(BaseSchema):
    """Vector search response."""

    hits: list[KnowledgeSearchHit]
    query: str
    embedding_available: bool = True
