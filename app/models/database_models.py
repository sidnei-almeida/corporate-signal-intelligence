"""PostgreSQL ORM models for Corporate Signal Intelligence."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class TimestampMixin:
    """Created/updated timestamps with timezone awareness."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    cik: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)


class MarketFeature(Base, TimestampMixin):
    __tablename__ = "market_features"
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_market_features_ticker_date"),
        Index("ix_market_features_ticker_date", "ticker", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    volume: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    daily_return: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    log_return: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    price_change_7d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    price_change_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    price_change_90d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    volatility_7d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    volatility_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    volatility_90d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    avg_volume_30d: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    std_volume_30d: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    volume_change_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    volume_zscore_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    avg_return_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    std_return_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    return_zscore_30d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    daily_range: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    open_gap: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FilingFeature(Base, TimestampMixin):
    __tablename__ = "filing_features"
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_filing_features_ticker_date"),
        Index("ix_filing_features_ticker_date", "ticker", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    filing_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    form_10k_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    form_10q_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    form_8k_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_count_30d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    filing_count_90d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    form_8k_count_30d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    form_10q_count_180d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    form_10k_count_365d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    days_since_last_filing: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    days_since_last_8k: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)


class FinancialFeature(Base, TimestampMixin):
    __tablename__ = "financial_features"
    __table_args__ = (
        UniqueConstraint("ticker", "reference_date", name="uq_financial_features_ticker_ref"),
        Index("ix_financial_features_ticker_ref", "ticker", "reference_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_year: Mapped[float | None] = mapped_column(Numeric(8, 1), nullable=True)
    fiscal_period: Mapped[str | None] = mapped_column(String(8), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    net_income: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    operating_income: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    assets: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    cash_and_equivalents: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    stockholders_equity: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    rd_expense: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    operating_margin: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    net_margin: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    cash_to_assets: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    equity_to_assets: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    rd_to_revenue: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    revenue_growth_qoq: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    revenue_growth_yoy: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    net_income_growth_qoq: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    net_income_growth_yoy: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    assets_growth_qoq: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)


class AnomalyResult(Base, TimestampMixin):
    __tablename__ = "anomaly_results"
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_anomaly_results_ticker_date"),
        Index("ix_anomaly_results_ticker_date", "ticker", "date"),
        Index("ix_anomaly_results_is_anomaly", "is_anomaly"),
        Index("ix_anomaly_results_anomaly_score", "anomaly_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Primary score: max(|return z|, |volume z|, |range z|) over a trailing 21-session
    # window. Higher is more deviant, the opposite of the Isolation Forest decision
    # function this column used to hold.
    anomaly_score: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    anomaly_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anomaly_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Secondary score: Isolation Forest over the full feature set. Kept for context on
    # unusual feature combinations; it raises no alerts.
    structural_score: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    is_structural_outlier: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # The three deviations the primary score is built from. The largest is the reason.
    return_zscore_21d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    volume_zscore_21d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    range_zscore_21d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)

    # Market context for the same session.
    log_return: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    realised_volatility_21d: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    market_return: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)
    idiosyncratic_zscore: Mapped[float | None] = mapped_column(Numeric(16, 8), nullable=True)

    # Disclosure context in the two-session reaction window.
    filed_8k_2d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    filed_10q_2d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    filed_10k_2d: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    in_earnings_window: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    days_since_8k: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)

    briefings: Mapped[list["AIBriefing"]] = relationship(back_populates="anomaly_result")


class SECFiling(Base, TimestampMixin):
    __tablename__ = "sec_filings"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "accession_number",
            "form_type",
            name="uq_sec_filings_ticker_accession_form",
        ),
        Index("ix_sec_filings_ticker_filing_date", "ticker", "filing_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    cik: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accession_number: Mapped[str] = mapped_column(String(64), nullable=False)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    form_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    primary_document: Mapped[str | None] = mapped_column(Text, nullable=True)
    filing_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TriageLog(Base, TimestampMixin):
    """One human review of one alert.

    This is the only table holding data the pipeline cannot produce. It exists to turn
    two assumptions into measurements: how long a review actually takes, and how often an
    analyst confirms the day as material.

    That second figure is deliberately *not* the same thing as the model's precision.
    Precision is measured against the prospective criterion (an abnormal move in the next
    session); this column records a human judgement about whether the day was worth the
    attention. The two can legitimately disagree, and keeping them separate is the point.
    """

    __tablename__ = "triage_log"
    __table_args__ = (
        Index("ix_triage_log_ticker_date", "ticker", "date"),
        Index("ix_triage_log_disposition", "disposition"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The alert being reviewed. Not a foreign key: the panel is rebuilt on every pipeline
    # run, and a review should outlive the row that prompted it.
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    reviewer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seconds_spent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # material | not_material | follow_up
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The score at the time of review, so a later re-run of the pipeline cannot silently
    # rewrite what the analyst was actually looking at.
    anomaly_score_at_review: Mapped[float | None] = mapped_column(
        Numeric(16, 8), nullable=True
    )
    budget_pct_at_review: Mapped[float | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )


class AIBriefing(Base, TimestampMixin):
    __tablename__ = "ai_briefings"
    __table_args__ = (
        UniqueConstraint("ticker", "date", "model", name="uq_ai_briefings_ticker_date_model"),
        Index("ix_ai_briefings_ticker_date", "ticker", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    anomaly_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("anomaly_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    briefing: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    anomaly_result: Mapped[AnomalyResult | None] = relationship(back_populates="briefings")
