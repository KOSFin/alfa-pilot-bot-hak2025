"""Callback handlers for inline keyboards."""
from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings
from app.services.storage.redis_store import RedisStore

router = Router()


@router.callback_query(F.data == "reset_context")
async def reset_context_callback(callback_query: CallbackQuery) -> None:
    """Handle reset context button click."""
    user_id = str(callback_query.from_user.id)

    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(f"{settings.api_base_url}/chat/context/{user_id}")

            if response.status_code == 200:
                await callback_query.answer("Контекст успешно сброшен! Начинаем новый диалог.", show_alert=True)
            else:
                await callback_query.answer("Ошибка при сбросе контекста. Попробуйте позже.", show_alert=True)
        except Exception as e:
            await callback_query.answer("Ошибка соединения. Попробуйте позже.", show_alert=True)
            print(f"Error resetting context: {e}")

    # Acknowledge the callback
    await callback_query.answer()


@router.callback_query(F.data == "select_language")
async def show_language_selection(callback_query: CallbackQuery) -> None:
    """Show language selection menu."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="go_back_profile")
        ]
    ])

    # Update the message content and keyboard to prompt for language selection
    await callback_query.message.edit_text(
        "Выберите язык для распознавания речи:",
        reply_markup=keyboard
    )
    await callback_query.answer()


@router.callback_query(F.data == "go_back_profile")
async def go_back_to_profile(callback_query: CallbackQuery) -> None:
    """Go back to profile menu."""
    from app.config import get_settings
    from bot.utils.onboarding import build_keyboard_for_stage, get_onboarding_status

    user_id = str(callback_query.from_user.id) if callback_query.from_user else None
    settings = get_settings()

    # Get current profile to show current language setting
    store = RedisStore()
    profile = await store.get_json(f"company-profile:{user_id}") or {}
    current_lang = profile.get("language", "ru")

    lang_text = "Русский" if current_lang == "ru" else "English"

    # Get the current onboarding status to determine the appropriate text
    status = await get_onboarding_status(user_id)
    if status.stage == "profile_needed":
        text = f"Текущий язык распознавания: {lang_text}\n\nДля завершения онбординга заполните профиль компании:"
        keyboard = build_keyboard_for_stage("profile_needed", user_id)
    elif status.stage == "integration_needed":
        text = f"Текущий язык распознавания: {lang_text}\n\nПродолжить настройку интеграции:"
        keyboard = build_keyboard_for_stage("integration_needed", user_id)
    else:
        text = f"Текущий язык распознавания: {lang_text}\n\nГотово к работе!"
        keyboard = build_keyboard_for_stage("ready", user_id)

    # Restore the original message with the appropriate keyboard
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()