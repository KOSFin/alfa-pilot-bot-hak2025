"""Conversation persistence and retrieval."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from ...schemas.chat import ChatMessage
from ..storage.redis_store import RedisStore

logger = logging.getLogger(__name__)


class ConversationManager:
    """Stores chat history in Redis and indexes to knowledge base if needed."""

    def __init__(self) -> None:
        self._redis = RedisStore()

    async def append_messages(self, user_id: str, messages: Iterable[ChatMessage]) -> None:
        for message in messages:
            payload = {
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "metadata": message.metadata or {},
            }
            await self._redis.push_dialog(user_id, payload)

    async def get_recent_messages(self, user_id: str, limit: int = 10) -> list[ChatMessage]:
        raw_items = await self._redis.fetch_dialog(user_id, limit=limit)
        history: list[ChatMessage] = []
        for item in raw_items:
            history.append(
                ChatMessage(
                    role=item.get("role", "user"),
                    content=item.get("content", ""),
                    timestamp=datetime.fromisoformat(item.get("timestamp")),
                    metadata=item.get("metadata"),
                )
            )
        return history
