"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.services import model_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Return service health and dependency status."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "data_source": "csv",
        "model_available": model_service.model_exists(),
    }
