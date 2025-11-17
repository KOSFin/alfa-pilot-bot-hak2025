"""Callback handlers for inline keyboards."""
from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings

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