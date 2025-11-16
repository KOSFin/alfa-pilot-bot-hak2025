"""General bot handlers."""
from __future__ import annotations

from textwrap import dedent

from aiogram import Router
import re

import httpx
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from app.config import get_settings

router = Router()


def build_start_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть веб-приложение", web_app={"url": settings.twa_url})],
            [InlineKeyboardButton(text="Интеграция с Альфа-Бизнес", callback_data="stub_integration")],
        ]
    )


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = dedent(
        """
        Привет! Я Alfa Pilot — умный ассистент для финансовых расчётов и советов.

        1. Загрузите документы и материалы компании через мини-приложение.
        2. Подключите Альфа-Бизнес (пока заглушка) для синхронизации операций.
        3. Опишите, что нужно посчитать или спросите совет — я всё сохраню в память.

        Готов помочь! 👇
        """
    ).strip()
    await message.answer(text, reply_markup=build_start_keyboard())


@router.message(lambda message: bool(message.text and message.text.startswith("/execute_")))
async def handle_commands(message: Message) -> None:
    match = re.match(r"^/execute_(?P<plan>[\w-]+)$", message.text or "")
    if not match:
        return

    plan_id = match.group("plan")
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {"plan_id": plan_id, "user_id": str(message.from_user.id)}
        response = await client.post(f"{settings.api_base_url}/chat/execute", json=payload)

    if response.status_code != 200:
        await message.answer("План не найден или истёк. Попробуйте запросить расчёт заново.")
        return

    data = response.json()
    reply_text = data.get("reply", {}).get("content", "")
    await message.answer(reply_text)
