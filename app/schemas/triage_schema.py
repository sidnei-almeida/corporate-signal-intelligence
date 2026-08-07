"""Triage-log schemas.

The triage log is the only data the pipeline cannot produce. It exists so that two
figures the business case currently assumes can eventually be measured: how long a review
takes, and how often an analyst confirms a flagged day was worth the attention.
"""

from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Disposition = Literal["material", "not_material", "follow_up"]

DISPOSITIONS: tuple[Disposition, ...] = ("material", "not_material", "follow_up")


class TriageEntryRequest(BaseModel):
    """One completed review, submitted from the alert queue."""

    ticker: str = Field(min_length=1, max_length=16)
    date: date_type
    disposition: Disposition
    seconds_spent: int | None = Field(default=None, ge=0, le=60 * 60 * 8)
    reviewer: str | None = Field(default=None, max_length=128)
    notes: str | None = None
    anomaly_score_at_review: float | None = None
    budget_pct_at_review: float | None = Field(default=None, ge=0, le=100)


class TriageEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    date: str
    disposition: Disposition
    seconds_spent: int | None = None
    reviewer: str | None = None
    notes: str | None = None
    anomaly_score_at_review: float | None = None
    budget_pct_at_review: float | None = None
    created_at: str | None = None


class TriageStats(BaseModel):
    """What the log has measured so far.

    ``confirmed_rate`` is an analyst judgement and is **not** the model's precision.
    Precision is measured against the prospective criterion — an abnormal move in the
    following session — which no human verdict can substitute for. The two are reported
    separately because they can legitimately disagree.
    """

    reviews: int
    reviews_with_timing: int
    median_seconds: float | None = None
    mean_seconds: float | None = None
    by_disposition: dict[str, int] = Field(default_factory=dict)
    confirmed_rate: float | None = Field(
        default=None,
        description="Share judged material among reviews with a definite verdict",
    )
    distinct_alerts_reviewed: int = 0
    # Null until enough reviews accumulate; the panel falls back to the stated assumption.
    measured_minutes_per_review: float | None = None


class TriageStatsResponse(BaseModel):
    stats: TriageStats
    # The business case's stated assumption, carried so the UI can label which one it is
    # showing rather than silently swapping a measurement for a guess.
    assumed_minutes_per_review: tuple[float, float] = (10.0, 15.0)
    minimum_reviews_for_measurement: int = 20
