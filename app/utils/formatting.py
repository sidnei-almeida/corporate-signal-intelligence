"""Formatting helpers for API responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def normalize_date(value: Any) -> str | None:
    """Convert a date-like value to ISO date string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    text = str(value).strip()
    if not text or text.lower() == "nat":
        return None
    return text[:10]


def safe_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    """Convert a value to int when possible."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_bool(value: Any) -> bool | None:
    """Convert a value to bool when possible."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(int(value))
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-serializable records."""
    if df.empty:
        return []
    cleaned = df.replace({np.nan: None, pd.NA: None})
    records = cleaned.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, (np.integer, np.floating)):
                record[key] = value.item()
            elif isinstance(value, (datetime, date, pd.Timestamp)):
                record[key] = normalize_date(value)
            elif isinstance(value, np.bool_):
                record[key] = bool(value)
    return records
