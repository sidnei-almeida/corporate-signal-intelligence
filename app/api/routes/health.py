"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.data_source import get_active_data_source
from app.core.database import anomaly_results_populated, database_available
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
        "data_source": get_active_data_source(),
        "database_configured": database_available() or bool(settings.DATABASE_URL),
        "database_connected": database_available(),
        "database_populated": anomaly_results_populated(),
        "model_available": model_service.model_exists(),
    }
