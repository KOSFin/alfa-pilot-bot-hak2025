"""Document upload handler."""
from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.types import Message

from app.config import get_settings
from bot.utils.onboarding import ensure_onboarding_ready

router = Router()


@router.message(F.document)
async def handle_document(message: Message) -> None:
    document = message.document
    if not document:
        return

    allowed, _ = await ensure_onboarding_ready(message)
    if not allowed:
        return

    settings = get_settings()
    bot = message.bot
    file = await bot.get_file(document.file_id)
    buffer = bytearray()
    await bot.download_file(file.file_path, destination=buffer)

    async with httpx.AsyncClient(timeout=120.0) as client:
        files = {"file": (document.file_name or "telegram-upload", bytes(buffer), document.mime_type or "application/octet-stream")}
        data = {
            "title": document.file_name or "Документ из Telegram",
            "description": "Загружено через Telegram",
            "category": "telegram",
            "tags_json": "[\"telegram\", \"user-upload\"]",
        }
        response = await client.post(f"{settings.api_base_url}/knowledge/documents", data=data, files=files)

    if response.status_code == 200:
        await message.answer("Документ успешно загружен и отправлен в базу знаний.")
    else:
        await message.answer("Не удалось обработать документ. Попробуйте позже.")
