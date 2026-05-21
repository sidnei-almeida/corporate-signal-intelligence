"""Executive briefing endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.briefing_schema import (
    BriefingFromRecordRequest,
    BriefingRequest,
    BriefingResponse,
)
from app.services import data_service, groq_service
from app.services.anomaly_service import get_top_anomalies

router = APIRouter(prefix="/briefings", tags=["briefings"])


def _ensure_groq_configured() -> None:
    if not get_settings().GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Briefings are unavailable.",
        )


def _build_briefing_response(
    briefing: str,
    record: dict | None = None,
) -> BriefingResponse:
    settings = get_settings()
    return BriefingResponse(
        briefing=briefing,
        model_used=settings.GROQ_MODEL,
        ticker=record.get("ticker") if record else None,
        date=str(record.get("date"))[:10] if record and record.get("date") else None,
        source_record=record,
    )


@router.post("/generate", response_model=BriefingResponse)
def generate_briefing(request: BriefingRequest) -> BriefingResponse:
    """Generate a briefing for a ticker/date anomaly record."""
    _ensure_groq_configured()

    record = data_service.find_anomaly_record(request.ticker, request.date)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No anomaly record found for {request.ticker.upper()} on {request.date}.",
        )

    profile = data_service.get_company_profile(request.ticker)
    try:
        briefing = groq_service.generate_executive_briefing(
            anomaly_record=record,
            company_context=profile,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to generate executive briefing.") from exc

    return _build_briefing_response(briefing, record)


@router.post("/generate-from-record", response_model=BriefingResponse)
def generate_briefing_from_record(request: BriefingFromRecordRequest) -> BriefingResponse:
    """Generate a briefing directly from a provided anomaly record."""
    _ensure_groq_configured()

    try:
        briefing = groq_service.generate_executive_briefing(
            anomaly_record=request.record,
            company_context=request.company_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to generate executive briefing.") from exc

    return _build_briefing_response(briefing, request.record)


@router.get("/sample", response_model=BriefingResponse)
def sample_briefing() -> BriefingResponse:
    """Generate a briefing for the current top anomaly."""
    _ensure_groq_configured()

    top = get_top_anomalies(limit=1)
    if not top["records"]:
        raise HTTPException(status_code=404, detail="No anomaly records available.")

    record = top["records"][0]
    ticker = str(record.get("ticker", ""))
    profile = data_service.get_company_profile(ticker) if ticker else None

    try:
        briefing = groq_service.generate_executive_briefing(
            anomaly_record=record,
            company_context=profile,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to generate executive briefing.") from exc

    return _build_briefing_response(briefing, record)
