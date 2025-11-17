"""Language selection handler."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.services.storage.redis_store import RedisStore

router = Router()


@router.callback_query(F.data.startswith("set_lang_"))
async def set_language_callback(callback_query: CallbackQuery) -> None:
    """Handle language selection callback."""
    lang_code = callback_query.data.split("_")[-1]
    user_id = str(callback_query.from_user.id)

    # Update user profile with selected language
    store = RedisStore()
    profile = await store.get_json(f"company-profile:{user_id}") or {}
    profile["language"] = lang_code
    await store.set_json(f"company-profile:{user_id}", profile)

    # Send confirmation message and update the keyboard
    lang_names = {
        "ru": "Русский",
        "en": "English"
    }
    lang_name = lang_names.get(lang_code, lang_code)

    # Create a keyboard to go back to the main menu
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Продолжить", callback_data="go_back_profile")
        ]
    ])

    await callback_query.message.edit_text(f"✅ Язык распознавания установлен на: {lang_name}\n\nТеперь вы можете продолжить работу с ботом.", reply_markup=keyboard)
    await callback_query.answer()