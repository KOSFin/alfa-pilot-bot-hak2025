"""Redis client helper with in-memory fallback."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from fnmatch import fnmatch
from typing import Any, DefaultDict

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from ...config import get_settings

logger = logging.getLogger(__name__)

_memory_lock = asyncio.Lock()
_memory_lists: DefaultDict[str, list[str]] = defaultdict(list)
_memory_json: dict[str, str] = {}


class RedisStore:
    """Wrapper around Redis with graceful degradation to in-memory storage."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        self._use_memory_only = False

    def _mark_unavailable(self, exc: Exception) -> None:
        if not self._use_memory_only:
            logger.warning("Redis unavailable, switching to in-memory store: %s", exc)
        self._use_memory_only = True

    def _can_use_redis(self) -> bool:
        return not self._use_memory_only and self._client is not None

    async def push_dialog(self, user_id: str, message: dict[str, Any]) -> None:
        key = f"dialog:{user_id}"
        payload = json.dumps(message)
        if self._can_use_redis():
            try:
                await self._client.rpush(key, payload)
                return
            except (RedisError, OSError) as exc:  # pragma: no cover - network failure
                self._mark_unavailable(exc)
        async with _memory_lock:
            _memory_lists[key].append(payload)

    async def fetch_dialog(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        key = f"dialog:{user_id}"
        if self._can_use_redis():
            try:
                length = await self._client.llen(key)
                start = max(length - limit, 0)
                raw_items = await self._client.lrange(key, start, -1)
                return [json.loads(item) for item in raw_items]
            except (RedisError, OSError) as exc:  # pragma: no cover - network failure
                self._mark_unavailable(exc)
        async with _memory_lock:
            items = _memory_lists.get(key, [])[-limit:]
            return [json.loads(item) for item in items]

    async def set_json(self, key: str, value: dict[str, Any], expire: int | None = None) -> None:
        payload = json.dumps(value)
        if self._can_use_redis():
            try:
                await self._client.set(key, payload, ex=expire)
                return
            except (RedisError, OSError) as exc:  # pragma: no cover - network failure
                self._mark_unavailable(exc)
        async with _memory_lock:
            _memory_json[key] = payload

    async def get_json(self, key: str) -> dict[str, Any] | None:
        if self._can_use_redis():
            try:
                raw = await self._client.get(key)
                return json.loads(raw) if raw else None
            except (RedisError, OSError) as exc:  # pragma: no cover - network failure
                self._mark_unavailable(exc)
        async with _memory_lock:
            raw = _memory_json.get(key)
            return json.loads(raw) if raw else None

    async def delete(self, key: str) -> None:
        if self._can_use_redis():
            try:
                await self._client.delete(key)
                return
            except (RedisError, OSError) as exc:  # pragma: no cover - network failure
                self._mark_unavailable(exc)
        async with _memory_lock:
            _memory_json.pop(key, None)
            _memory_lists.pop(key, None)

    async def keys(self, pattern: str) -> list[str]:
        if self._can_use_redis():
            try:
                return await self._client.keys(pattern)
            except (RedisError, OSError) as exc:  # pragma: no cover - network failure
                self._mark_unavailable(exc)
        async with _memory_lock:
            return [key for key in _memory_json if fnmatch(key, pattern)]

    async def close(self) -> None:
        if self._client and not self._use_memory_only:
            await self._client.close()
