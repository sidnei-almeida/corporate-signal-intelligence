"""CSV data loading and query helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.utils.formatting import dataframe_to_records, normalize_date, safe_bool, safe_float

ANOMALY_RESULTS_FILE = "anomaly_detection_results.csv"
TOP_ANOMALIES_FILE = "top_anomalies_final.csv"
MODEL_READY_FILE = "model_ready_dataset.csv"
MARKET_FEATURES_FILE = "market_features.csv"
FILING_FEATURES_FILE = "filing_features.csv"
FINANCIAL_FEATURES_FILE = "financial_features_selected.csv"

IMPORTANT_COLUMNS = [
    "ticker",
    "date",
    "anomaly_score",
    "is_anomaly",
    "anomaly_type",
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


def _csv_path(filename: str) -> Path:
    return get_settings().data_path / filename


@lru_cache
def _load_csv(filename: str) -> pd.DataFrame:
    """Load and cache a CSV file from the data directory."""
    path = _csv_path(filename)
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper()
    return df


def _normalize_anomaly_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure expected anomaly columns exist with graceful fallbacks."""
    if df.empty:
        return df
    frame = df.copy()
    if "is_anomaly" not in frame.columns and "anomaly_label" in frame.columns:
        frame["is_anomaly"] = frame["anomaly_label"].astype(int).astype(bool)
    if "is_anomaly" in frame.columns:
        frame["is_anomaly"] = frame["is_anomaly"].apply(safe_bool)
    if "anomaly_score" in frame.columns:
        frame["anomaly_score"] = pd.to_numeric(frame["anomaly_score"], errors="coerce")
    return frame


def load_anomaly_results() -> pd.DataFrame:
    """Load anomaly detection results."""
    return _normalize_anomaly_frame(_load_csv(ANOMALY_RESULTS_FILE))


def load_model_ready_dataset() -> pd.DataFrame:
    """Load the model-ready feature dataset."""
    return _load_csv(MODEL_READY_FILE)


def load_market_features() -> pd.DataFrame:
    """Load market feature dataset."""
    return _load_csv(MARKET_FEATURES_FILE)


def load_filing_features() -> pd.DataFrame:
    """Load filing feature dataset."""
    return _load_csv(FILING_FEATURES_FILE)


def load_financial_features() -> pd.DataFrame:
    """Load selected financial features."""
    return _load_csv(FINANCIAL_FEATURES_FILE)


def _load_top_anomalies_file() -> pd.DataFrame:
    path = _csv_path(TOP_ANOMALIES_FILE)
    if not path.is_file():
        return pd.DataFrame()
    return _normalize_anomaly_frame(_load_csv(TOP_ANOMALIES_FILE))


def get_available_companies() -> list[str]:
    """Return sorted list of tickers present in anomaly results."""
    df = load_anomaly_results()
    if df.empty or "ticker" not in df.columns:
        return []
    return sorted(df["ticker"].dropna().unique().tolist())


def _filter_ticker(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df.empty or "ticker" not in df.columns:
        return df
    return df[df["ticker"] == ticker.upper()].copy()


def get_company_anomalies(ticker: str) -> pd.DataFrame:
    """Return anomaly rows for a specific ticker."""
    df = load_anomaly_results()
    filtered = _filter_ticker(df, ticker)
    if "is_anomaly" in filtered.columns:
        return filtered[filtered["is_anomaly"] == True].copy()  # noqa: E712
    return filtered


def get_top_anomalies(limit: int = 20) -> pd.DataFrame:
    """Return top anomalies from file or computed from full results."""
    top_df = _load_top_anomalies_file()
    if not top_df.empty:
        if "anomaly_score" in top_df.columns:
            top_df = top_df.sort_values("anomaly_score", ascending=True)
        return top_df.head(limit).copy()

    df = load_anomaly_results()
    if df.empty:
        return df
    if "is_anomaly" in df.columns:
        df = df[df["is_anomaly"] == True].copy()  # noqa: E712
    if "anomaly_score" in df.columns:
        df = df.sort_values("anomaly_score", ascending=True)
    return df.head(limit).copy()


def get_anomaly_summary() -> list[dict[str, Any]]:
    """Return grouped anomaly summary by ticker."""
    df = load_anomaly_results()
    if df.empty or "ticker" not in df.columns:
        return []

    summaries: list[dict[str, Any]] = []
    for ticker, group in df.groupby("ticker"):
        rows = len(group)
        if "is_anomaly" in group.columns:
            anomalies = int(group["is_anomaly"].fillna(False).astype(bool).sum())
        else:
            anomalies = 0
        scores = group["anomaly_score"] if "anomaly_score" in group.columns else pd.Series(dtype=float)
        summaries.append(
            {
                "ticker": ticker,
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
    """Build a company profile from anomaly results."""
    df = load_anomaly_results()
    company_df = _filter_ticker(df, ticker)
    if company_df.empty:
        return None

    if "date" in company_df.columns:
        company_df = company_df.sort_values("date")
        first_date = normalize_date(company_df["date"].iloc[0])
        last_date = normalize_date(company_df["date"].iloc[-1])
    else:
        first_date = None
        last_date = None

    if "is_anomaly" in company_df.columns:
        anomaly_df = company_df[company_df["is_anomaly"] == True].copy()  # noqa: E712
        anomaly_count = len(anomaly_df)
    else:
        anomaly_df = pd.DataFrame()
        anomaly_count = 0

    row_count = len(company_df)
    latest_anomaly = None
    if not anomaly_df.empty:
        latest_row = anomaly_df.sort_values("date").iloc[-1]
        latest_anomaly = dataframe_to_records(latest_row.to_frame().T)[0]

    return {
        "ticker": ticker.upper(),
        "row_count": row_count,
        "first_date": first_date,
        "last_date": last_date,
        "anomaly_count": anomaly_count,
        "anomaly_rate": round(anomaly_count / row_count, 4) if row_count else 0.0,
        "latest_anomaly": latest_anomaly,
    }


def find_anomaly_record(ticker: str, date_value: str) -> dict[str, Any] | None:
    """Find a specific anomaly record by ticker and date."""
    df = load_anomaly_results()
    company_df = _filter_ticker(df, ticker)
    if company_df.empty or "date" not in company_df.columns:
        return None

    target = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(target):
        return None

    matches = company_df[company_df["date"].dt.date == target.date()]
    if matches.empty:
        return None
    return dataframe_to_records(matches.head(1))[0]


def query_anomalies(
    ticker: str | None = None,
    limit: int = 100,
    only_anomalies: bool = True,
    sort_by: str = "anomaly_score",
    ascending: bool = True,
) -> list[dict[str, Any]]:
    """Query anomaly records with optional filters."""
    df = load_anomaly_results()
    if df.empty:
        return []

    if ticker:
        df = _filter_ticker(df, ticker)
    if df.empty:
        return []

    if only_anomalies and "is_anomaly" in df.columns:
        df = df[df["is_anomaly"] == True].copy()  # noqa: E712

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending, na_position="last")
    elif "anomaly_score" in df.columns:
        df = df.sort_values("anomaly_score", ascending=True, na_position="last")

    return dataframe_to_records(df.head(limit))


def get_anomaly_type_counts() -> list[dict[str, int | str]]:
    """Return counts of individual anomaly types."""
    df = load_anomaly_results()
    if df.empty or "anomaly_type" not in df.columns:
        return []

    if "is_anomaly" in df.columns:
        df = df[df["is_anomaly"] == True].copy()  # noqa: E712

    counts: dict[str, int] = {}
    for value in df["anomaly_type"].dropna():
        for part in str(value).split(","):
            label = part.strip()
            if label:
                counts[label] = counts.get(label, 0) + 1
    return [{"anomaly_type": key, "count": value} for key, value in sorted(counts.items())]
