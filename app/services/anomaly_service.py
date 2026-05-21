"""Anomaly query orchestration."""

from __future__ import annotations

from typing import Any

from app.services import data_service
from app.utils.ticker import normalize_ticker


def list_anomalies(
    ticker: str | None = None,
    limit: int = 100,
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = True,
) -> dict[str, Any]:
    """Return filtered anomaly records."""
    records = data_service.query_anomalies(
        ticker=ticker,
        limit=limit,
        only_anomalies=only_anomalies,
        sort_by=sort_by,
        ascending=ascending,
    )
    return {"count": len(records), "records": records}


def get_top_anomalies(limit: int = 20) -> dict[str, Any]:
    """Return top anomalous records."""
    from app.utils.formatting import dataframe_to_records

    df = data_service.get_top_anomalies(limit=limit)
    records = dataframe_to_records(df)
    return {"count": len(records), "records": records}


def get_summary() -> list[dict]:
    """Return anomaly summary grouped by ticker."""
    return data_service.get_anomaly_summary()


def get_type_counts() -> list[dict]:
    """Return anomaly type frequency counts."""
    return data_service.get_anomaly_type_counts()


def get_company_anomalies(ticker: str) -> dict[str, Any]:
    """Return anomalies for one ticker."""
    df = data_service.get_company_anomalies(ticker)
    from app.utils.formatting import dataframe_to_records

    records = dataframe_to_records(df)
    return {
        "ticker": normalize_ticker(ticker),
        "count": len(records),
        "records": records,
    }
