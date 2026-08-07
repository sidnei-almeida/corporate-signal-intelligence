"""Triage-log endpoints.

These are the only write paths in the API. They record what a human did with an alert,
which is what lets the tool eventually report measured review time and a confirmed rate
instead of the assumption the business case had to state.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.triage_schema import TriageEntry, TriageEntryRequest, TriageStatsResponse
from app.services import triage_service
from app.services.triage_service import TriageUnavailable

logger = logging.getLogger("app.routes.triage")

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("", response_model=TriageEntry, status_code=201)
def record_review(payload: TriageEntryRequest) -> TriageEntry:
    """Record one completed review of an alert."""
    try:
        return triage_service.record_entry(payload)
    except TriageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/stats", response_model=TriageStatsResponse)
def triage_stats() -> TriageStatsResponse:
    """Measured review time and confirmed rate, with the assumption alongside."""
    logger.info("triage_stats")
    return triage_service.get_stats()


@router.get("", response_model=list[TriageEntry])
def list_reviews(
    ticker: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[TriageEntry]:
    """Recent reviews, newest first."""
    return triage_service.get_entries(ticker=ticker, limit=limit)
