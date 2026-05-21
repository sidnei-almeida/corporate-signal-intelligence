"""Resolve whether the API reads from PostgreSQL or CSV files."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.database import anomaly_results_populated, database_available


@lru_cache
def get_active_data_source() -> str:
    """
    Return the active data source: 'database' or 'csv'.

    Modes (DATA_SOURCE env):
    - auto: use database when configured, reachable, and populated; else csv
    - database: require database; fall back to csv if unavailable
    - csv: always use csv files
    """
    settings = get_settings()
    mode = (settings.DATA_SOURCE or "auto").strip().lower()

    if mode == "csv":
        return "csv"

    if mode in {"database", "db", "postgres", "postgresql"}:
        if database_available() and anomaly_results_populated():
            return "database"
        return "csv"

    # auto
    if database_available() and anomaly_results_populated():
        return "database"
    return "csv"


def using_database() -> bool:
    """Return True when API queries should hit PostgreSQL."""
    return get_active_data_source() == "database"


def clear_data_source_cache() -> None:
    """Clear cached data source resolution (e.g. after CSV load)."""
    get_active_data_source.cache_clear()
