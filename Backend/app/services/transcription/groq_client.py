"""Groq Whisper transcription client."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import BinaryIO

import httpx

from ...config import get_settings

logger = logging.getLogger(__name__)


class GroqTranscriber:
    """Async client for Groq Whisper transcription API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.groq_api_key
        self._api_url = settings.groq_api_url
        self._http_client = httpx.AsyncClient(timeout=60.0)

    async def transcribe(self, file: BinaryIO, filename: str, *, language: str = "ru", prompt: str | None = None) -> dict:
        logger.info("Transcribing audio via Groq Whisper with language: %s", language)

        files = {
            "file": (filename, file, "audio/mpeg"),
            "model": (None, "whisper-large-v3-turbo"),
            "temperature": (None, "0"),
            "response_format": (None, "verbose_json"),
            "language": (None, language),
        }
        if prompt:
            files["prompt"] = (None, prompt)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
        }
        logger.debug("Making request to: %s with headers: %s", self._api_url, {k: v if k != "Authorization" else "[HIDDEN]" for k, v in headers.items()})
        response = await self._http_client.post(self._api_url, files=files, headers=headers)
        response.raise_for_status()
        payload = response.json()
        logger.debug("Groq transcription response: %s", json.dumps(payload)[:512])
        return payload

    async def transcribe_file(self, path: Path, **kwargs) -> dict:
        loop = asyncio.get_running_loop()
        with path.open("rb") as file:
            data = file.read()
        return await loop.run_in_executor(None, self._transcribe_bytes, data, path.name, kwargs)

    def _transcribe_bytes(self, data: bytes, filename: str, kwargs: dict) -> dict:
        import anyio

        async def _inner() -> dict:
            async with httpx.AsyncClient(timeout=60.0) as client:

                files = {
                    "file": (filename, data, "audio/mpeg"),
                    "model": (None, "whisper-large-v3-turbo"),
                    "temperature": (None, "0"),
                    "response_format": (None, "verbose_json"),
                    "language": (None, kwargs.get("language", "ru")),
                }
                if kwargs.get("prompt"):
                    files["prompt"] = (None, kwargs["prompt"])
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                }
                response = await client.post(self._api_url, files=files, headers=headers)
                response.raise_for_status()
                return response.json()

        return anyio.run(_inner)

    async def aclose(self) -> None:
        await self._http_client.aclose()
