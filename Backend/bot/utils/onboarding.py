"""Helpers for onboarding state and keyboards."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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


def _build_web_app_url(base_url: str, user_id: str | None = None, extra: dict[str, str] | None = None) -> str:
    """Attach query params (telegram user id, extra flags) to the web app URL."""

    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if user_id:
        query["tg_user_id"] = str(user_id)
    if extra:
        query.update({key: value for key, value in extra.items() if value is not None})
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))


def build_keyboard_for_stage(stage: OnboardingStage, user_id: str | None = None) -> InlineKeyboardMarkup:
    """Return onboarding keyboard tailored to the current stage with per-user URLs."""

    settings = get_settings()
    profile_url = _build_web_app_url(settings.twa_url, user_id)
    integration_url = _build_web_app_url(settings.twa_url, user_id, {"mode": "integration"})
    profile_button = InlineKeyboardButton(
        text="Заполнить профиль",
        web_app=WebAppInfo(url=profile_url),
    )
    integration_button = InlineKeyboardButton(
        text="Подключить Альфа-Бизнес",
        web_app=WebAppInfo(url=integration_url),
    )

    language_button = InlineKeyboardButton(
        text="🌐 Язык распознавания",
        callback_data="select_language"
    )
    reset_context_button = InlineKeyboardButton(
        text="🔄 Сбросить контекст",
        callback_data="reset_context"
    )
    if stage == OnboardingStage.PROFILE:
        return InlineKeyboardMarkup(inline_keyboard=[[profile_button]])
    if stage == OnboardingStage.INTEGRATION:
        return InlineKeyboardMarkup(inline_keyboard=[[integration_button]])

    return InlineKeyboardMarkup(inline_keyboard=[[profile_button], [integration_button], [language_button], [reset_context_button]])


async def ensure_onboarding_ready(message: Message, store: RedisStore | None = None) -> tuple[bool, OnboardingStatus]:
    """Verify onboarding completion before processing free-form input."""

    from_user = message.from_user
    user_id = str(from_user.id) if from_user else "anonymous"
    keyboard_user_id = str(from_user.id) if from_user else None
    local_store = store or RedisStore()
    status = await get_onboarding_status(user_id, local_store)

    if status.stage == OnboardingStage.READY:
        return True, status

    if status.stage == OnboardingStage.PROFILE:
        from textwrap import dedent
        text = dedent(
            """
            📋 <b>Заполните профиль компании</b>

            Откройте мини-приложение ниже и введите базовую информацию о вашем бизнесе. Это займёт 2 минуты, но даст мне понимание контекста вашей компании. После сохранения профиль автоматически проиндексируется.
            """
        ).strip()
        await message.answer(
            text,
            reply_markup=build_keyboard_for_stage(OnboardingStage.PROFILE, keyboard_user_id),
        )
        return False, status

    from textwrap import dedent
    text = dedent(
        """
        🔗 <b>Подключите Альфа-Бизнес</b>

        Это последний шаг онбординга. Подключение позволит мне анализировать ваши финансовые операции и давать более точные рекомендации. Нажмите кнопку ниже — это займёт всего 10 секунд.
        """
    ).strip()
    await message.answer(
        text,
        reply_markup=build_keyboard_for_stage(OnboardingStage.INTEGRATION, keyboard_user_id),
    )
    return False, status
