"""Voice message handler."""
from __future__ import annotations

import io

import httpx
from aiogram import F, Router
from aiogram.types import Message

from app.config import get_settings
from app.services.transcription.groq_client import GroqTranscriber
from bot.utils.onboarding import ensure_onboarding_ready

router = Router()


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    voice = message.voice
    if not voice:
        return

    allowed, _ = await ensure_onboarding_ready(message)
    if not allowed:
        return

    settings = get_settings()
    bot = message.bot
    file = await bot.get_file(voice.file_id)
    buffer = bytearray()
    await bot.download_file(file.file_path, destination=buffer)

    transcriber = GroqTranscriber()
    transcription = await transcriber.transcribe(io.BytesIO(buffer), filename="voice.ogg", language="ru")
    await transcriber.aclose()

    text = transcription.get("text")
    if not text:
        segments = transcription.get("segments", [])
        text = " ".join(segment.get("text", "") for segment in segments)

    if not text:
        await message.answer("Не удалось распознать речь. Попробуйте ещё раз.")
        return

    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "user_id": str(message.from_user.id),
            "content": text,
            "metadata": {"source": "voice", "duration": voice.duration},
        }
        response = await client.post(f"{settings.api_base_url}/chat/messages", json=payload)

    if response.status_code != 200:
        await message.answer("Ошибка при обработке запроса. Попробуйте позже.")
        return

    reply_payload = response.json()
    reply_text = reply_payload.get("reply", {}).get("content")
    await message.answer(f"Текст: {text}\n\n{reply_text}")
