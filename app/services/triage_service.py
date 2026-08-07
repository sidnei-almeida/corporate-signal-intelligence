"""Recording and aggregating human reviews of alerts.

Unlike every other service here, this one writes. It requires PostgreSQL: a review is
data the pipeline cannot regenerate, so there is no CSV fallback that would be honest.
"""

from __future__ import annotations

import logging
from statistics import mean, median

from sqlalchemy import func, select

from app.core.data_source import using_database
from app.core.database import session_scope
from app.models.database_models import TriageLog
from app.schemas.triage_schema import (
    TriageEntry,
    TriageEntryRequest,
    TriageStats,
    TriageStatsResponse,
)
from app.utils.formatting import normalize_date
from app.utils.ticker import normalize_ticker

logger = logging.getLogger(__name__)

# Below this many timed reviews the median is noise, and the panel keeps showing the
# stated assumption instead of dressing up a small sample as a measurement.
MINIMUM_REVIEWS_FOR_MEASUREMENT = 20

# The business case's stated assumption: ten to fifteen minutes per issuer per cycle.
ASSUMED_MINUTES_PER_REVIEW = (10.0, 15.0)


class TriageUnavailable(RuntimeError):
    """Raised when no database is configured to persist reviews."""


def _require_database() -> None:
    if not using_database():
        raise TriageUnavailable(
            "Recording a review requires a configured PostgreSQL database. "
            "Set DATABASE_URL and run the migrations."
        )


def record_entry(payload: TriageEntryRequest) -> TriageEntry:
    """Persist one completed review."""
    _require_database()

    row = TriageLog(
        ticker=normalize_ticker(payload.ticker),
        date=payload.date,
        disposition=payload.disposition,
        seconds_spent=payload.seconds_spent,
        reviewer=payload.reviewer,
        notes=payload.notes,
        anomaly_score_at_review=payload.anomaly_score_at_review,
        budget_pct_at_review=payload.budget_pct_at_review,
    )
    with session_scope() as session:
        session.add(row)
        session.flush()
        entry = TriageEntry(
            ticker=row.ticker,
            date=normalize_date(row.date) or str(row.date),
            disposition=payload.disposition,
            seconds_spent=row.seconds_spent,
            reviewer=row.reviewer,
            notes=row.notes,
            anomaly_score_at_review=(
                float(row.anomaly_score_at_review)
                if row.anomaly_score_at_review is not None
                else None
            ),
            budget_pct_at_review=(
                float(row.budget_pct_at_review)
                if row.budget_pct_at_review is not None
                else None
            ),
        )
    logger.info("triage recorded %s %s -> %s", entry.ticker, entry.date, entry.disposition)
    return entry


def get_entries(ticker: str | None = None, limit: int = 100) -> list[TriageEntry]:
    """Recent reviews, newest first."""
    if not using_database():
        return []
    stmt = select(TriageLog).order_by(TriageLog.created_at.desc()).limit(limit)
    if ticker:
        stmt = stmt.where(TriageLog.ticker == normalize_ticker(ticker))
    with session_scope() as session:
        rows = session.execute(stmt).scalars().all()
        return [
            TriageEntry(
                ticker=row.ticker,
                date=normalize_date(row.date) or str(row.date),
                disposition=row.disposition,  # type: ignore[arg-type]
                seconds_spent=row.seconds_spent,
                reviewer=row.reviewer,
                notes=row.notes,
                anomaly_score_at_review=(
                    float(row.anomaly_score_at_review)
                    if row.anomaly_score_at_review is not None
                    else None
                ),
                budget_pct_at_review=(
                    float(row.budget_pct_at_review)
                    if row.budget_pct_at_review is not None
                    else None
                ),
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
            for row in rows
        ]


def get_stats() -> TriageStatsResponse:
    """Aggregate what the log has measured so far."""
    empty = TriageStats(reviews=0, reviews_with_timing=0)
    if not using_database():
        return TriageStatsResponse(
            stats=empty,
            assumed_minutes_per_review=ASSUMED_MINUTES_PER_REVIEW,
            minimum_reviews_for_measurement=MINIMUM_REVIEWS_FOR_MEASUREMENT,
        )

    with session_scope() as session:
        timings = [
            value
            for (value,) in session.execute(
                select(TriageLog.seconds_spent).where(TriageLog.seconds_spent.isnot(None))
            ).all()
            if value is not None
        ]
        counts = dict(
            session.execute(
                select(TriageLog.disposition, func.count()).group_by(TriageLog.disposition)
            ).all()
        )
        total = session.execute(select(func.count()).select_from(TriageLog)).scalar() or 0
        distinct_alerts = (
            session.execute(
                select(func.count(func.distinct(func.concat(TriageLog.ticker, TriageLog.date))))
            ).scalar()
            or 0
        )

    # follow_up is not a verdict, so it is excluded from the denominator rather than
    # counted as a rejection.
    material = int(counts.get("material", 0))
    not_material = int(counts.get("not_material", 0))
    decided = material + not_material

    measured_minutes = None
    if len(timings) >= MINIMUM_REVIEWS_FOR_MEASUREMENT:
        measured_minutes = round(median(timings) / 60, 2)

    stats = TriageStats(
        reviews=int(total),
        reviews_with_timing=len(timings),
        median_seconds=round(median(timings), 1) if timings else None,
        mean_seconds=round(mean(timings), 1) if timings else None,
        by_disposition={key: int(value) for key, value in counts.items()},
        confirmed_rate=round(material / decided, 4) if decided else None,
        distinct_alerts_reviewed=int(distinct_alerts),
        measured_minutes_per_review=measured_minutes,
    )
    return TriageStatsResponse(
        stats=stats,
        assumed_minutes_per_review=ASSUMED_MINUTES_PER_REVIEW,
        minimum_reviews_for_measurement=MINIMUM_REVIEWS_FOR_MEASUREMENT,
    )
