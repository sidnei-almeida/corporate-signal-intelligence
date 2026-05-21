"""PostgreSQL repository for API data access."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import select, text

from app.core.database import session_scope
from app.models.database_models import AnomalyResult
from app.utils.formatting import dataframe_to_records, normalize_date, safe_bool, safe_float
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


def _load_anomaly_dataframe() -> pd.DataFrame:
    """Load all anomaly results from PostgreSQL into a DataFrame."""
    query = text(
        f"""
        SELECT {", ".join(_ANOMALY_COLUMNS)}
        FROM anomaly_results
        ORDER BY ticker, date
        """
    )
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


def get_company_anomalies(ticker: str) -> pd.DataFrame:
    df = _load_anomaly_dataframe()
    normalized = normalize_ticker(ticker)
    filtered = df.loc[df["ticker"] == normalized].copy()
    if "is_anomaly" in filtered.columns:
        return filtered.loc[filtered["is_anomaly"] == True].copy()  # noqa: E712
    return filtered


def get_top_anomalies(limit: int = 20) -> pd.DataFrame:
    df = _load_anomaly_dataframe()
    if df.empty:
        return df
    working = df.loc[df["is_anomaly"] == True].copy() if "is_anomaly" in df.columns else df.copy()  # noqa: E712
    if "anomaly_score" in working.columns:
        working = working.sort_values("anomaly_score", ascending=True).copy()
    return working.head(limit).copy()


def get_anomaly_summary() -> list[dict[str, Any]]:
    df = _load_anomaly_dataframe()
    if df.empty:
        return []
    summaries: list[dict[str, Any]] = []
    for ticker, group in df.groupby("ticker", sort=True):
        group = group.copy()
        rows = len(group)
        anomalies = int(group["is_anomaly"].fillna(False).astype(bool).sum()) if "is_anomaly" in group else 0
        scores = group["anomaly_score"] if "anomaly_score" in group.columns else pd.Series(dtype=float)
        summaries.append(
            {
                "ticker": str(ticker),
                "rows": rows,
                "anomalies": anomalies,
                "anomaly_rate": round(anomalies / rows, 4) if rows else 0.0,
                "min_score": safe_float(scores.min()) if not scores.empty else None,
                "avg_score": safe_float(scores.mean()) if not scores.empty else None,
                "max_score": safe_float(scores.max()) if not scores.empty else None,
            }
        )
    return sorted(summaries, key=lambda item: item["ticker"])


def get_company_profile(ticker: str) -> dict[str, Any] | None:
    normalized = normalize_ticker(ticker)
    if not ticker_exists(normalized):
        return None
    df = _load_anomaly_dataframe()
    company_df = df.loc[df["ticker"] == normalized].copy()
    if company_df.empty:
        return None
    company_df = company_df.sort_values("date")
    first_date = normalize_date(company_df["date"].iloc[0])
    last_date = normalize_date(company_df["date"].iloc[-1])
    if "is_anomaly" in company_df.columns:
        anomaly_df = company_df.loc[company_df["is_anomaly"] == True].copy()  # noqa: E712
        anomaly_count = len(anomaly_df)
    else:
        anomaly_df = pd.DataFrame()
        anomaly_count = 0
    latest_anomaly = None
    if not anomaly_df.empty:
        latest_row = anomaly_df.sort_values("date").iloc[-1]
        latest_anomaly = dataframe_to_records(latest_row.to_frame().T)[0]
    row_count = len(company_df)
    return {
        "ticker": normalized,
        "row_count": row_count,
        "first_date": first_date,
        "last_date": last_date,
        "anomaly_count": anomaly_count,
        "anomaly_rate": round(anomaly_count / row_count, 4) if row_count else 0.0,
        "latest_anomaly": latest_anomaly,
    }


def find_anomaly_record(ticker: str, date_value: str) -> dict[str, Any] | None:
    normalized = normalize_ticker(ticker)
    target = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(target):
        return None
    with session_scope() as session:
        row = session.scalars(
            select(AnomalyResult).where(
                AnomalyResult.ticker == normalized,
                AnomalyResult.date == target.date(),
            )
        ).first()
        if row is None:
            return None
        data = {col: getattr(row, col) for col in _ANOMALY_COLUMNS}
    data["date"] = normalize_date(data.get("date"))
    return data


def query_anomalies(
    ticker: str | None = None,
    limit: int = 100,
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = True,
) -> list[dict[str, Any]]:
    df = _load_anomaly_dataframe()
    if df.empty:
        return []
    if ticker:
        df = df.loc[df["ticker"] == normalize_ticker(ticker)].copy()
    if df.empty:
        return []
    if only_anomalies and "is_anomaly" in df.columns:
        df = df.loc[df["is_anomaly"] == True].copy()  # noqa: E712
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending, na_position="last").copy()
    elif "anomaly_score" in df.columns:
        df = df.sort_values("anomaly_score", ascending=True, na_position="last").copy()
    return dataframe_to_records(df.head(limit))


def get_anomaly_type_counts() -> list[dict[str, int | str]]:
    df = _load_anomaly_dataframe()
    if df.empty or "anomaly_type" not in df.columns:
        return []
    working = df.loc[df["is_anomaly"] == True].copy() if "is_anomaly" in df.columns else df.copy()  # noqa: E712
    counts: dict[str, int] = {}
    for value in working["anomaly_type"].dropna():
        for part in str(value).split(","):
            label = part.strip()
            if label:
                counts[label] = counts.get(label, 0) + 1
    return [{"anomaly_type": key, "count": value} for key, value in sorted(counts.items())]
