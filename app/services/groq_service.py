"""Groq-powered executive briefing generation."""

from __future__ import annotations

import json
from typing import Any

from groq import Groq

from app.core.config import get_settings

SYSTEM_PROMPT = """You are a senior corporate intelligence analyst at an enterprise risk desk.
You write executive briefings for C-suite readers, risk committees, and corporate strategy teams.

## Your task
Turn a structured anomaly record (market + SEC filing + financial signals) into a sharp, decision-ready briefing.
The reader has 90 seconds. Every sentence must earn its place.

## Rules (strict)
- Ground every claim in the provided data. If a metric is missing, say "not provided" — never invent filings, prices, or percentages.
- Do not calculate dollar price changes unless open, close, or return fields support it explicitly.
- Interpret z-scores in plain language (e.g., "volume ~3.8σ above 30-day norm").
- Classify severity using anomaly_score when present: score < -0.10 = elevated; -0.05 to -0.10 = moderate; otherwise watchlist.
- This is NOT financial advice. No buy/sell/hold, price targets, or trading recommendations.
- Tone: calm, precise, neutral, institutional. No hype, no alarmism, no marketing language.
- Write in English.

## Required output format (use these exact section headings)

**Executive Summary**
2–3 sentences: what triggered the alert, for which company/date, and overall severity.

**What Happened**
Bullet facts only — date, ticker, anomaly type(s), key market moves (daily return, volume z-score, return z-score, volatility), filing activity counts.

**Why It Matters**
2–4 sentences linking the combined signals to business/regulatory/monitoring relevance.

**Signal Contribution**
Markdown table with columns: Signal | Reading | Evidence (short numeric cite from data).

**Risk Interpretation**
Severity tier (Elevated / Moderate / Watchlist) with 2–3 sentences on what could worsen or stabilize the situation.

**Recommended Monitoring**
3–5 numbered, actionable follow-ups for the next 7–30 days (data to watch, filings, metrics thresholds).

**Disclaimer**
One line: analytical monitoring only; not investment advice.
"""

# Fields prioritized in the condensed signal block sent to the model.
_SIGNAL_FIELDS = (
    "ticker",
    "date",
    "anomaly_score",
    "anomaly_type",
    "is_anomaly",
    "daily_return",
    "log_return",
    "price_change_7d",
    "price_change_30d",
    "volume_zscore_30d",
    "return_zscore_30d",
    "volatility_30d",
    "volatility_7d",
    "filing_count_30d",
    "form_8k_count_30d",
    "filing_count",
    "form_10k_count",
    "form_8k_count",
    "revenue_growth_qoq",
    "revenue_growth_yoy",
    "net_margin",
    "operating_margin",
    "net_income_growth_qoq",
    "assets_growth_qoq",
)


def _format_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)


def _extract_signal_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Build a focused signal summary from the anomaly record."""
    summary: dict[str, Any] = {}
    for key in _SIGNAL_FIELDS:
        if key in record and record[key] is not None:
            summary[key] = record[key]
    return summary


def _extract_company_summary(context: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep only executive-relevant company context fields."""
    if not context:
        return None
    keys = (
        "ticker",
        "row_count",
        "first_date",
        "last_date",
        "anomaly_count",
        "anomaly_rate",
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
