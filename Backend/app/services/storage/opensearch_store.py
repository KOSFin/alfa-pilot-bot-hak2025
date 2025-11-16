"""OpenSearch vector storage utilities."""
from __future__ import annotations

import logging
from typing import Any

from opensearchpy import AsyncOpenSearch

from ...config import get_settings

logger = logging.getLogger(__name__)


class OpenSearchVectorStore:
    """Manage vector indices in OpenSearch."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenSearch(settings.opensearch_url)
        self._index_documents = settings.opensearch_index
        self._index_dialogs = settings.opensearch_chat_index
        self._embedding_dim = 768

    @property
    def client(self) -> AsyncOpenSearch:
        return self._client

    async def ensure_indices(self) -> None:
        for index_name in (self._index_documents, self._index_dialogs):
            exists = await self._client.indices.exists(index=index_name)
            if not exists:
                logger.info("Creating OpenSearch index %s", index_name)
                await self._client.indices.create(index=index_name, body=self._build_index_body())

    def _build_index_body(self) -> dict[str, Any]:
        return {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512,
                }
            },
            "mappings": {
                "properties": {
                    "text_vector": {
                        "type": "knn_vector",
                        "dimension": self._embedding_dim,
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                            "space_type": "cosinesimil",
                        },
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "object", "enabled": True},
                }
            },
        }

    async def upsert_document(self, doc_id: str, text: str, vector: list[float], metadata: dict[str, Any]) -> None:
        body = {
            "text": text,
            "text_vector": vector,
            "metadata": metadata,
        }
        await self._client.index(index=self._index_documents, id=doc_id, body=body, refresh=True)

    async def upsert_dialog(self, dialog_id: str, text: str, vector: list[float], metadata: dict[str, Any]) -> None:
        body = {
            "text": text,
            "text_vector": vector,
            "metadata": metadata,
        }
        await self._client.index(index=self._index_dialogs, id=dialog_id, body=body, refresh=True)

    async def search(self, query_vector: list[float], k: int = 5, source: str = "documents") -> list[dict[str, Any]]:
        index = self._index_documents if source == "documents" else self._index_dialogs
        response = await self._client.search(
            index=index,
            body={
                "size": k,
                "query": {
                    "knn": {
                        "text_vector": {
                            "vector": query_vector,
                            "k": k,
                        }
                    }
                },
            },
        )
        hits = response.get("hits", {}).get("hits", [])
        return hits

    async def close(self) -> None:
        await self._client.close()
