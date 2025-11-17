"""Helpers for onboarding state and keyboards."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.config import get_settings
from app.services.storage.redis_store import RedisStore


class OnboardingStage(str, Enum):
    """Stages of the guided onboarding flow."""

    PROFILE = "profile_needed"
    INTEGRATION = "integration_needed"
    READY = "ready"


@dataclass
class OnboardingStatus:
    """Aggregated onboarding state."""

    stage: OnboardingStage
    profile: dict[str, Any] | None
    integration: dict[str, Any] | None


async def get_onboarding_status(user_id: str, store: RedisStore | None = None) -> OnboardingStatus:
    """Fetch onboarding state for the given user."""

    local_store = store or RedisStore()
    profile = await local_store.get_json(f"company-profile:{user_id}")
    integration = await local_store.get_json(f"integration:alpha-business:{user_id}")
    if not profile:
        stage = OnboardingStage.PROFILE
    elif not integration or integration.get("status") != "connected":
        stage = OnboardingStage.INTEGRATION
    else:
        stage = OnboardingStage.READY
    return OnboardingStatus(stage=stage, profile=profile, integration=integration)


def build_keyboard_for_stage(stage: OnboardingStage) -> InlineKeyboardMarkup:
    """Return onboarding keyboard tailored to the current stage."""

    settings = get_settings()
    profile_button = InlineKeyboardButton(
        text="Заполнить профиль",
        web_app=WebAppInfo(url=settings.twa_url),
    )
    integration_button = InlineKeyboardButton(
        text="Подключить Альфа-Бизнес",
        web_app=WebAppInfo(url=f"{settings.twa_url}?mode=integration"),
    )
    if stage == OnboardingStage.PROFILE:
        return InlineKeyboardMarkup(inline_keyboard=[[profile_button]])
    if stage == OnboardingStage.INTEGRATION:
        return InlineKeyboardMarkup(inline_keyboard=[[integration_button]])
    return InlineKeyboardMarkup(inline_keyboard=[[profile_button], [integration_button]])


async def ensure_onboarding_ready(message: Message, store: RedisStore | None = None) -> tuple[bool, OnboardingStatus]:
    """Verify onboarding completion before processing free-form input."""

    from_user = message.from_user
    user_id = str(from_user.id) if from_user else "anonymous"
    local_store = store or RedisStore()
    status = await get_onboarding_status(user_id, local_store)

    if status.stage == OnboardingStage.READY:
        return True, status

    if status.stage == OnboardingStage.PROFILE:
        await message.answer(
            "Для начала работы заполните профиль компании в мини-приложении. "
            "Это нужно, чтобы бот учитывал контекст вашего бизнеса. После сохранения профиль "
            "автоматически ставится в очередь на индексацию.",
            reply_markup=build_keyboard_for_stage(OnboardingStage.PROFILE),
        )
        return False, status

    await message.answer(
        "Остался последний шаг — подключить Альфа-Бизнес через мини-приложение. "
        "Это позволит мне подсказывать с учётом финансовых данных. После подключения можно продолжить диалог.",
        reply_markup=build_keyboard_for_stage(OnboardingStage.INTEGRATION),
    )
    return False, status
