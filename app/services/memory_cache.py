"""Lightweight in-memory API response caches (built once at startup)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default number of top anomalies precomputed for /anomalies/top and /briefings/sample
DEFAULT_TOP_CACHE_SIZE = 100


@dataclass
class ApiMemoryCache:
    """Precomputed summaries to avoid repeated pandas work per request."""

    ready: bool = False
    tickers: frozenset[str] = field(default_factory=frozenset)
    companies_list: list[dict[str, Any]] = field(default_factory=list)
    anomaly_summary: list[dict[str, Any]] = field(default_factory=list)
    top_anomalies: list[dict[str, Any]] = field(default_factory=list)
    anomaly_type_counts: list[dict[str, int | str]] = field(default_factory=list)
    company_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)


_cache = ApiMemoryCache()


def get_cache() -> ApiMemoryCache:
    return _cache


def is_cache_ready() -> bool:
    return _cache.ready


def clear_cache() -> None:
    global _cache
    _cache = ApiMemoryCache()


def set_cache(
    *,
    tickers: frozenset[str],
    companies_list: list[dict[str, Any]],
    anomaly_summary: list[dict[str, Any]],
    top_anomalies: list[dict[str, Any]],
    anomaly_type_counts: list[dict[str, int | str]],
    company_profiles: dict[str, dict[str, Any]],
) -> None:
    global _cache
    _cache = ApiMemoryCache(
        ready=True,
        tickers=tickers,
        companies_list=companies_list,
        anomaly_summary=anomaly_summary,
        top_anomalies=top_anomalies,
        anomaly_type_counts=anomaly_type_counts,
        company_profiles=company_profiles,
    )
    logger.info(
        "API cache ready: %s tickers, %s top anomalies, %s type labels",
        len(tickers),
        len(top_anomalies),
        len(anomaly_type_counts),
    )
