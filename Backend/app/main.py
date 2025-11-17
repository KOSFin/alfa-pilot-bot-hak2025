"""Entry point for FastAPI + aiogram backend."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import chat, documents, health, integration
from .services.ai.orchestrator import AIOrchestrator
from .services.calculators.engine import CalculatorEngine
from .services.conversation.manager import ConversationManager
from .services.storage.knowledge_base import KnowledgeBase
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)


async def configure_webhook(bot: Bot, dispatcher: Dispatcher, settings) -> bool:
    webhook_base = settings.webhook_base_url
    if not webhook_base:
        logger.warning("WEBHOOK_BASE_URL is not configured; Telegram webhook will not be set.")
        return False

    webhook_url = f"{webhook_base.rstrip('/')}/telegram/webhook"
    webhook_kwargs = {
        "url": webhook_url,
        "drop_pending_updates": True,
        "allowed_updates": dispatcher.resolve_used_update_types(),
    }
    if settings.webhook_secret_token:
        webhook_kwargs["secret_token"] = settings.webhook_secret_token

    try:
        await bot.set_webhook(**webhook_kwargs)
        logger.info("Telegram webhook configured: %s", webhook_url)
        return True
    except TelegramBadRequest as exc:
        logger.error("Failed to configure Telegram webhook at %s: %s", webhook_url, exc)
    except Exception as exc:
        logger.exception("Unexpected error while configuring Telegram webhook: %s", exc)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()

    logger.info("Starting backend in %s mode", settings.environment)

    knowledge_base = KnowledgeBase()
    await knowledge_base.initialize()

    orchestrator = AIOrchestrator()
    conversation_manager = ConversationManager()
    calculator_engine = CalculatorEngine()

    try:
        storage = RedisStorage.from_url(settings.redis_url)
        await storage.redis.ping()
        logger.info("FSM storage connected to Redis")
    except Exception as exc:
        logger.warning("Redis FSM storage unavailable, falling back to in-memory storage: %s", exc)
        storage = MemoryStorage()

    dispatcher = Dispatcher(storage=storage)

    from bot.handlers import setup_handlers

    dispatcher.include_router(setup_handlers())
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    polling_task: asyncio.Task | None = None
    if not await configure_webhook(bot, dispatcher, settings):
        logger.info("Falling back to long polling mode for Telegram updates.")
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except TelegramBadRequest as exc:
            logger.warning("Could not remove webhook before starting polling: %s", exc)
        polling_task = asyncio.create_task(dispatcher.start_polling(bot))

    app.state.settings = settings
    app.state.knowledge_base = knowledge_base
    app.state.orchestrator = orchestrator
    app.state.conversation_manager = conversation_manager
    app.state.calculator_engine = calculator_engine
    app.state.bot = bot
    app.state.dispatcher = dispatcher
    app.state.polling_task = polling_task

    yield

    if polling_task:
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task

    await bot.session.close()
    await storage.close()
    await knowledge_base.aclose()


settings = get_settings()

def with_prefix(path: str) -> str:
    prefix = settings.api_prefix.rstrip("/")
    if not prefix:
        return path
    return f"{prefix}{path}"

app = FastAPI(
    title=settings.project_name,
    lifespan=lifespan,
    docs_url=with_prefix("/docs"),
    redoc_url=with_prefix("/redoc"),
    openapi_url=with_prefix("/openapi.json"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(integration.router)

app.include_router(api_router, prefix=settings.api_prefix)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict[str, str]:
    data = await request.json()
    update = Update.model_validate(data)
    bot: Bot = request.app.state.bot
    dispatcher: Dispatcher = request.app.state.dispatcher
    await dispatcher.feed_update(bot, update)
    return {"status": "accepted"}


@app.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {"message": "Alfa Pilot backend", "api": settings.api_prefix}
