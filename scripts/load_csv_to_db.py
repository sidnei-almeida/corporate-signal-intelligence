#!/usr/bin/env python3
"""
Load project CSV files into PostgreSQL (Neon).

Usage:
  export DATABASE_URL=postgresql+psycopg://...
  alembic upgrade head
  python scripts/load_csv_to_db.py --truncate
  python scripts/load_csv_to_db.py --only anomaly_results
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.data_source import clear_data_source_cache
from app.core.database import engine, session_scope
from app.models.database_models import (
    AnomalyResult,
    Company,
    FilingFeature,
    FinancialFeature,
    MarketFeature,
    SECFiling,
)
from scripts.db_load_utils import (
    clean_bool,
    clean_date,
    clean_datetime,
    clean_float,
    clean_int,
    clean_str,
    clean_ticker,
)

BATCH_SIZE = 1000

TABLE_TRUNCATE_ORDER = [
    "ai_briefings",
    "anomaly_results",
    "sec_filings",
    "financial_features",
    "filing_features",
    "market_features",
    "companies",
]


def _read_csv(name: str) -> pd.DataFrame:
    path = get_settings().data_path / name
    if not path.is_file():
        print(f"  skip missing: {path.name}")
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df


def truncate_tables() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    with engine.begin() as conn:
        for table in TABLE_TRUNCATE_ORDER:
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    print("Truncated tables:", ", ".join(TABLE_TRUNCATE_ORDER))


def _bulk_insert(session, model, rows: list[dict], conflict_cols: list[str]) -> int:
    if not rows:
        return 0
    inserted = 0
    table = model.__table__
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        stmt = insert(table).values(chunk)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in table.columns
            if c.name not in conflict_cols and c.name not in {"id", "created_at"}
        }
        if update_cols:
            stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
        session.execute(stmt)
        inserted += len(chunk)
    return inserted


def load_companies(session) -> int:
    print("Loading companies...")
    df = _read_csv("clean_company_metadata.csv")
    rows: list[dict] = []
    seen: set[str] = set()
    if not df.empty:
        for _, row in df.iterrows():
            ticker = clean_ticker(row.get("ticker"))
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "ticker": ticker,
                    "company_name": clean_str(row.get("company_name")),
                    "cik": clean_str(row.get("cik")),
                    "source": clean_str(row.get("source")),
                }
            )
    anomaly_df = _read_csv("anomaly_detection_results.csv")
    if not anomaly_df.empty:
        for ticker in anomaly_df["ticker"].dropna().unique():
            t = clean_ticker(ticker)
            if t and t not in seen:
                seen.add(t)
                rows.append(
                    {
                        "id": uuid.uuid4(),
                        "ticker": t,
                        "company_name": None,
                        "cik": None,
                        "source": "anomaly_detection_results",
                    }
                )
    count = _bulk_insert(session, Company, rows, ["ticker"])
    print(f"  companies: {count}")
    return count


def load_market_features(session) -> int:
    print("Loading market_features...")
    df = _read_csv("market_features.csv")
    rows = []
    for _, row in df.iterrows():
        ticker = clean_ticker(row.get("ticker"))
        dt = clean_date(row.get("date"))
        if not ticker or not dt:
            continue
        rows.append(
            {
                "id": uuid.uuid4(),
                "ticker": ticker,
                "date": dt,
                "open": clean_float(row.get("open")),
                "high": clean_float(row.get("high")),
                "low": clean_float(row.get("low")),
                "close": clean_float(row.get("close")),
                "volume": clean_float(row.get("volume")),
                "daily_return": clean_float(row.get("daily_return")),
                "log_return": clean_float(row.get("log_return")),
                "price_change_7d": clean_float(row.get("price_change_7d")),
                "price_change_30d": clean_float(row.get("price_change_30d")),
                "price_change_90d": clean_float(row.get("price_change_90d")),
                "volatility_7d": clean_float(row.get("volatility_7d")),
                "volatility_30d": clean_float(row.get("volatility_30d")),
                "volatility_90d": clean_float(row.get("volatility_90d")),
                "avg_volume_30d": clean_float(row.get("avg_volume_30d")),
                "std_volume_30d": clean_float(row.get("std_volume_30d")),
                "volume_change_30d": clean_float(row.get("volume_change_30d")),
                "volume_zscore_30d": clean_float(row.get("volume_zscore_30d")),
                "avg_return_30d": clean_float(row.get("avg_return_30d")),
                "std_return_30d": clean_float(row.get("std_return_30d")),
                "return_zscore_30d": clean_float(row.get("return_zscore_30d")),
                "daily_range": clean_float(row.get("daily_range")),
                "open_gap": clean_float(row.get("open_gap")),
                "source": clean_str(row.get("source")),
                "collected_at": clean_datetime(row.get("collected_at")),
            }
        )
    count = _bulk_insert(session, MarketFeature, rows, ["ticker", "date"])
    print(f"  market_features: {count}")
    return count


def load_filing_features(session) -> int:
    print("Loading filing_features...")
    df = _read_csv("filing_features.csv")
    rows = []
    for _, row in df.iterrows():
        ticker = clean_ticker(row.get("ticker"))
        dt = clean_date(row.get("date"))
        if not ticker or not dt:
            continue
        rows.append(
            {
                "id": uuid.uuid4(),
                "ticker": ticker,
                "date": dt,
                "filing_count": clean_int(row.get("filing_count")),
                "form_10k_count": clean_int(row.get("form_10k_count")),
                "form_10q_count": clean_int(row.get("form_10q_count")),
                "form_8k_count": clean_int(row.get("form_8k_count")),
                "filing_count_30d": clean_float(row.get("filing_count_30d")),
                "filing_count_90d": clean_float(row.get("filing_count_90d")),
                "form_8k_count_30d": clean_float(row.get("form_8k_count_30d")),
                "form_10q_count_180d": clean_float(row.get("form_10q_count_180d")),
                "form_10k_count_365d": clean_float(row.get("form_10k_count_365d")),
                "days_since_last_filing": clean_float(row.get("days_since_last_filing")),
                "days_since_last_8k": clean_float(row.get("days_since_last_8k")),
            }
        )
    count = _bulk_insert(session, FilingFeature, rows, ["ticker", "date"])
    print(f"  filing_features: {count}")
    return count


def load_financial_features(session) -> int:
    print("Loading financial_features...")
    df = _read_csv("financial_features_selected.csv")
    rows = []
    for _, row in df.iterrows():
        ticker = clean_ticker(row.get("ticker"))
        ref = clean_date(row.get("reference_date"))
        if not ticker or not ref:
            continue
        rows.append(
            {
                "id": uuid.uuid4(),
                "ticker": ticker,
                "reference_date": ref,
                "fiscal_year": clean_float(row.get("fiscal_year")),
                "fiscal_period": clean_str(row.get("fiscal_period")),
                "revenue": clean_float(row.get("revenue")),
                "net_income": clean_float(row.get("net_income")),
                "operating_income": clean_float(row.get("operating_income")),
                "assets": clean_float(row.get("assets")),
                "cash_and_equivalents": clean_float(row.get("cash_and_equivalents")),
                "stockholders_equity": clean_float(row.get("stockholders_equity")),
                "rd_expense": clean_float(row.get("rd_expense")),
                "operating_margin": clean_float(row.get("operating_margin")),
                "net_margin": clean_float(row.get("net_margin")),
                "cash_to_assets": clean_float(row.get("cash_to_assets")),
                "equity_to_assets": clean_float(row.get("equity_to_assets")),
                "rd_to_revenue": clean_float(row.get("rd_to_revenue")),
                "revenue_growth_qoq": clean_float(row.get("revenue_growth_qoq")),
                "revenue_growth_yoy": clean_float(row.get("revenue_growth_yoy")),
                "net_income_growth_qoq": clean_float(row.get("net_income_growth_qoq")),
                "net_income_growth_yoy": clean_float(row.get("net_income_growth_yoy")),
                "assets_growth_qoq": clean_float(row.get("assets_growth_qoq")),
            }
        )
    count = _bulk_insert(session, FinancialFeature, rows, ["ticker", "reference_date"])
    print(f"  financial_features: {count}")
    return count


def load_sec_filings(session) -> int:
    print("Loading sec_filings...")
    df = _read_csv("clean_sec_filings.csv")
    rows = []
    for _, row in df.iterrows():
        ticker = clean_ticker(row.get("ticker"))
        accession = clean_str(row.get("accession_number"))
        form_type = clean_str(row.get("form_type"))
        if not ticker or not accession:
            continue
        rows.append(
            {
                "id": uuid.uuid4(),
                "ticker": ticker,
                "cik": clean_str(row.get("cik")),
                "accession_number": accession,
                "filing_date": clean_date(row.get("filing_date")),
                "report_date": clean_date(row.get("report_date")),
                "form_type": form_type,
                "primary_document": clean_str(row.get("primary_document")),
                "filing_url": clean_str(row.get("filing_url")),
                "source": clean_str(row.get("source")),
                "collected_at": clean_datetime(row.get("collected_at")),
            }
        )
    count = _bulk_insert(session, SECFiling, rows, ["ticker", "accession_number", "form_type"])
    print(f"  sec_filings: {count}")
    return count


def load_anomaly_results(session) -> int:
    print("Loading anomaly_results...")
    df = _read_csv("anomaly_detection_results.csv")
    rows = []
    for _, row in df.iterrows():
        ticker = clean_ticker(row.get("ticker"))
        dt = clean_date(row.get("date"))
        if not ticker or not dt:
            continue
        is_anomaly = clean_bool(row.get("is_anomaly"))
        if is_anomaly is None and "anomaly_label" in row.index:
            label = clean_int(row.get("anomaly_label"))
            is_anomaly = label == -1 or label == 1 if label is not None else False
        rows.append(
            {
                "id": uuid.uuid4(),
                "ticker": ticker,
                "date": dt,
                "anomaly_score": clean_float(row.get("anomaly_score")),
                "anomaly_label": clean_int(row.get("anomaly_label")),
                "is_anomaly": bool(is_anomaly) if is_anomaly is not None else False,
                "anomaly_type": clean_str(row.get("anomaly_type")),
                "has_missing_financial_data": clean_bool(row.get("has_missing_financial_data")),
                "daily_return": clean_float(row.get("daily_return")),
                "volume_zscore_30d": clean_float(row.get("volume_zscore_30d")),
                "return_zscore_30d": clean_float(row.get("return_zscore_30d")),
                "volatility_30d": clean_float(row.get("volatility_30d")),
                "filing_count_30d": clean_float(row.get("filing_count_30d")),
                "form_8k_count_30d": clean_float(row.get("form_8k_count_30d")),
                "revenue_growth_qoq": clean_float(row.get("revenue_growth_qoq")),
                "net_margin": clean_float(row.get("net_margin")),
                "operating_margin": clean_float(row.get("operating_margin")),
            }
        )
    count = _bulk_insert(session, AnomalyResult, rows, ["ticker", "date"])
    print(f"  anomaly_results: {count}")
    return count


LOADERS = {
    "companies": load_companies,
    "market_features": load_market_features,
    "filing_features": load_filing_features,
    "financial_features": load_financial_features,
    "sec_filings": load_sec_filings,
    "anomaly_results": load_anomaly_results,
}

LOAD_ORDER = [
    "companies",
    "market_features",
    "filing_features",
    "financial_features",
    "sec_filings",
    "anomaly_results",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Load CSV data into PostgreSQL.")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate all tables before loading.",
    )
    parser.add_argument(
        "--only",
        choices=list(LOADERS.keys()),
        nargs="*",
        help="Load only specific tables.",
    )
    args = parser.parse_args()

    if engine is None:
        print("ERROR: DATABASE_URL is not set.")
        sys.exit(1)

    if args.truncate:
        truncate_tables()

    targets = args.only or LOAD_ORDER
    with session_scope() as session:
        for name in LOAD_ORDER:
            if name in targets:
                LOADERS[name](session)

    clear_data_source_cache()
    print("Done. Active data source will prefer database when DATA_SOURCE=auto.")


if __name__ == "__main__":
    main()
