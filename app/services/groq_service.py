"""Groq-powered executive briefing generation."""

from __future__ import annotations

import json
from typing import Any

from groq import Groq

from app.core.config import get_settings


SYSTEM_PROMPT = """You are a senior corporate intelligence analyst preparing an executive briefing.

Analyze the provided anomaly record and company context. Structure your response to cover:
1. What happened
2. Why it matters
3. Which signals contributed
4. Risk interpretation
5. Suggested monitoring actions

Write in a professional, concise, corporate, and business-oriented tone.
Use plain language suitable for executives and risk teams.
Do not invent facts not supported by the provided data.

This is not financial advice. The briefing is for analytical and monitoring purposes only.
Do not provide investment recommendations, buy/sell guidance, or trading advice.
"""


def _format_record(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, default=str)


def generate_executive_briefing(
    anomaly_record: dict[str, Any],
    company_context: dict[str, Any] | None = None,
) -> str:
    """Generate an executive briefing for an anomaly record using Groq."""
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=settings.GROQ_API_KEY)
    context_block = ""
    if company_context:
        context_block = f"\n\nCompany context:\n{_format_record(company_context)}"

    user_prompt = (
        "Generate an executive briefing for the following corporate signal anomaly.\n\n"
        f"Anomaly record:\n{_format_record(anomaly_record)}"
        f"{context_block}"
    )

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        temperature=0.3,
        max_tokens=700,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty briefing.")
    return content.strip()
