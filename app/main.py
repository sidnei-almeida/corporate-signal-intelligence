"""FastAPI application entrypoint."""

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
    """Warm lightweight API caches at startup; do not load joblib or wide CSVs."""
    clear_data_source_cache()
    try:
        data_service.warmup_api_cache()
        logger.info("Startup cache warmup completed.")
    except Exception as exc:
        logger.warning("Startup cache warmup skipped: %s", exc)
    yield


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

    cors_kwargs: dict = {
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if settings.is_development:
        cors_kwargs["allow_origins"] = ["*"]
        cors_kwargs["allow_credentials"] = False
    else:
        cors_kwargs["allow_origins"] = [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://corporate-signal-intelligence.onrender.com",
        ]
        cors_kwargs["allow_credentials"] = True

    application.add_middleware(CORSMiddleware, **cors_kwargs)
    application.add_middleware(RequestLoggingMiddleware)

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
