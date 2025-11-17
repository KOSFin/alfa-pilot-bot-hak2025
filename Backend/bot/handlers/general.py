"""General bot handlers."""
from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from textwrap import dedent

import httpx
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import get_settings
from app.services.storage.redis_store import RedisStore
from app.schemas.integration import IntegrationStatus

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
    keyboard_user_id = str(message.from_user.id) if message.from_user else None
    status = await get_onboarding_status(user_id)

    if status.stage == OnboardingStage.PROFILE:
        text = dedent(
            """
            👋 Привет! Я <b>Alfa Pilot</b> — ваш умный помощник для бизнес-расчётов и анализа.
            
            🎯 <b>Зачем я нужен?</b>
            • Быстро считаю бизнес-сценарии с учётом контекста вашей компании
            • Отвечаю на вопросы, используя вашу базу знаний и документы
            • Помогаю принимать решения на основе финансовых данных
            
            📋 <b>Что нужно для начала?</b>
            Заполните профиль компании в мини-приложении ниже. Это займёт 2 минуты, но даст мне понимание вашего бизнеса. После сохранения профиль автоматически проиндексируется, и я смогу давать более точные ответы.
            """
        ).strip()
    elif status.stage == OnboardingStage.INTEGRATION:
        text = dedent(
            """
            ✅ Отлично! Профиль компании получен и уже индексируется.
            
            🔗 <b>Следующий шаг — подключение Альфа-Бизнес</b>
            Это позволит мне учитывать ваши реальные финансовые операции при расчётах и анализе. Нажмите кнопку ниже, чтобы подключить интеграцию.
            """
        ).strip()
    else:
        text = dedent(
            """
            🎉 <b>Отлично! Всё готово к работе.</b>
            
            📖 <b>Как использовать бота:</b>
            
            1️⃣ <b>Задавайте вопросы</b>
            Просто напишите текстом или отправьте голосовое сообщение. Я отвечу с учётом контекста вашей компании и сохраню диалог в памяти.
            
            2️⃣ <b>Загружайте документы</b>
            Через веб-приложение можно загрузить документы (отчёты, регламенты, контракты). Я буду использовать их при ответах.
            
            3️⃣ <b>Выполняйте расчёты</b>
            Если я предложу расчётный план, вы сможете выполнить его командой /execute_&lt;id&gt;
            
            4️⃣ <b>Используйте веб-интерфейс</b>
            Для работы с документами и детального диалога используйте веб-приложение.
            
            Готов к работе! Задавайте вопросы или загружайте документы.
            """
        ).strip()

    await message.answer(text, reply_markup=build_keyboard_for_stage(status.stage, keyboard_user_id))


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

    # Send a "thinking" message first
    thinking_message = await message.answer("⏳ Выполняю расчёт...")

    data = response.json()
    reply_text = data.get("reply", {}).get("content", "")
    # Format the reply text to ensure proper Telegram formatting
    formatted_reply = format_bot_message(reply_text)

    # Edit the thinking message with the actual response
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=thinking_message.message_id,
            text=formatted_reply
        )
    except Exception:
        # If editing fails (e.g., message too old), send a new message
        await message.answer(formatted_reply)


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
    """Handle data from web app - this is only for Telegram mini app closure confirmation."""
    if not message.web_app_data or not message.web_app_data.data:
        await message.answer("Не удалось получить данные из мини-приложения.")
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("Получены некорректные данные от веб-приложения.")
        return

    logger.info("Web app data received: type=%s", payload.get("type"))
    
    # Web app data is just for confirmation, actual notifications come from API
    await message.answer("✅ Данные получены!")


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    """Handle /language command to show language selection."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Get current language from user profile
    user_id = str(message.from_user.id)
    store = RedisStore()
    profile = await store.get_json(f"company-profile:{user_id}") or {}
    current_lang = profile.get("language", "ru")

    lang_text = "Русский" if current_lang == "ru" else "English"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="go_back_profile")
        ]
    ])

    await message.answer(
        f"Текущий язык распознавания речи: <b>{lang_text}</b>\n\nВыберите язык для голосовых сообщений:",
        reply_markup=keyboard
    )
