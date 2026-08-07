"""Anomaly query orchestration."""

from __future__ import annotations

from typing import Any

from app.schemas.anomaly_schema import SCORE_SORT_ASCENDING
from app.services import data_service
from app.utils.ticker import normalize_ticker


def _with_severity(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the severity tier so every consumer reads one definition of it."""
    for record in records:
        score = record.get("anomaly_score")
        record["severity"] = data_service.severity_tier(
            float(score) if score is not None else None
        )
    return records


def list_anomalies(
    ticker: str | None = None,
    limit: int = 100,
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = SCORE_SORT_ASCENDING,
) -> dict[str, Any]:
    """Return filtered anomaly records."""
    records = data_service.query_anomalies(
        ticker=ticker,
        limit=limit,
        only_anomalies=only_anomalies,
        sort_by=sort_by,
        ascending=ascending,
    )
    return {"count": len(records), "records": _with_severity(records)}


def get_alert_queue(
    budget_pct: float = 1.0,
    ticker: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Return the alert queue implied by a budget."""
    records, budget = data_service.query_by_budget(
        budget_pct=budget_pct, ticker=ticker, limit=limit
    )
    return {"count": len(records), "budget": budget, "records": _with_severity(records)}


def get_top_anomalies(limit: int = 20) -> dict[str, Any]:
    """Return top anomalous records from startup cache."""
    records = data_service.get_top_anomalies_cached(limit=limit)
    return {"count": len(records), "records": _with_severity(records)}


def get_summary() -> list[dict]:
    """Return anomaly summary grouped by ticker (cached)."""
    return data_service.get_anomaly_summary_cached()


def get_type_counts() -> list[dict]:
    """Return anomaly type frequency counts (cached)."""
    return data_service.get_anomaly_types_cached()


def get_company_anomalies(ticker: str) -> dict[str, Any]:
    """Return anomalies for one ticker."""
    records = data_service.get_company_anomalies(ticker)
    return {
        "ticker": normalize_ticker(ticker),
        "count": len(records),
        "records": _with_severity(records),
    }
