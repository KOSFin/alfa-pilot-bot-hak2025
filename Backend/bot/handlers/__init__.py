"""Register bot handlers."""
from __future__ import annotations

from aiogram import Router

from . import callbacks, documents, general, integration, voice
from .fallback import router as fallback_router


def setup_handlers() -> Router:
    router = Router()
    router.include_router(general.router)
    router.include_router(documents.router)
    router.include_router(integration.router)
    router.include_router(voice.router)
    router.include_router(callbacks.router)
    router.include_router(fallback_router)
    return router
