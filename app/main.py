import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.webhooks import router as webhooks_router
from app.integrations.whatsmeow_gateway_client import WhatsMeowGatewayClient
from app.logging_config import setup_logging
from app.services.session_store import SessionStore
from app.settings import get_settings
from bot_utilities.config_loader import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    from app.services.message_handler import MessageHandler

    sessions = SessionStore(max_history=int(config.get("MAX_HISTORY", 8)))
    whatsapp_gateway = WhatsMeowGatewayClient(settings)
    handler = MessageHandler(settings, whatsapp_gateway, sessions)

    app.state.settings = settings
    app.state.session_store = sessions
    app.state.whatsapp_gateway_client = whatsapp_gateway
    app.state.message_handler = handler

    logger.info(
        "AI WhatsApp Personal Assistant started | instance=%s | gateway=%s",
        settings.whatsapp_instance,
        settings.whatsapp_gateway_url,
    )
    yield
    logger.info("AI WhatsApp Personal Assistant shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI WhatsApp Personal Assistant",
        description="Assistente de IA integrado ao WhatsApp via gateway WhatsMeow",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(webhooks_router)
    return app


app = create_app()
