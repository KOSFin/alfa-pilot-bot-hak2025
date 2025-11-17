"""Fallback text handler."""
from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.types import Message

from app.config import get_settings
from bot.utils.onboarding import ensure_onboarding_ready

router = Router()


@router.message(F.text)
async def handle_text(message: Message) -> None:
    if message.text and message.text.startswith("/"):
        return

    allowed, _ = await ensure_onboarding_ready(message)
    if not allowed:
        return

    settings = get_settings()
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "user_id": str(message.from_user.id),
            "content": message.text,
            "metadata": {"source": "telegram"},
        }
        response = await client.post(f"{settings.api_base_url}/chat/messages", json=payload)

    if response.status_code != 200:
        await message.answer("Сейчас не могу ответить, попробуйте позже.")
        return

    data = response.json()
    reply_text = data.get("reply", {}).get("content", "")
    plan_info = data.get("reply", {}).get("metadata", {})

    if plan_info and (plan_id := plan_info.get("plan_id")):
        await message.answer(f"{reply_text}\n\nДля запуска расчёта нажмите /execute_{plan_id}")
    else:
        await message.answer(reply_text)
