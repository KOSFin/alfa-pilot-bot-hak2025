"""Voice message handler."""
from __future__ import annotations

import html
import io
import re

import httpx
from aiogram import F, Router
from aiogram.types import Message

from app.config import get_settings
from app.services.transcription.groq_client import GroqTranscriber
from bot.utils.onboarding import ensure_onboarding_ready

router = Router()


def format_bot_message(text: str) -> str:
    """
    Format the bot message for proper display in Telegram.
    Converts markdown-like formatting to Telegram-compatible formatting.
    """
    if not text:
        return text

    # Escape HTML characters to prevent issues
    text = html.escape(text)

    # Convert markdown-style bold (**) to Telegram HTML bold tags
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    # Convert markdown-style italic (*) to Telegram HTML italic tags
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

    # Handle markdown-style code blocks
    text = re.sub(r'```([\s\S]*?)```', r'<pre>\1</pre>', text)  # Multi-line code blocks
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)  # Inline code

    # Handle markdown-style lists
    text = re.sub(r'^\s*[-*]\s+(.*)', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+(.*)', r'• \1', text, flags=re.MULTILINE)

    # Convert markdown headers to bold text
    text = re.sub(r'^\s*#+\s+(.*)', r'<b>\1</b>', text, flags=re.MULTILINE)

    # Handle newlines appropriately
    text = text.replace('\n\n', '\n\n')  # Preserve paragraph breaks

    return text


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    voice = message.voice
    if not voice:
        return

    allowed, _ = await ensure_onboarding_ready(message)
    if not allowed:
        return

    # Get user's language preference from profile
    user_id = str(message.from_user.id)
    from app.services.storage.redis_store import RedisStore
    store = RedisStore()
    profile = await store.get_json(f"company-profile:{user_id}")
    language = "ru"  # Default language
    if profile and profile.get("language"):
        language = profile["language"]

    settings = get_settings()
    bot = message.bot
    file = await bot.get_file(voice.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, destination=buffer)
    buffer.seek(0)  # Reset buffer position to the beginning

    transcriber = GroqTranscriber()
    transcription = await transcriber.transcribe(buffer, filename="voice.ogg", language=language)
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

    # Send a "thinking" message first
    thinking_message = await message.answer("⏳ Обрабатываю запрос...")

    reply_payload = response.json()
    reply_text = reply_payload.get("reply", {}).get("content")
    # Format the reply text to ensure proper Telegram formatting
    formatted_reply = format_bot_message(reply_text)

    # Edit the thinking message with the actual response
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=thinking_message.message_id,
            text=f"Текст: {text}\n\n{formatted_reply}"
        )
    except Exception:
        # If editing fails (e.g., message too old), send a new message
        await message.answer(f"Текст: {text}\n\n{formatted_reply}")
