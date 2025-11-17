"""Gemini client wrapper."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from ...config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingServiceUnavailable(RuntimeError):
    """Raised when embeddings are not available in the current environment."""


class GeminiClient:
    """Async-friendly wrapper around OpenAI-compatible API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            base_url="https://ai.megallm.io/v1",
            api_key=settings.gemini_api_key
        )
        self._model_name_default = "gemini-2.5-flash"

    async def generate_content(self, prompt: str, *, model: str | None = None, tools: list[dict[str, Any]] | None = None) -> str:
        model_name = model or self._model_name_default
        logger.debug("Generating content with model=%s", model_name)
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self._client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools if tools else None
            )
            return response.choices[0].message.content or ""
        except OpenAIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise
        except Exception as exc:
            logger.exception("Unexpected error generating content")
            raise

    async def generate_structured(self, prompt: str, *, schema: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        model_name = model or self._model_name_default
        logger.debug("Generating structured content with schema via model=%s", model_name)
        try:
            messages = [
                {"role": "system", "content": "You must respond with valid JSON that matches the provided schema."},
                {"role": "user", "content": prompt}
            ]
            response = await self._client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content or "{}"
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse structured response, returning empty dict")
                return {}
        except OpenAIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise
        except Exception as exc:
            logger.exception("Unexpected error generating structured content")
            raise

    async def embed_text(self, text: str, *, model: str = "text-embedding-3-small") -> list[float]:
        logger.debug("Embedding text via model=%s", model)
        try:
            response = await self._client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except OpenAIError as exc:
            logger.warning("Embedding API rejected request: %s", exc)
            raise EmbeddingServiceUnavailable("Embedding service unavailable") from exc
        except Exception as exc:
            logger.exception("Unexpected embedding failure")
            raise EmbeddingServiceUnavailable("Embedding service error") from exc
