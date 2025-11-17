"""Fallback text handler."""
from __future__ import annotations

import html
import httpx
import re
from aiogram import F, Router
from aiogram.types import Message

from app.config import get_settings
from bot.utils.onboarding import ensure_onboarding_ready

router = Router()


def format_bot_message(text: str) -> str:
    """
    Format the bot message for proper display in Telegram.
    Converts markdown-like formatting to Telegram-compatible formatting.
    """
    if not text:
        return text


    text = html.escape(text)


    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)


    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)


    text = re.sub(r'```([\s\S]*?)```', r'<pre>\1</pre>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)


    text = re.sub(r'^\s*[-*]\s+(.*)', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+(.*)', r'• \1', text, flags=re.MULTILINE)


    text = re.sub(r'^\s*#+\s+(.*)', r'<b>\1</b>', text, flags=re.MULTILINE)


    text = text.replace('\n\n', '\n\n')

    return text


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

    try:
        data = response.json()
    except Exception as e:
        await message.answer("Произошла ошибка при обработке ответа. Попробуйте позже.")
        return


    thinking_message = await message.answer("⏳ Думаю...")

    reply_text = data.get("reply", {}).get("content", "")
    plan_info = data.get("reply", {}).get("metadata", {})


    formatted_reply = format_bot_message(reply_text)


    tools_used = plan_info.get("tools_used", [])
    if tools_used:
        tools_str = " ".join([f"{tool.get('icon', '🔧')} {tool.get('name', 'Tool')}" for tool in tools_used])
        formatted_reply += f"\n\n<i>🛠 Использованные инструменты: {tools_str}</i>"


    try:
        if plan_info and (plan_id := plan_info.get("plan_id")):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=thinking_message.message_id,
                text=f"{formatted_reply}\n\nДля запуска расчёта нажмите /execute_{plan_id}"
            )
        else:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=thinking_message.message_id,
                text=formatted_reply
            )
    except Exception:

        if plan_info and (plan_id := plan_info.get("plan_id")):
            await message.answer(f"{formatted_reply}\n\nДля запуска расчёта нажмите /execute_{plan_id}")
        else:
            await message.answer(formatted_reply)
