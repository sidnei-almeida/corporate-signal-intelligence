"""Shared helpers for CSV → PostgreSQL loaders."""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime
from typing import Any

import pandas as pd


def clean_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def clean_ticker(value: Any) -> str | None:
    text = clean_str(value)
    return text.upper() if text else None


def clean_bool(value: Any) -> bool | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def clean_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def clean_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def clean_datetime(value: Any) -> datetime | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def row_to_dict(row: pd.Series, mapping: dict[str, str]) -> dict[str, Any]:
    """Map a CSV row to DB column names."""
    payload: dict[str, Any] = {"id": uuid.uuid4()}
    for db_col, csv_col in mapping.items():
        if csv_col not in row.index:
            payload[db_col] = None
            continue
        payload[db_col] = row[csv_col]
    return payload
