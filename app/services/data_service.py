"""CSV/DB data access with minimal memory footprint and startup caches."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.core.data_source import using_database
from app.repositories import db_repository
from app.services import memory_cache
from app.utils.formatting import dataframe_to_records, normalize_date, safe_bool, safe_float
from app.utils.ticker import normalize_ticker

logger = logging.getLogger(__name__)

ANOMALY_RESULTS_FILE = "anomaly_detection_results.csv"
TOP_ANOMALIES_FILE = "top_anomalies_final.csv"
MODEL_READY_FILE = "model_ready_dataset.csv"
MARKET_FEATURES_FILE = "market_features.csv"
FILING_FEATURES_FILE = "filing_features.csv"
FINANCIAL_FEATURES_FILE = "financial_features_selected.csv"

# Columns loaded for API paths (avoids wide 60+ column CSV in memory).
MINIMAL_ANOMALY_COLUMNS = [
    "ticker",
    "date",
    "anomaly_score",
    "anomaly_label",
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

TOP_ANOMALY_COLUMNS = [
    "ticker",
    "date",
    "anomaly_score",
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
    "is_anomaly",
]

IMPORTANT_COLUMNS = MINIMAL_ANOMALY_COLUMNS  # backwards compatibility


def _csv_path(filename: str) -> Path:
    return get_settings().data_path / filename


def _existing_columns(path: Path, requested: list[str]) -> list[str]:
    if not path.is_file():
        return []
    header = pd.read_csv(path, nrows=0).columns.tolist()
    return [col for col in requested if col in header]


def _normalize_anomaly_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types in-place on a minimal anomaly frame."""
    if df.empty:
        return df
    if "is_anomaly" not in df.columns and "anomaly_label" in df.columns:
        df["is_anomaly"] = df["anomaly_label"] == -1
    if "is_anomaly" in df.columns:
        df["is_anomaly"] = df["is_anomaly"].apply(safe_bool)
    if "anomaly_score" in df.columns:
        df["anomaly_score"] = pd.to_numeric(df["anomaly_score"], errors="coerce")
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def get_anomaly_results_minimal() -> pd.DataFrame:
    """
    Load only API-relevant columns from anomaly_detection_results.csv.
    Does not load other dataset files.
    """
    if using_database():
        return db_repository.fetch_anomaly_minimal_dataframe()

    path = _csv_path(ANOMALY_RESULTS_FILE)
    usecols = _existing_columns(path, MINIMAL_ANOMALY_COLUMNS)
    if not usecols:
        return pd.DataFrame()
    df = pd.read_csv(path, usecols=usecols)
    return _normalize_anomaly_frame(df)


def _load_optional_csv(filename: str) -> pd.DataFrame:
    """Lazy-load a non-default dataset only when explicitly requested."""
    path = _csv_path(filename)
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df


def load_anomaly_results() -> pd.DataFrame:
    """Return anomaly results (minimal columns). Prefer cache-backed access in hot paths."""
    return get_anomaly_results_minimal()


def load_model_ready_dataset() -> pd.DataFrame:
    """Load model-ready dataset on demand (not used by default API routes)."""
    return _load_optional_csv(MODEL_READY_FILE)


def load_market_features() -> pd.DataFrame:
    """Load market features on demand (not used by default API routes)."""
    return _load_optional_csv(MARKET_FEATURES_FILE)


def load_filing_features() -> pd.DataFrame:
    """Load filing features on demand (not used by default API routes)."""
    return _load_optional_csv(FILING_FEATURES_FILE)


def load_financial_features() -> pd.DataFrame:
    """Load financial features on demand (not used by default API routes)."""
    return _load_optional_csv(FINANCIAL_FEATURES_FILE)


def _build_caches_from_dataframe(df: pd.DataFrame, top_n: int) -> None:
    """Single-pass construction of lightweight API caches from a minimal frame."""
    if df.empty or "ticker" not in df.columns:
        memory_cache.set_cache(
            tickers=frozenset(),
            companies_list=[],
            anomaly_summary=[],
            top_anomalies=[],
            anomaly_type_counts=[],
            company_profiles={},
        )
        return

    tickers = frozenset(df["ticker"].dropna().unique())
    summaries: list[dict[str, Any]] = []
    companies_list: list[dict[str, Any]] = []
    profiles: dict[str, dict[str, Any]] = {}

    for ticker, group in df.groupby("ticker", sort=True):
        ticker_str = str(ticker)
        rows = len(group)
        if "is_anomaly" in group.columns:
            anomaly_mask = group["is_anomaly"].fillna(False).astype(bool)
            anomalies = int(anomaly_mask.sum())
            anomaly_rows = group.loc[anomaly_mask]
        else:
            anomalies = 0
            anomaly_rows = group.iloc[0:0]

        scores = group["anomaly_score"] if "anomaly_score" in group.columns else pd.Series(dtype=float)
        summary = {
            "ticker": ticker_str,
            "rows": rows,
            "anomalies": anomalies,
            "anomaly_rate": round(anomalies / rows, 4) if rows else 0.0,
            "min_score": safe_float(scores.min()) if not scores.empty else None,
            "avg_score": safe_float(scores.mean()) if not scores.empty else None,
            "max_score": safe_float(scores.max()) if not scores.empty else None,
        }
        summaries.append(summary)

        if "date" in group.columns:
            ordered = group.sort_values("date")
            first_date = normalize_date(ordered["date"].iloc[0])
            last_date = normalize_date(ordered["date"].iloc[-1])
        else:
            first_date = last_date = None

        latest_anomaly = None
        if not anomaly_rows.empty and "date" in anomaly_rows.columns:
            latest = anomaly_rows.sort_values("date").iloc[-1]
            latest_anomaly = dataframe_to_records(latest.to_frame().T)[0]

        profile = {
            "ticker": ticker_str,
            "row_count": rows,
            "first_date": first_date,
            "last_date": last_date,
            "anomaly_count": anomalies,
            "anomaly_rate": round(anomalies / rows, 4) if rows else 0.0,
            "latest_anomaly": latest_anomaly,
        }
        profiles[ticker_str] = profile
        companies_list.append(
            {
                "ticker": ticker_str,
                "row_count": rows,
                "first_date": first_date,
                "last_date": last_date,
                "anomaly_count": anomalies,
                "anomaly_rate": profile["anomaly_rate"],
            }
        )

    summaries.sort(key=lambda item: item["ticker"])
    companies_list.sort(key=lambda item: item["ticker"])

    top_records: list[dict[str, Any]] = []
    top_path = _csv_path(TOP_ANOMALIES_FILE)
    if top_path.is_file():
        top_usecols = _existing_columns(top_path, TOP_ANOMALY_COLUMNS)
        if top_usecols:
            top_df = _normalize_anomaly_frame(pd.read_csv(top_path, usecols=top_usecols))
            if "anomaly_score" in top_df.columns:
                top_df = top_df.sort_values("anomaly_score", ascending=True)
            top_records = dataframe_to_records(top_df.head(top_n))

    if not top_records and "is_anomaly" in df.columns:
        anomaly_only = df.loc[df["is_anomaly"].fillna(False).astype(bool)]
        if "anomaly_score" in anomaly_only.columns:
            anomaly_only = anomaly_only.sort_values("anomaly_score", ascending=True)
        top_records = dataframe_to_records(anomaly_only.head(top_n))

    type_counts: dict[str, int] = {}
    if "anomaly_type" in df.columns and "is_anomaly" in df.columns:
        flagged = df.loc[df["is_anomaly"].fillna(False).astype(bool), "anomaly_type"]
        for value in flagged.dropna():
            for part in str(value).split(","):
                label = part.strip()
                if label:
                    type_counts[label] = type_counts.get(label, 0) + 1

    memory_cache.set_cache(
        tickers=tickers,
        companies_list=companies_list,
        anomaly_summary=summaries,
        top_anomalies=top_records,
        anomaly_type_counts=[
            {"anomaly_type": key, "count": value}
            for key, value in sorted(type_counts.items())
        ],
        company_profiles=profiles,
    )


def warmup_api_cache(top_n: int | None = None) -> None:
    """Build in-memory API caches once at startup."""
    limit = top_n or memory_cache.DEFAULT_TOP_CACHE_SIZE
    if using_database():
        df = db_repository.fetch_anomaly_minimal_dataframe()
    else:
        df = get_anomaly_results_minimal()
    _build_caches_from_dataframe(df, limit)
    del df


def get_available_companies() -> list[str]:
    cache = memory_cache.get_cache()
    if cache.ready:
        return sorted(cache.tickers)
    if using_database():
        return db_repository.get_available_companies()
    return sorted(get_anomaly_results_minimal()["ticker"].dropna().unique())


def ticker_exists(ticker: str) -> bool:
    normalized = normalize_ticker(ticker)
    cache = memory_cache.get_cache()
    if cache.ready:
        return normalized in cache.tickers
    if using_database():
        return db_repository.ticker_exists(ticker)
    return normalized in get_available_companies()


def get_companies_list_cached() -> list[dict[str, Any]]:
    """Return precomputed company list items."""
    cache = memory_cache.get_cache()
    if cache.ready:
        return list(cache.companies_list)
    warmup_api_cache()
    return list(memory_cache.get_cache().companies_list)


def get_anomaly_summary_cached() -> list[dict[str, Any]]:
    cache = memory_cache.get_cache()
    if cache.ready:
        return list(cache.anomaly_summary)
    warmup_api_cache()
    return list(memory_cache.get_cache().anomaly_summary)


def get_top_anomalies_cached(limit: int = 20) -> list[dict[str, Any]]:
    cache = memory_cache.get_cache()
    if cache.ready:
        return list(cache.top_anomalies[:limit])
    warmup_api_cache()
    return list(memory_cache.get_cache().top_anomalies[:limit])


def get_anomaly_types_cached() -> list[dict[str, int | str]]:
    cache = memory_cache.get_cache()
    if cache.ready:
        return list(cache.anomaly_type_counts)
    warmup_api_cache()
    return list(memory_cache.get_cache().anomaly_type_counts)


def get_company_profile(ticker: str) -> dict[str, Any] | None:
    normalized = normalize_ticker(ticker)
    cache = memory_cache.get_cache()
    if cache.ready:
        return cache.company_profiles.get(normalized)
    if using_database():
        return db_repository.get_company_profile(ticker)
    if not ticker_exists(normalized):
        return None
    warmup_api_cache()
    return memory_cache.get_cache().company_profiles.get(normalized)


def get_company_anomalies(ticker: str) -> list[dict[str, Any]]:
    """Return anomaly rows for one ticker (records, not DataFrame)."""
    if using_database():
        return db_repository.get_company_anomaly_records(ticker)
    df = get_anomaly_results_minimal()
    normalized = normalize_ticker(ticker)
    mask = df["ticker"] == normalized
    if "is_anomaly" in df.columns:
        mask &= df["is_anomaly"].fillna(False).astype(bool)
    subset = df.loc[mask]
    return dataframe_to_records(subset)


def get_top_anomalies(limit: int = 20) -> pd.DataFrame:
    """Legacy DataFrame return — prefer get_top_anomalies_cached for routes."""
    records = get_top_anomalies_cached(limit)
    return pd.DataFrame(records) if records else pd.DataFrame()


def get_anomaly_summary() -> list[dict[str, Any]]:
    return get_anomaly_summary_cached()


def find_anomaly_record(ticker: str, date_value: str) -> dict[str, Any] | None:
    if using_database():
        return db_repository.find_anomaly_record(ticker, date_value)
    normalized = normalize_ticker(ticker)
    target = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(target):
        return None
    df = get_anomaly_results_minimal()
    matches = df.loc[
        (df["ticker"] == normalized) & (df["date"].dt.date == target.date())
    ]
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
    if using_database():
        return db_repository.query_anomalies(
            ticker=ticker,
            limit=limit,
            only_anomalies=only_anomalies,
            sort_by=sort_by,
            ascending=ascending,
        )

    df = get_anomaly_results_minimal()
    if df.empty:
        return []

    if ticker:
        df = df.loc[df["ticker"] == normalize_ticker(ticker)]
    if df.empty:
        return []
    if only_anomalies and "is_anomaly" in df.columns:
        df = df.loc[df["is_anomaly"].fillna(False).astype(bool)]

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending, na_position="last")
    elif "anomaly_score" in df.columns:
        df = df.sort_values("anomaly_score", ascending=True, na_position="last")

    return dataframe_to_records(df.head(limit))


def get_anomaly_type_counts() -> list[dict[str, int | str]]:
    return get_anomaly_types_cached()
