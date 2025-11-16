"""Entry point for FastAPI + aiogram backend."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import chat, documents, health
from .services.ai.orchestrator import AIOrchestrator
from .services.calculators.engine import CalculatorEngine
from .services.conversation.manager import ConversationManager
from .services.storage.knowledge_base import KnowledgeBase
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)


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

    storage = RedisStorage.from_url(settings.redis_url)
    dispatcher = Dispatcher(storage=storage)

    from bot.handlers import setup_handlers  # local import to avoid circular

    dispatcher.include_router(setup_handlers())
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    app.state.settings = settings
    app.state.knowledge_base = knowledge_base
    app.state.orchestrator = orchestrator
    app.state.conversation_manager = conversation_manager
    app.state.calculator_engine = calculator_engine
    app.state.bot = bot
    app.state.dispatcher = dispatcher

    yield

    await bot.session.close()
    await storage.close()
    await knowledge_base.aclose()


settings = get_settings()
app = FastAPI(title=settings.project_name, lifespan=lifespan)

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
