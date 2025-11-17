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

    async def embed_text(self, text: str, *, model: str = "simple-tfidf") -> list[float]:
        """Simple text vectorization without external API calls."""
        logger.debug("Embedding text via simple vectorization")
        try:
            # Simple bag-of-words vectorization
            import re
            from collections import Counter
            import math
            
            # Tokenize and clean
            words = re.findall(r'\w+', text.lower())
            if not words:
                return [0.0] * 384  # Return zero vector
            
            # Create a simple hash-based vector (384 dimensions)
            vector = [0.0] * 384
            word_freq = Counter(words)
            
            # Distribute word frequencies across vector dimensions
            for word, freq in word_freq.items():
                # Use word hash to determine vector positions
                word_hash = hash(word)
                for i in range(3):  # Each word affects 3 dimensions
                    idx = (word_hash + i) % 384
                    # TF-IDF approximation: log(1 + freq)
                    vector[idx] += math.log(1 + freq)
            
            # Normalize vector
            magnitude = math.sqrt(sum(x * x for x in vector))
            if magnitude > 0:
                vector = [x / magnitude for x in vector]
            
            return vector
        except Exception as exc:
            logger.exception("Unexpected embedding failure")
            raise EmbeddingServiceUnavailable("Embedding service error") from exc
