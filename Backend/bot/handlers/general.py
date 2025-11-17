"""General bot handlers."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from textwrap import dedent

import httpx
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import get_settings
from app.services.storage.redis_store import RedisStore

from ..utils.onboarding import (
    OnboardingStage,
    build_keyboard_for_stage,
    get_onboarding_status,
)

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    logger.info("Handling /start for user %s", message.from_user.id if message.from_user else "unknown")
    user_id = str(message.from_user.id) if message.from_user else "anonymous"
    status = await get_onboarding_status(user_id)

    if status.stage == OnboardingStage.PROFILE:
        text = dedent(
            """
            Привет! Я Alfa Pilot и помогаю быстро считать сценарии и отвечать на бизнес-вопросы.\n\nПока я ничего не знаю о вашей компании, поэтому первым делом заполните профиль в мини-приложении. Это нужно, чтобы учесть ваш контекст, а данные сразу же отправятся в очередь на индексацию.
            """
        ).strip()
    elif status.stage == OnboardingStage.INTEGRATION:
        text = dedent(
            """
            Профиль компании уже у меня и стоит в очереди на индексацию. Осталось подключить Альфа-Бизнес через мини-приложение, чтобы я мог подстраиваться под реальные операции.
            """
        ).strip()
    else:
        text = dedent(
            """
            Отлично, все готово! Вот как мы работаем дальше:\n1. Задавайте запросы или отправляйте голосовые сообщения — я отвечу и сохраню диалог.\n2. Загружайте документы, и я буду подбирать выдержки в ответах.\n3. Если пришлю расчётный план — выполните его командой /execute_<id>.
            """
        ).strip()

    await message.answer(text, reply_markup=build_keyboard_for_stage(status.stage))


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
    payload_type = payload.get("type", "company_profile")
    user_id = str(message.from_user.id if message.from_user else payload.get("user_id", "unknown"))

    if payload_type == "alpha_business_connected":
        logger.info("Received Alfa Business integration confirmation from user %s", user_id)
        integration_payload = {
            "status": "connected",
            "connected_at": datetime.utcnow().isoformat(),
        }
        await store.set_json(f"integration:alpha-business:{user_id}", integration_payload)
        reply = dedent(
            """
            Готово — отметили подключение Альфа-Бизнес. Я завершил знакомство и готов работать. Вот что можно сделать дальше:
            1. Задавайте вопросы или голосовые сообщения — отвечу и сохраню их в памяти.
            2. Загружайте документы, чтобы использовать их в ответах.
            3. Просите расчёты — если предложу план, выполните его командой /execute_<id>.
            """
        ).strip()
        await message.answer(reply, reply_markup=build_keyboard_for_stage(OnboardingStage.READY))
        return

    profile = {
        "user_id": user_id,
        "company_name": payload.get("company_name", ""),
        "industry": payload.get("industry"),
        "employees": payload.get("employees"),
        "annual_revenue": payload.get("annual_revenue"),
        "key_systems": payload.get("key_systems"),
        "goals": payload.get("goals"),
        "submitted_at": datetime.utcnow().isoformat(),
    }

    logger.info("Received company profile from web app for user %s", profile["user_id"])

    await store.set_json(f"company-profile:{profile['user_id']}", profile)
    details = _format_profile(profile)
    reply = "Профиль сохранён и отправлен в очередь на индексацию. "
    if details:
        reply += f"\n\n{details}"
    reply += "\n\nСледующий шаг — подключить Альфа-Бизнес через мини-приложение."
    await message.answer(reply, reply_markup=build_keyboard_for_stage(OnboardingStage.INTEGRATION))
