"""PostgreSQL repository — SQL-first, minimal memory."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import text

from app.core.database import session_scope
from app.utils.formatting import normalize_date, safe_bool
from app.utils.ticker import normalize_ticker

_ANOMALY_COLUMNS = [
    "ticker",
    "date",
    "anomaly_score",
    "anomaly_label",
    "is_anomaly",
    "anomaly_type",
    "has_missing_financial_data",
    "daily_return",
    "volume_zscore_30d",
    "return_zscore_30d",
    "volatility_30d",
    "filing_count_30d",
    "form_8k_count_30d",
    "revenue_growth_qoq",
    "net_margin",
    "operating_margin",
]

_SORTABLE_COLUMNS = frozenset(_ANOMALY_COLUMNS)


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a DB row mapping to a JSON-friendly dict."""
    data = dict(row._mapping)
    if "date" in data:
        data["date"] = normalize_date(data.get("date"))
    if "is_anomaly" in data:
        data["is_anomaly"] = safe_bool(data.get("is_anomaly"))
    return data


def fetch_anomaly_minimal_dataframe() -> pd.DataFrame:
    """Load minimal anomaly columns once (startup cache build only)."""
    cols = ", ".join(_ANOMALY_COLUMNS)
    query = text(f"SELECT {cols} FROM anomaly_results ORDER BY ticker, date")
    with session_scope() as session:
        df = pd.read_sql(query, session.bind)
    if df.empty:
        return df
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "is_anomaly" in df.columns:
        df["is_anomaly"] = df["is_anomaly"].apply(safe_bool)
    return df


def get_available_companies() -> list[str]:
    with session_scope() as session:
        rows = session.execute(
            text("SELECT DISTINCT ticker FROM anomaly_results ORDER BY ticker")
        ).fetchall()
    return [str(row[0]).upper() for row in rows]


def ticker_exists(ticker: str) -> bool:
    normalized = normalize_ticker(ticker)
    with session_scope() as session:
        row = session.execute(
            text("SELECT 1 FROM anomaly_results WHERE ticker = :ticker LIMIT 1"),
            {"ticker": normalized},
        ).first()
    return row is not None


def find_anomaly_record(ticker: str, date_value: str) -> dict[str, Any] | None:
    normalized = normalize_ticker(ticker)
    target = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(target):
        return None
    cols = ", ".join(_ANOMALY_COLUMNS)
    sql = text(
        f"""
        SELECT {cols} FROM anomaly_results
        WHERE ticker = :ticker AND date = :date
        LIMIT 1
        """
    )
    with session_scope() as session:
        row = session.execute(
            sql,
            {"ticker": normalized, "date": target.date()},
        ).first()
    if row is None:
        return None
    return _row_to_dict(row)


def get_company_anomaly_records(ticker: str) -> list[dict[str, Any]]:
    normalized = normalize_ticker(ticker)
    cols = ", ".join(_ANOMALY_COLUMNS)
    sql = text(
        f"""
        SELECT {cols} FROM anomaly_results
        WHERE ticker = :ticker AND is_anomaly = true
        ORDER BY date
        """
    )
    with session_scope() as session:
        rows = session.execute(sql, {"ticker": normalized}).fetchall()
    return [_row_to_dict(row) for row in rows]


def query_anomalies(
    ticker: str | None = None,
    limit: int = 100,
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = True,
) -> list[dict[str, Any]]:
    cols = ", ".join(_ANOMALY_COLUMNS)
    order_col = sort_by if sort_by in _SORTABLE_COLUMNS else "anomaly_score"
    direction = "ASC" if ascending else "DESC"
    clauses = ["WHERE 1=1"]
    params: dict[str, Any] = {"limit": limit}
    if ticker:
        clauses.append("AND ticker = :ticker")
        params["ticker"] = normalize_ticker(ticker)
    if only_anomalies:
        clauses.append("AND is_anomaly = true")
    where_sql = " ".join(clauses)
    sql = text(
        f"""
        SELECT {cols} FROM anomaly_results
        {where_sql}
        ORDER BY {order_col} {direction} NULLS LAST
        LIMIT :limit
        """
    )
    with session_scope() as session:
        rows = session.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_company_profile(ticker: str) -> dict[str, Any] | None:
    """Point lookup — prefer data_service cache when available."""
    from app.services import memory_cache

    cache = memory_cache.get_cache()
    normalized = normalize_ticker(ticker)
    if cache.ready:
        return cache.company_profiles.get(normalized)
    if not ticker_exists(normalized):
        return None

    sql = text(
        """
        SELECT
            ticker,
            COUNT(*) AS row_count,
            MIN(date) AS first_date,
            MAX(date) AS last_date,
            SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS anomaly_count
        FROM anomaly_results
        WHERE ticker = :ticker
        GROUP BY ticker
        """
    )
    with session_scope() as session:
        row = session.execute(sql, {"ticker": normalized}).first()
    if row is None:
        return None

    row_count = int(row.row_count)
    anomaly_count = int(row.anomaly_count)
    latest_anomaly = None
    if anomaly_count > 0:
        latest_sql = text(
            f"""
            SELECT {", ".join(_ANOMALY_COLUMNS)} FROM anomaly_results
            WHERE ticker = :ticker AND is_anomaly = true
            ORDER BY date DESC LIMIT 1
            """
        )
        with session_scope() as session:
            latest_row = session.execute(latest_sql, {"ticker": normalized}).first()
        if latest_row is not None:
            latest_anomaly = _row_to_dict(latest_row)

    return {
        "ticker": normalized,
        "row_count": row_count,
        "first_date": normalize_date(row.first_date),
        "last_date": normalize_date(row.last_date),
        "anomaly_count": anomaly_count,
        "anomaly_rate": round(anomaly_count / row_count, 4) if row_count else 0.0,
        "latest_anomaly": latest_anomaly,
    }
