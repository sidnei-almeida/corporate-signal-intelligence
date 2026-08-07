"""Anomaly endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas.anomaly_schema import (
    SCORE_SORT_ASCENDING,
    AlertBudget,
    AnomalyListResponse,
    AnomalySummary,
    AnomalyTypeCount,
)
from app.services import anomaly_service, data_service
from app.utils.ticker import is_plausible_ticker, is_reserved_path_segment, normalize_ticker

logger = logging.getLogger("app.routes.anomalies")

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


# --- Static routes (must stay before /{ticker}) ---


@router.get("", response_model=AnomalyListResponse)
def list_anomalies(
    ticker: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = SCORE_SORT_ASCENDING,
) -> AnomalyListResponse:
    """Return filtered anomaly records, most deviant first."""
    if ticker:
        normalized = normalize_ticker(ticker)
        if not data_service.ticker_exists(normalized):
            raise HTTPException(
                status_code=404,
                detail=f"Ticker '{normalized}' not found.",
            )
    logger.info("list_anomalies ticker=%s limit=%s", ticker, limit)
    result = anomaly_service.list_anomalies(
        ticker=normalize_ticker(ticker) if ticker else None,
        limit=limit,
        only_anomalies=only_anomalies,
        sort_by=sort_by,
        ascending=ascending,
    )
    return AnomalyListResponse(**result)


@router.get("/queue", response_model=AnomalyListResponse)
def alert_queue(
    budget_pct: float = Query(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Share of issuer-days allowed to raise an alert",
    ),
    ticker: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> AnomalyListResponse:
    """Return the alert queue at a given budget.

    The budget, not a score cutoff, is the operating control: it states how much analyst
    attention is on offer and the threshold follows from it.
    """
    if ticker:
        normalized = normalize_ticker(ticker)
        if not data_service.ticker_exists(normalized):
            raise HTTPException(status_code=404, detail=f"Ticker '{normalized}' not found.")
        ticker = normalized

    logger.info("alert_queue budget=%s ticker=%s limit=%s", budget_pct, ticker, limit)
    result = anomaly_service.get_alert_queue(
        budget_pct=budget_pct, ticker=ticker, limit=limit
    )
    return AnomalyListResponse(
        count=result["count"],
        budget=AlertBudget(**result["budget"]),
        records=result["records"],
    )


@router.get("/budget", response_model=AlertBudget)
def alert_budget(
    budget_pct: float = Query(default=1.0, ge=0.1, le=10.0),
) -> AlertBudget:
    """Return the threshold and alert volume a budget implies, without the rows."""
    logger.info("alert_budget budget=%s", budget_pct)
    return AlertBudget(**data_service.resolve_budget(budget_pct))


@router.get("/top", response_model=AnomalyListResponse)
def top_anomalies(limit: int = Query(default=20, ge=1, le=500)) -> AnomalyListResponse:
    """Return the most anomalous records."""
    logger.info("top_anomalies limit=%s", limit)
    result = anomaly_service.get_top_anomalies(limit=limit)
    return AnomalyListResponse(**result)


@router.get("/summary", response_model=list[AnomalySummary])
def anomaly_summary() -> list[AnomalySummary]:
    """Return grouped anomaly summary by ticker."""
    logger.info("anomaly_summary")
    summaries = anomaly_service.get_summary()
    return [AnomalySummary(**item) for item in summaries]


@router.get("/types", response_model=list[AnomalyTypeCount])
def anomaly_types() -> list[AnomalyTypeCount]:
    """Return exploded anomaly type counts."""
    logger.info("anomaly_types")
    counts = anomaly_service.get_type_counts()
    return [AnomalyTypeCount(**item) for item in counts]


# --- Dynamic route (must remain last) ---


@router.get("/{ticker}", response_model=AnomalyListResponse)
def company_anomalies(
    ticker: str = Path(..., min_length=1, max_length=12, description="Stock ticker symbol"),
) -> AnomalyListResponse:
    """Return anomalies for a specific ticker."""
    if is_reserved_path_segment(ticker):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown anomalies resource '{ticker}'. "
                "Use /anomalies/queue, /anomalies/budget, /anomalies/top, "
                "/anomalies/summary, or /anomalies/types."
            ),
        )
    if not is_plausible_ticker(ticker):
        raise HTTPException(status_code=404, detail=f"Invalid ticker '{ticker}'.")

    normalized = normalize_ticker(ticker)
    if not data_service.ticker_exists(normalized):
        raise HTTPException(status_code=404, detail=f"Ticker '{normalized}' not found.")

    logger.info("company_anomalies ticker=%s", normalized)
    result = anomaly_service.get_company_anomalies(normalized)
    return AnomalyListResponse(count=result["count"], records=result["records"])
