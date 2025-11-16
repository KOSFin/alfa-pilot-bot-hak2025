"""Integration endpoints for Telegram Web App onboarding."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.integration import CompanyProfile, CompanyProfileResponse
from ..services.storage.redis_store import RedisStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integration", tags=["integration"])


def get_store() -> RedisStore:
    return RedisStore()


@router.post("/profile", response_model=CompanyProfileResponse)
async def save_company_profile(profile: CompanyProfile, store: RedisStore = Depends(get_store)) -> CompanyProfileResponse:
    """Persist the company profile submitted from the Telegram Web App."""
    if not profile.company_name.strip():
        raise HTTPException(status_code=422, detail="Company name is required")

    key = f"company-profile:{profile.user_id}"
    await store.set_json(key, profile.model_dump(mode="json"))
    logger.info("Stored company profile for user %s", profile.user_id)
    return CompanyProfileResponse(profile=profile)
