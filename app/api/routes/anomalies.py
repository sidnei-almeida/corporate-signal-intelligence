"""Anomaly endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.anomaly_schema import AnomalyListResponse, AnomalySummary, AnomalyTypeCount
from app.services import anomaly_service, data_service

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=AnomalyListResponse)
def list_anomalies(
    ticker: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = True,
) -> AnomalyListResponse:
    """Return filtered anomaly records."""
    if ticker and ticker.upper() not in data_service.get_available_companies():
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found.")
    result = anomaly_service.list_anomalies(
        ticker=ticker,
        limit=limit,
        only_anomalies=only_anomalies,
        sort_by=sort_by,
        ascending=ascending,
    )
    return AnomalyListResponse(**result)


@router.get("/top", response_model=AnomalyListResponse)
def top_anomalies(limit: int = Query(default=20, ge=1, le=500)) -> AnomalyListResponse:
    """Return the most anomalous records."""
    result = anomaly_service.get_top_anomalies(limit=limit)
    return AnomalyListResponse(**result)


@router.get("/summary", response_model=list[AnomalySummary])
def anomaly_summary() -> list[AnomalySummary]:
    """Return grouped anomaly summary by ticker."""
    summaries = anomaly_service.get_summary()
    return [AnomalySummary(**item) for item in summaries]


@router.get("/types", response_model=list[AnomalyTypeCount])
def anomaly_types() -> list[AnomalyTypeCount]:
    """Return exploded anomaly type counts."""
    counts = anomaly_service.get_type_counts()
    return [AnomalyTypeCount(**item) for item in counts]


@router.get("/{ticker}", response_model=AnomalyListResponse)
def company_anomalies(ticker: str) -> AnomalyListResponse:
    """Return anomalies for a specific ticker."""
    if ticker.upper() not in data_service.get_available_companies():
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found.")
    result = anomaly_service.get_company_anomalies(ticker)
    return AnomalyListResponse(count=result["count"], records=result["records"])
