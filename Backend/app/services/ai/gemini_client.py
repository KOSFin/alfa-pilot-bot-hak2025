"""Gemini client wrapper."""
from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from ...config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingServiceUnavailable(RuntimeError):
    """Raised when Gemini embeddings are not available in the current environment."""


class GeminiClient:
    """Async-friendly wrapper around Gemini SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self._model_name_default = "gemini-2.5-pro"

    async def generate_content(self, prompt: str, *, model: str | None = None, tools: list[dict[str, Any]] | None = None) -> str:
        model_name = model or self._model_name_default
        logger.debug("Generating content with Gemini model=%s", model_name)
        response = await asyncio.to_thread(
            lambda: genai.GenerativeModel(model_name, tools=tools).generate_content(prompt)
        )
        return response.text or ""

    async def generate_structured(self, prompt: str, *, schema: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        model_name = model or self._model_name_default
        logger.debug("Generating structured content with schema via Gemini model=%s", model_name)
        generation_schema = self._sanitize_schema(schema)
        if generation_schema != schema:
            logger.debug("Sanitized response schema before calling Gemini")
        response = await asyncio.to_thread(
            lambda: genai.GenerativeModel(model_name).generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": generation_schema,
                },
            )
        )
        if hasattr(response, "parsed") and response.parsed:
            return response.parsed
        if response.text:
            import json

            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse structured response, returning empty dict")
        return {}

    async def embed_text(self, text: str, *, model: str = "text-embedding-004") -> list[float]:
        logger.debug("Embedding text via Gemini model=%s", model)
        try:
            response = await asyncio.to_thread(lambda: genai.embed_content(model=model, content=text))
        except google_exceptions.GoogleAPIError as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini embedding rejected request: %s", exc)
            raise EmbeddingServiceUnavailable("Embedding service unavailable") from exc
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected embedding failure")
            raise EmbeddingServiceUnavailable("Embedding service error") from exc

        embedding = response.get("embedding") if isinstance(response, dict) else None
        if not embedding:
            raise EmbeddingServiceUnavailable("Embedding payload missing")
        return embedding

    @staticmethod
    def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
        """Remove JSON Schema fields unsupported by Gemini response_schema."""

        def _clean(node: Any) -> Any:
            if isinstance(node, dict):
                cleaned: dict[str, Any] = {}
                for key, value in node.items():
                    if key == "additionalProperties":
                        continue
                    cleaned[key] = _clean(value)
                return cleaned
            if isinstance(node, list):
                return [_clean(item) for item in node]
            return node

        return _clean(deepcopy(schema))
