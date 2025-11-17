"""Integration endpoints for Telegram Web App onboarding."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import ValidationError

from ..schemas.integration import (
    CompanyProfile,
    CompanyProfileResponse,
    IntegrationConfirmation,
    IntegrationConfirmationResponse,
    IntegrationStatus,
    OnboardingStateResponse,
    ProfileIndexStatus,
)
from ..services.storage.knowledge_base import KnowledgeBase
from ..services.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integration", tags=["integration"])


def get_store() -> RedisStore:
    return RedisStore()


def get_knowledge_base(request: Request) -> KnowledgeBase:
    return request.app.state.knowledge_base


async def _notify_bot_profile_saved(request: Request, user_id: str) -> None:
    """Send a message to the bot after profile is saved."""
    try:
        from aiogram import Bot
        from textwrap import dedent
        
        logger.info("Starting notification for profile saved: user_id=%s", user_id)
        
        bot: Bot = request.app.state.bot
        if not bot:
            logger.error("Bot instance not available in app state")
            return
        if not (user_id and str(user_id).lstrip("-+ ").isdigit()):
            logger.warning("Skip profile notification: user_id '%s' is not numeric", user_id)
            return

        store = RedisStore()
        integration_state = await store.get_json(f"integration:alpha-business:{user_id}")
        if integration_state and integration_state.get("status") == "connected":
            logger.info("Skip profile notification: integration already connected for user %s", user_id)
            return
        
        text = dedent(
            """
            ✅ <b>Профиль сохранён и отправлен в очередь на индексацию!</b>
            
            🔗 <b>Следующий шаг — подключение Альфа-Бизнес</b>
            Это позволит мне анализировать ваши финансовые операции и давать более точные рекомендации. Нажмите кнопку ниже, чтобы подключить интеграцию (это займёт 10 секунд).
            """
        ).strip()
        
        from bot.utils.onboarding import OnboardingStage, build_keyboard_for_stage
        
        chat_id = int(user_id)
        logger.info("Sending message to user %s", chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=build_keyboard_for_stage(OnboardingStage.INTEGRATION, str(chat_id))
        )
        logger.info("Successfully sent profile saved notification to user %s", user_id)
    except Exception as exc:
        logger.exception("Failed to notify bot about profile save for user %s: %s", user_id, exc)


async def _notify_bot_integration_connected(request: Request, user_id: str) -> None:
    """Send a message to the bot after integration is connected."""
    try:
        from aiogram import Bot
        from textwrap import dedent
        
        logger.info("Starting notification for integration connected: user_id=%s", user_id)
        
        bot: Bot = request.app.state.bot
        if not bot:
            logger.error("Bot instance not available in app state")
            return
        if not (user_id and str(user_id).lstrip("-+ ").isdigit()):
            logger.warning("Skip integration notification: user_id '%s' is not numeric", user_id)
            return
        
        text = dedent(
            """
            🎉 <b>Отлично! Альфа-Бизнес подключён.</b>
            
            ✅ Онбординг завершён! Теперь я готов работать с полным контекстом вашего бизнеса.
            
            📖 <b>Как использовать бота:</b>
            
            1️⃣ <b>Задавайте вопросы</b>
            Просто напишите текстом или отправьте голосовое сообщение. Я отвечу с учётом контекста вашей компании и финансовых данных.
            
            2️⃣ <b>Загружайте документы</b>
            Через веб-приложение можно загрузить документы (отчёты, регламенты, контракты). Я буду использовать их при ответах.
            
            3️⃣ <b>Выполняйте расчёты</b>
            Если я предложу расчётный план, вы сможете выполнить его командой /execute_&lt;id&gt;
            
            4️⃣ <b>Используйте веб-интерфейс</b>
            Для работы с документами и детального диалога откройте веб-приложение.
            
            Готов к работе! Чем могу помочь?
            """
        ).strip()
        
        from bot.utils.onboarding import OnboardingStage, build_keyboard_for_stage
        
        chat_id = int(user_id)
        logger.info("Sending message to user %s", chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=build_keyboard_for_stage(OnboardingStage.READY, str(chat_id))
        )
        logger.info("Successfully sent integration connected notification to user %s", user_id)
    except Exception as exc:
        logger.exception("Failed to notify bot about integration for user %s: %s", user_id, exc)


async def _index_profile_background(profile: CompanyProfile, knowledge_base: KnowledgeBase) -> None:
    """Convert profile to text and index it asynchronously with comprehensive representations."""

    store = RedisStore()
    status_key = f"profile-index-status:{profile.user_id}"
    await store.set_json(
        status_key,
        {"status": "processing", "started_at": datetime.utcnow().isoformat()},
    )

    try:
        # Primary structured summary
        fields = {
            "Название": profile.company_name,
            "Индустрия": profile.industry,
            "Сотрудников": profile.employees,
            "Выручка": profile.annual_revenue,
            "Системы": profile.key_systems,
            "Цели": profile.goals,
        }
        
        lines = [f"{label}: {value}" for label, value in fields.items() if value]
        primary_summary = "Профиль компании\n" + "\n".join(lines)

        # Comprehensive list of representations to maximize search recall
        additional_texts = []
        
        if profile.company_name:
            # Variations for company name queries
            name_variations = [
                f"Компания: {profile.company_name}",
                f"Название моей компании: {profile.company_name}",
                f"Моя компания называется: {profile.company_name}",
                f"Организация: {profile.company_name}",
                f"Моя организация: {profile.company_name}",
                f"Фирма: {profile.company_name}",
                f"Компания {profile.company_name} работает в сфере {profile.industry or 'неизвестной индустрии'}"
            ]
            
            # Variations for direct questions about company name
            question_variations = [
                f"Как называется моя компания? Моя компания называется {profile.company_name}",
                f"Название вашей компании: {profile.company_name}",
                f"Моя компания - {profile.company_name}",
                f"Наименование организации: {profile.company_name}",
                f"Компания, с которой мы работаем: {profile.company_name}",
                f"Название нашей компании: {profile.company_name}",
                f"Компания {profile.company_name}",
                f"Мы работаем с компанией {profile.company_name}",
                f"{profile.company_name} - это название моей компании",
                f"Наша организация: {profile.company_name}"
            ]
            
            additional_texts.extend(name_variations)
            additional_texts.extend(question_variations)
            
            # Contextual information combining company name with other details
            contextual_variations = []
            if profile.industry:
                contextual_variations.extend([
                    f"Компания {profile.company_name} работает в индустрии {profile.industry}",
                    f"Моя компания {profile.company_name} специализируется на {profile.industry}",
                    f"{profile.company_name} - {profile.industry} компания"
                ])
            if profile.annual_revenue:
                contextual_variations.extend([
                    f"Компания {profile.company_name} имеет выручку {profile.annual_revenue}",
                    f"Выручка {profile.company_name} составляет {profile.annual_revenue}"
                ])
            if profile.employees:
                contextual_variations.extend([
                    f"Компания {profile.company_name} насчитывает {profile.employees} сотрудников",
                    f"В {profile.company_name} работает {profile.employees} человек"
                ])
            if profile.goals:
                contextual_variations.extend([
                    f"Цели компании {profile.company_name}: {profile.goals}",
                    f"{profile.company_name} стремится к: {profile.goals}"
                ])
            
            additional_texts.extend(contextual_variations)

        # Prepare all documents to index
        all_documents = [(primary_summary, "primary")]
        all_documents.extend([(text, "variation") for text in additional_texts if text.strip()])

        # Index all representations
        metadata = {"user_id": profile.user_id, "source": "company_profile", "profile_type": "company_info"}
        
        indexed_any = False
        for idx, (text, doc_type) in enumerate(all_documents):
            if text.strip():  # Only index non-empty texts
                dialog_id = f"profile:{profile.user_id}:{uuid.uuid4()}:{idx}"
                try:
                    indexed = await knowledge_base.index_dialog(dialog_id, text, metadata)
                    if indexed:
                        indexed_any = True
                except Exception as e:
                    logger.warning(f"Failed to index company profile document {dialog_id} for user {profile.user_id}: {e}")
                    # Continue with other documents even if one fails

        if not indexed_any:
            logger.warning("No company profile documents were indexed for user %s", profile.user_id)
            await store.set_json(
                status_key,
                {
                    "status": "failed",
                    "reason": "embedding_unavailable",
                    "finished_at": datetime.utcnow().isoformat(),
                },
            )
            return

        await store.set_json(
            status_key,
            {
                "status": "indexed",
                "finished_at": datetime.utcnow().isoformat(),
                "indexed_count": len(all_documents),
            },
        )
        
        logger.info(f"Successfully indexed company profile for user {profile.user_id} with {len(all_documents)} documents")

    except Exception as exc:
        logger.exception("Failed to index company profile for user %s", profile.user_id)
        await store.set_json(
            status_key,
            {
                "status": "failed",
                "reason": "unexpected_error",
                "finished_at": datetime.utcnow().isoformat(),
            },
        )


@router.post("/profile", response_model=CompanyProfileResponse)
async def save_company_profile(
    profile: CompanyProfile,
    background_tasks: BackgroundTasks,
    request: Request,
    store: RedisStore = Depends(get_store),
    knowledge_base: KnowledgeBase = Depends(get_knowledge_base),
) -> CompanyProfileResponse:
    """Persist the company profile submitted from the Telegram Web App."""
    if not profile.company_name.strip():
        raise HTTPException(status_code=422, detail="Company name is required")

    key = f"company-profile:{profile.user_id}"
    payload = profile.model_dump(mode="json")
    payload["submitted_at"] = datetime.utcnow().isoformat()
    await store.set_json(key, payload)
    await store.set_json(
        f"profile-index-status:{profile.user_id}",
        {"status": "queued", "queued_at": datetime.utcnow().isoformat()},
    )
    background_tasks.add_task(_index_profile_background, profile, knowledge_base)
    background_tasks.add_task(_notify_bot_profile_saved, request, profile.user_id)
    logger.info("Stored company profile for user %s", profile.user_id)
    return CompanyProfileResponse(profile=profile)


@router.post("/alpha-business", response_model=IntegrationConfirmationResponse)
async def confirm_alpha_business(
    confirmation: IntegrationConfirmation,
    background_tasks: BackgroundTasks,
    request: Request,
    store: RedisStore = Depends(get_store),
) -> IntegrationConfirmationResponse:
    payload = IntegrationStatus(
        status="connected",
        provider=confirmation.provider,
        connected_at=confirmation.connected_at,
    )
    await store.set_json(f"integration:alpha-business:{confirmation.user_id}", payload.model_dump(mode="json"))
    background_tasks.add_task(_notify_bot_integration_connected, request, confirmation.user_id)
    logger.info("Alpha Business integration confirmed for user %s", confirmation.user_id)
    return IntegrationConfirmationResponse(integration=payload)


@router.get("/state/{user_id}", response_model=OnboardingStateResponse)
async def get_onboarding_state(user_id: str, store: RedisStore = Depends(get_store)) -> OnboardingStateResponse:
    profile_data = await store.get_json(f"company-profile:{user_id}")
    profile: CompanyProfile | None = None
    if profile_data:
        profile_data = dict(profile_data)
        profile_data.pop("submitted_at", None)
        try:
            profile = CompanyProfile.model_validate(profile_data)
        except ValidationError as exc:
            logger.warning("Failed to load stored profile for %s: %s", user_id, exc)

    profile_status_data = await store.get_json(f"profile-index-status:{user_id}")
    profile_status: ProfileIndexStatus | None = None
    if profile_status_data:
        try:
            profile_status = ProfileIndexStatus.model_validate(profile_status_data)
        except ValidationError as exc:
            logger.warning("Failed to parse profile status for %s: %s", user_id, exc)
    if not profile_status and profile is not None:
        profile_status = ProfileIndexStatus(status="missing")

    integration_data = await store.get_json(f"integration:alpha-business:{user_id}")
    integration: IntegrationStatus | None = None
    if integration_data:
        try:
            integration = IntegrationStatus.model_validate(integration_data)
        except ValidationError as exc:
            logger.warning("Failed to parse integration status for %s: %s", user_id, exc)

    return OnboardingStateResponse(
        user_id=user_id,
        profile=profile,
        profile_status=profile_status,
        integration=integration,
    )
