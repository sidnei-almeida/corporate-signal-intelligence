"""Ticker normalization and validation helpers."""

from __future__ import annotations

# Path segments used by static anomaly routes — must not be treated as tickers.
RESERVED_PATH_SEGMENTS = frozenset({"TOP", "SUMMARY", "TYPES", "QUEUE", "BUDGET"})


def normalize_ticker(ticker: str) -> str:
    """Normalize a ticker symbol for lookups."""
    return ticker.strip().upper()


def is_reserved_path_segment(segment: str) -> bool:
    """Return True when a URL segment matches a static anomalies route name."""
    return normalize_ticker(segment) in RESERVED_PATH_SEGMENTS


def is_plausible_ticker(ticker: str) -> bool:
    """Return True when the ticker looks like a valid symbol."""
    normalized = normalize_ticker(ticker)
    if not normalized or is_reserved_path_segment(normalized):
        return False
    return normalized.replace(".", "").replace("-", "").isalnum()
