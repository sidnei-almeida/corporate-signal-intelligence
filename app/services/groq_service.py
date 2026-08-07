"""Groq-powered executive briefing generation."""

from __future__ import annotations

import json
from typing import Any

from groq import Groq

from app.core.config import get_settings
from app.services import data_service

SYSTEM_PROMPT = """You are a senior analyst on a corporate monitoring desk.
You write short briefings that explain why a specific trading day was put in front of a
human for review.

## What the alert is, and is not

The system ranks issuer-days by a conditional deviation score: the largest of three
standardised deviations measured against the issuer's own trailing 21-session behaviour —
log return, log volume, and intraday range. A day is flagged when that score exceeds the
cutoff set by the alert budget.

Two consequences you must respect:

1. **The score is its own explanation.** Whichever of `return_zscore_21d`,
   `volume_zscore_21d` and `range_zscore_21d` has the largest absolute value *is*
   `anomaly_score`, and is the reason the day was flagged. Identify it and lead with it.
2. **This is a triage instrument, not a forecast.** It prioritises attention. It does not
   predict direction, and the underlying study found direction is not predictable from
   disclosures. Never imply the alert says which way the price will go.

`structural_score` is a secondary Isolation Forest reading over the wider feature set. It
was not validated as an early-warning signal and raises no alerts. Mention it only as
corroborating context, never as the reason.

## Rules (strict)
- Ground every claim in the provided data. If a metric is missing, say "not provided" —
  never invent filings, prices, or percentages.
- Interpret z-scores in plain language (e.g., "volume ~3.8σ above its own 21-day norm").
  Always say "against its own recent behaviour", because the scale is issuer-relative.
- Severity comes from `severity_tier` in the payload. Do not invent your own cutoffs.
- Disclosure context: `filed_8k_2d`, `filed_10q_2d` and `filed_10k_2d` mean a filing of
  that type landed within the two-session reaction window. `in_earnings_window` marks a
  scheduled reporting window. Treat these as co-occurrence, not causation.
- If `market_return` is large in the same direction, say so: the move may be market-wide
  rather than issuer-specific. `idiosyncratic_zscore` is the issuer-specific residual.
- This is NOT financial advice. No buy/sell/hold, price targets, or trading
  recommendations.
- Tone: calm, precise, neutral. No hype, no alarmism, no marketing language.
- Write in English.

## Required output format (use these exact section headings)

**Executive Summary**
2–3 sentences: which issuer and date, which deviation triggered the alert, how large it
was against that issuer's own recent norm, and the severity tier.

**What Triggered This**
Bullet facts only — the dominant deviation and its value, the other two for comparison,
the day's log return, and any filing inside the two-session window.

**Reading the Signal**
Markdown table with columns: Deviation | Value (σ) | Dominant? | Reading.
One row each for return, volume and range.

**Context**
2–4 sentences: was the move issuer-specific or market-wide, was it near a disclosure or
an earnings window, and what the secondary structural score adds, if anything.

**What to Check**
3–5 numbered, concrete follow-ups: the specific filing to open, the metric to compare,
the window to watch. Each must be something a person can actually do.

**Limits of This Alert**
2–3 sentences: what this score cannot tell the reader. Be specific — the score is
self-normalising, so it is robust to changing volatility regimes but blind to the regime
itself; and a flagged day is a candidate for review, not a finding.

**Disclaimer**
One line: attention prioritisation for analytical monitoring only; not investment advice,
not a legal or accounting opinion on any filing.
"""

# Fields prioritized in the condensed signal block sent to the model. These mirror what
# the conditional score is actually built from; the quarterly fundamental block is absent
# because the benchmark measured it as not carrying its cost.
_SIGNAL_FIELDS = (
    "ticker",
    "date",
    "anomaly_score",
    "anomaly_type",
    "is_anomaly",
    "return_zscore_21d",
    "volume_zscore_21d",
    "range_zscore_21d",
    "log_return",
    "realised_volatility_21d",
    "market_return",
    "idiosyncratic_zscore",
    "filed_8k_2d",
    "filed_10q_2d",
    "filed_10k_2d",
    "in_earnings_window",
    "days_since_8k",
    "structural_score",
    "is_structural_outlier",
)

# The three deviations the score is the maximum of.
_DEVIATIONS = {
    "return_zscore_21d": "price move",
    "volume_zscore_21d": "volume spike",
    "range_zscore_21d": "range expansion",
}


def _format_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)


def _dominant_deviation(record: dict[str, Any]) -> dict[str, Any] | None:
    """Identify which of the three deviations the score came from."""
    readings = {
        field: abs(float(record[field]))
        for field in _DEVIATIONS
        if record.get(field) is not None
    }
    if not readings:
        return None
    field = max(readings, key=readings.get)
    return {
        "field": field,
        "label": _DEVIATIONS[field],
        "value": record[field],
        "absolute": round(readings[field], 4),
    }


def _extract_signal_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Build a focused signal summary from the anomaly record."""
    summary: dict[str, Any] = {}
    for key in _SIGNAL_FIELDS:
        if key in record and record[key] is not None:
            summary[key] = record[key]

    # Resolve the two things the model must not guess at: which deviation drove the
    # score, and how severe the day is on the desk's own scale.
    dominant = _dominant_deviation(record)
    if dominant:
        summary["dominant_deviation"] = dominant
    score = record.get("anomaly_score")
    if score is not None:
        summary["severity_tier"] = data_service.severity_tier(float(score))
        summary["severity_scale"] = [
            {"tier": tier, "score_at_or_above": round(threshold, 4)}
            for tier, threshold in data_service.severity_thresholds()
        ]
    return summary


def _extract_company_summary(context: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep only executive-relevant company context fields."""
    if not context:
        return None
    # anomaly_rate is deliberately withheld. The score is self-normalising, so under a
    # fixed budget every issuer lands near the same rate: handing it to the model invites
    # a comparison between issuers that the number cannot support.
    keys = (
        "ticker",
        "row_count",
        "first_date",
        "last_date",
        "anomaly_count",
    )
    return {k: context[k] for k in keys if k in context}


def _build_user_prompt(
    anomaly_record: dict[str, Any],
    company_context: dict[str, Any] | None = None,
) -> str:
    """Assemble a structured user prompt with focused signal context."""
    signal_summary = _extract_signal_summary(anomaly_record)
    company_summary = _extract_company_summary(company_context)

    parts = [
        "Produce the executive briefing for the anomaly below.",
        "",
        "## Primary signal summary (use these metrics first)",
        _format_json(signal_summary),
    ]

    if company_summary:
        parts.extend(
            [
                "",
                "## Company historical context",
                _format_json(company_summary),
            ]
        )

    parts.extend(
        [
            "",
            "## Full anomaly record (reference only — do not repeat every field)",
            _format_json(anomaly_record),
        ]
    )

    return "\n".join(parts)


def generate_executive_briefing(
    anomaly_record: dict[str, Any],
    company_context: dict[str, Any] | None = None,
) -> str:
    """Generate an executive briefing for an anomaly record using Groq."""
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=settings.GROQ_API_KEY)
    user_prompt = _build_user_prompt(anomaly_record, company_context)

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.2,
        max_tokens=1100,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty briefing.")
    return content.strip()
