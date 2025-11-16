"""High level interface for knowledge ingestion and search."""
from __future__ import annotations

import hashlib
import logging
from typing import Iterable

from ...schemas.knowledge import DocumentSource, KnowledgeSearchResponse
from ..ai.gemini_client import GeminiClient
from .opensearch_store import OpenSearchVectorStore

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Facade for embedding content and storing it in OpenSearch."""

    def __init__(self, embedding_model: str = "text-embedding-004") -> None:
        self._gemini = GeminiClient()
        self._store = OpenSearchVectorStore()
        self._embedding_model = embedding_model

    async def initialize(self) -> None:
        await self._store.ensure_indices()

    async def ingest(self, source: DocumentSource, chunks: Iterable[str]) -> None:
        logger.info("Ingesting document %s", source.id)
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{source.id}:{idx}"
            vector = await self._gemini.embed_text(chunk, model=self._embedding_model)
            metadata = source.model_dump()
            metadata.update({"chunk_index": idx})
            await self._store.upsert_document(chunk_id, chunk, vector, metadata)

    async def index_dialog(self, dialog_id: str, text: str, metadata: dict[str, str]) -> None:
        vector = await self._gemini.embed_text(text, model=self._embedding_model)
        await self._store.upsert_dialog(dialog_id, text, vector, metadata)

    async def search(self, query: str, k: int = 5) -> KnowledgeSearchResponse:
        vector = await self._gemini.embed_text(query, model=self._embedding_model)
        hits = await self._store.search(vector, k=k)
        formatted = [
            {
                "id": hit.get("_id"),
                "score": hit.get("_score", 0.0),
                "text": hit.get("_source", {}).get("text", ""),
                "metadata": hit.get("_source", {}).get("metadata", {}),
            }
            for hit in hits
        ]
        return KnowledgeSearchResponse(hits=formatted, query=query)

    @staticmethod
    def compute_checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def aclose(self) -> None:
        await self._store.close()
