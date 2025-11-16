"""Redis client helper."""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from ...config import get_settings


class RedisStore:
    """Wrapper around redis client for namespaced operations."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

    @property
    def client(self) -> aioredis.Redis:
        return self._client

    async def push_dialog(self, user_id: str, message: dict[str, Any]) -> None:
        key = f"dialog:{user_id}"
        await self._client.rpush(key, json.dumps(message))

    async def fetch_dialog(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        key = f"dialog:{user_id}"
        length = await self._client.llen(key)
        start = max(length - limit, 0)
        raw_items = await self._client.lrange(key, start, -1)
        return [json.loads(item) for item in raw_items]

    async def set_json(self, key: str, value: dict[str, Any], expire: int | None = None) -> None:
        await self._client.set(key, json.dumps(value), ex=expire)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self._client.get(key)
        return json.loads(raw) if raw else None

    async def close(self) -> None:
        await self._client.close()
