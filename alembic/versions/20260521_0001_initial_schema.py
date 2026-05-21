"""Initial PostgreSQL schema for Corporate Signal Intelligence.

Revision ID: 20260521_0001
Revises:
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260521_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("cik", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("ticker", name="uq_companies_ticker"),
    )
    op.create_index("ix_companies_ticker", "companies", ["ticker"])

    op.create_table(
        "market_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=True),
        sa.Column("high", sa.Numeric(20, 6), nullable=True),
        sa.Column("low", sa.Numeric(20, 6), nullable=True),
        sa.Column("close", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.Numeric(24, 4), nullable=True),
        sa.Column("daily_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("log_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("price_change_7d", sa.Numeric(16, 8), nullable=True),
        sa.Column("price_change_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("price_change_90d", sa.Numeric(16, 8), nullable=True),
        sa.Column("volatility_7d", sa.Numeric(16, 8), nullable=True),
        sa.Column("volatility_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("volatility_90d", sa.Numeric(16, 8), nullable=True),
        sa.Column("avg_volume_30d", sa.Numeric(24, 4), nullable=True),
        sa.Column("std_volume_30d", sa.Numeric(24, 4), nullable=True),
        sa.Column("volume_change_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("volume_zscore_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("avg_return_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("std_return_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("return_zscore_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("daily_range", sa.Numeric(16, 8), nullable=True),
        sa.Column("open_gap", sa.Numeric(16, 8), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("ticker", "date", name="uq_market_features_ticker_date"),
    )
    op.create_index("ix_market_features_ticker", "market_features", ["ticker"])
    op.create_index("ix_market_features_date", "market_features", ["date"])
    op.create_index("ix_market_features_ticker_date", "market_features", ["ticker", "date"])

    op.create_table(
        "filing_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("filing_count", sa.Integer(), nullable=True),
        sa.Column("form_10k_count", sa.Integer(), nullable=True),
        sa.Column("form_10q_count", sa.Integer(), nullable=True),
        sa.Column("form_8k_count", sa.Integer(), nullable=True),
        sa.Column("filing_count_30d", sa.Numeric(16, 4), nullable=True),
        sa.Column("filing_count_90d", sa.Numeric(16, 4), nullable=True),
        sa.Column("form_8k_count_30d", sa.Numeric(16, 4), nullable=True),
        sa.Column("form_10q_count_180d", sa.Numeric(16, 4), nullable=True),
        sa.Column("form_10k_count_365d", sa.Numeric(16, 4), nullable=True),
        sa.Column("days_since_last_filing", sa.Numeric(16, 4), nullable=True),
        sa.Column("days_since_last_8k", sa.Numeric(16, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("ticker", "date", name="uq_filing_features_ticker_date"),
    )
    op.create_index("ix_filing_features_ticker", "filing_features", ["ticker"])
    op.create_index("ix_filing_features_date", "filing_features", ["date"])
    op.create_index("ix_filing_features_ticker_date", "filing_features", ["ticker", "date"])

    op.create_table(
        "financial_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Numeric(8, 1), nullable=True),
        sa.Column("fiscal_period", sa.Text(), nullable=True),
        sa.Column("revenue", sa.Numeric(24, 4), nullable=True),
        sa.Column("net_income", sa.Numeric(24, 4), nullable=True),
        sa.Column("operating_income", sa.Numeric(24, 4), nullable=True),
        sa.Column("assets", sa.Numeric(24, 4), nullable=True),
        sa.Column("cash_and_equivalents", sa.Numeric(24, 4), nullable=True),
        sa.Column("stockholders_equity", sa.Numeric(24, 4), nullable=True),
        sa.Column("rd_expense", sa.Numeric(24, 4), nullable=True),
        sa.Column("operating_margin", sa.Numeric(16, 8), nullable=True),
        sa.Column("net_margin", sa.Numeric(16, 8), nullable=True),
        sa.Column("cash_to_assets", sa.Numeric(16, 8), nullable=True),
        sa.Column("equity_to_assets", sa.Numeric(16, 8), nullable=True),
        sa.Column("rd_to_revenue", sa.Numeric(16, 8), nullable=True),
        sa.Column("revenue_growth_qoq", sa.Numeric(16, 8), nullable=True),
        sa.Column("revenue_growth_yoy", sa.Numeric(16, 8), nullable=True),
        sa.Column("net_income_growth_qoq", sa.Numeric(16, 8), nullable=True),
        sa.Column("net_income_growth_yoy", sa.Numeric(16, 8), nullable=True),
        sa.Column("assets_growth_qoq", sa.Numeric(16, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("ticker", "reference_date", name="uq_financial_features_ticker_ref"),
    )
    op.create_index("ix_financial_features_ticker", "financial_features", ["ticker"])
    op.create_index("ix_financial_features_reference_date", "financial_features", ["reference_date"])
    op.create_index(
        "ix_financial_features_ticker_ref",
        "financial_features",
        ["ticker", "reference_date"],
    )

    op.create_table(
        "anomaly_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("anomaly_score", sa.Numeric(16, 8), nullable=True),
        sa.Column("anomaly_label", sa.Integer(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("anomaly_type", sa.Text(), nullable=True),
        sa.Column("has_missing_financial_data", sa.Boolean(), nullable=True),
        sa.Column("daily_return", sa.Numeric(16, 8), nullable=True),
        sa.Column("volume_zscore_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("return_zscore_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("volatility_30d", sa.Numeric(16, 8), nullable=True),
        sa.Column("filing_count_30d", sa.Numeric(16, 4), nullable=True),
        sa.Column("form_8k_count_30d", sa.Numeric(16, 4), nullable=True),
        sa.Column("revenue_growth_qoq", sa.Numeric(16, 8), nullable=True),
        sa.Column("net_margin", sa.Numeric(16, 8), nullable=True),
        sa.Column("operating_margin", sa.Numeric(16, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("ticker", "date", name="uq_anomaly_results_ticker_date"),
    )
    op.create_index("ix_anomaly_results_ticker", "anomaly_results", ["ticker"])
    op.create_index("ix_anomaly_results_date", "anomaly_results", ["date"])
    op.create_index("ix_anomaly_results_is_anomaly", "anomaly_results", ["is_anomaly"])
    op.create_index("ix_anomaly_results_anomaly_score", "anomaly_results", ["anomaly_score"])
    op.create_index("ix_anomaly_results_ticker_date", "anomaly_results", ["ticker", "date"])

    op.create_table(
        "sec_filings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("cik", sa.Text(), nullable=True),
        sa.Column("accession_number", sa.Text(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("form_type", sa.Text(), nullable=True),
        sa.Column("primary_document", sa.Text(), nullable=True),
        sa.Column("filing_url", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "ticker",
            "accession_number",
            "form_type",
            name="uq_sec_filings_ticker_accession_form",
        ),
    )
    op.create_index("ix_sec_filings_ticker", "sec_filings", ["ticker"])
    op.create_index("ix_sec_filings_filing_date", "sec_filings", ["filing_date"])
    op.create_index("ix_sec_filings_form_type", "sec_filings", ["form_type"])
    op.create_index("ix_sec_filings_ticker_filing_date", "sec_filings", ["ticker", "filing_date"])

    op.create_table(
        "ai_briefings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("anomaly_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("briefing", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["anomaly_result_id"],
            ["anomaly_results.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("ticker", "date", "model", name="uq_ai_briefings_ticker_date_model"),
    )
    op.create_index("ix_ai_briefings_ticker", "ai_briefings", ["ticker"])
    op.create_index("ix_ai_briefings_date", "ai_briefings", ["date"])
    op.create_index("ix_ai_briefings_ticker_date", "ai_briefings", ["ticker", "date"])


def downgrade() -> None:
    op.drop_table("ai_briefings")
    op.drop_table("sec_filings")
    op.drop_table("anomaly_results")
    op.drop_table("financial_features")
    op.drop_table("filing_features")
    op.drop_table("market_features")
    op.drop_table("companies")
