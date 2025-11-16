"""Integration stub handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(F.data == "stub_integration")
async def handle_stub_integration(callback: CallbackQuery) -> None:
    await callback.answer("Открываем форму интеграции", show_alert=True)
    await callback.message.answer(
        "Заглушка: подключение к Альфа-Бизнес пока недоступно. Представим, что интеграция прошла успешно."
    )
