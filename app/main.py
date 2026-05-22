"""FastAPI application entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import anomalies, briefings, companies, health, model
from app.core.config import get_settings
from app.core.data_source import clear_data_source_cache
from app.core.logging_config import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.services import data_service

configure_logging()
logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Warm caches in background so /health responds immediately (Render cold start)."""
    clear_data_source_cache()

    async def _warmup() -> None:
        try:
            await asyncio.to_thread(data_service.warmup_api_cache)
            logger.info("Startup cache warmup completed.")
        except Exception as exc:
            logger.warning("Startup cache warmup skipped: %s", exc)

    warmup_task = asyncio.create_task(_warmup())
    yield
    warmup_task.cancel()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        version=API_VERSION,
        description=(
            "Corporate intelligence API combining market data, SEC filings, "
            "anomaly detection, and Groq-powered executive briefings."
        ),
        lifespan=lifespan,
    )

    # RequestLogging first, CORS last → CORS runs outermost (handles OPTIONS first).
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS allow_origins=%s", settings.cors_origins)

    application.include_router(health.router)
    application.include_router(companies.router)
    application.include_router(anomalies.router)
    application.include_router(briefings.router)
    application.include_router(model.router)

    @application.get("/", tags=["system"])
    def root() -> dict:
        return {
            "service": settings.APP_NAME,
            "version": API_VERSION,
            "docs": "/docs",
            "health": "/health",
        }

    return application


app = create_app()
