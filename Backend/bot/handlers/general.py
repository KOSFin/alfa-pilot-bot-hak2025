"""General bot handlers."""
from __future__ import annotations

import json
import re
from textwrap import dedent

import httpx
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.config import get_settings
from app.services.storage.redis_store import RedisStore

router = Router()


def build_start_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть веб-приложение", web_app=WebAppInfo(url=settings.twa_url))],
            [InlineKeyboardButton(text="Интеграция с Альфа-Бизнес", callback_data="stub_integration")],
        ]
    )


@router.message(CommandStart())
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


def _format_profile(profile: dict[str, str | int | None]) -> str:
    fields = {
        "Название": profile.get("company_name"),
        "Индустрия": profile.get("industry"),
        "Сотрудников": profile.get("employees"),
        "Выручка": profile.get("annual_revenue"),
        "Системы": profile.get("key_systems"),
        "Цели": profile.get("goals"),
    }
    lines = [f"{label}: {value}" for label, value in fields.items() if value]
    return "\n".join(lines)


@router.message(F.web_app_data)
async def handle_web_app_data(message: Message) -> None:
    if not message.web_app_data or not message.web_app_data.data:
        await message.answer("Не удалось получить данные из мини-приложения.")
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("Получены некорректные данные от веб-приложения.")
        return

    store = RedisStore()
    profile = {
        "user_id": str(message.from_user.id if message.from_user else "unknown"),
        "company_name": payload.get("company_name", ""),
        "industry": payload.get("industry"),
        "employees": payload.get("employees"),
        "annual_revenue": payload.get("annual_revenue"),
        "key_systems": payload.get("key_systems"),
        "goals": payload.get("goals"),
    }

    await store.set_json(f"company-profile:{profile['user_id']}", profile)

    details = _format_profile(profile)
    reply = "Отлично, я сохранил профиль вашей компании. "
    if details:
        reply += f"\n\n{details}"
    reply += "\n\nПродолжайте знакомство — задайте вопрос или загрузите документы."
    await message.answer(reply)
