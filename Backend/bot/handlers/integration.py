"""Integration stub handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(F.data == "stub_integration")
async def handle_stub_integration(callback: CallbackQuery) -> None:
    await callback.answer("Обновили процесс подключения", show_alert=True)
    await callback.message.answer(
        "Интеграция теперь запускается из мини-приложения. Нажмите /start, чтобы получить актуальную кнопку."
    )
