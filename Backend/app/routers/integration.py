"""Integration endpoints for Telegram Web App onboarding."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from ..schemas.integration import (
    CompanyProfile,
    CompanyProfileResponse,
    IntegrationConfirmation,
    IntegrationConfirmationResponse,
)
from ..services.ai.gemini_client import EmbeddingServiceUnavailable
from ..services.storage.knowledge_base import KnowledgeBase
from ..services.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integration", tags=["integration"])


def get_store() -> RedisStore:
    return RedisStore()


def get_knowledge_base(request: Request) -> KnowledgeBase:
    return request.app.state.knowledge_base


async def _index_profile_background(profile: CompanyProfile, knowledge_base: KnowledgeBase) -> None:
    """Convert profile to text and index it asynchronously."""

    store = RedisStore()
    status_key = f"profile-index-status:{profile.user_id}"
    await store.set_json(
        status_key,
        {"status": "processing", "started_at": datetime.utcnow().isoformat()},
    )

    fields = {
        "Название": profile.company_name,
        "Индустрия": profile.industry,
        "Сотрудников": profile.employees,
        "Выручка": profile.annual_revenue,
        "Системы": profile.key_systems,
        "Цели": profile.goals,
    }
    lines = [f"{label}: {value}" for label, value in fields.items() if value]
    summary = "Профиль компании\n" + "\n".join(lines)

    dialog_id = f"profile:{profile.user_id}:{uuid.uuid4()}"
    metadata = {"user_id": profile.user_id, "source": "company_profile"}

    try:
        await knowledge_base.index_dialog(dialog_id, summary, metadata)
    except EmbeddingServiceUnavailable as exc:
        logger.warning("Embedding unavailable when indexing profile for user %s: %s", profile.user_id, exc)
        await store.set_json(
            status_key,
            {
                "status": "failed",
                "reason": "embedding_unavailable",
                "finished_at": datetime.utcnow().isoformat(),
            },
        )
        return
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to index company profile for user %s", profile.user_id)
        await store.set_json(
            status_key,
            {
                "status": "failed",
                "reason": "unexpected_error",
                "finished_at": datetime.utcnow().isoformat(),
            },
        )
        return

    await store.set_json(
        status_key,
        {
            "status": "indexed",
            "finished_at": datetime.utcnow().isoformat(),
        },
    )


@router.post("/profile", response_model=CompanyProfileResponse)
async def save_company_profile(
    profile: CompanyProfile,
    background_tasks: BackgroundTasks,
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
    logger.info("Stored company profile for user %s", profile.user_id)
    return CompanyProfileResponse(profile=profile)


@router.post("/alpha-business", response_model=IntegrationConfirmationResponse)
async def confirm_alpha_business(
    confirmation: IntegrationConfirmation,
    store: RedisStore = Depends(get_store),
) -> IntegrationConfirmationResponse:
    payload = confirmation.model_dump(mode="json")
    payload["status"] = "connected"
    await store.set_json(f"integration:alpha-business:{confirmation.user_id}", payload)
    logger.info("Alpha Business integration confirmed for user %s", confirmation.user_id)
    return IntegrationConfirmationResponse(integration=confirmation)
