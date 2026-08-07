"""Re-anchor anomaly_results on the conditional deviation score.

The table was shaped around the first pipeline: an Isolation Forest score plus 30-day
market features and a block of quarterly fundamentals. The benchmark that replaced it
selected a conditional score built from three 21-session standardised deviations, and
measured the fundamental block as not worth its cost. The columns follow.

Two consequences worth stating, because they are not reversible by renaming:

* ``anomaly_score`` changes meaning and direction. It held a negated Isolation Forest
  decision function; it now holds max(|return z|, |volume z|, |range z|), where a larger
  value is a larger deviation.
* The dropped fundamental columns have no equivalent in the new panel.

Existing rows are therefore deleted rather than migrated, and the loader repopulates the
table from ``data/anomaly_detection_results.csv``.

Revision ID: 20260807_0002
Revises: 20260521_0001
Create Date: 2026-08-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0002"
down_revision: Union[str, None] = "20260521_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DROPPED = [
    "has_missing_financial_data",
    "daily_return",
    "volume_zscore_30d",
    "return_zscore_30d",
    "volatility_30d",
    "filing_count_30d",
    "form_8k_count_30d",
    "revenue_growth_qoq",
    "net_margin",
    "operating_margin",
]

ADDED = [
    ("structural_score", sa.Numeric(16, 8)),
    ("is_structural_outlier", sa.Boolean()),
    ("return_zscore_21d", sa.Numeric(16, 8)),
    ("volume_zscore_21d", sa.Numeric(16, 8)),
    ("range_zscore_21d", sa.Numeric(16, 8)),
    ("log_return", sa.Numeric(16, 8)),
    ("realised_volatility_21d", sa.Numeric(16, 8)),
    ("market_return", sa.Numeric(16, 8)),
    ("idiosyncratic_zscore", sa.Numeric(16, 8)),
    ("filed_8k_2d", sa.Numeric(16, 4)),
    ("filed_10q_2d", sa.Numeric(16, 4)),
    ("filed_10k_2d", sa.Numeric(16, 4)),
    ("in_earnings_window", sa.Numeric(16, 4)),
    ("days_since_8k", sa.Numeric(16, 4)),
]


def upgrade() -> None:
    # Briefings reference anomaly rows by id; clearing them first keeps the FK honest
    # and is correct on its own terms, since a memo explains a score that no longer
    # exists in the same units.
    op.execute("DELETE FROM ai_briefings")
    op.execute("DELETE FROM anomaly_results")

    for name, column_type in ADDED:
        op.add_column("anomaly_results", sa.Column(name, column_type, nullable=True))
    for name in DROPPED:
        op.drop_column("anomaly_results", name)


def downgrade() -> None:
    op.execute("DELETE FROM ai_briefings")
    op.execute("DELETE FROM anomaly_results")

    op.add_column(
        "anomaly_results",
        sa.Column("has_missing_financial_data", sa.Boolean(), nullable=True),
    )
    for name in ("daily_return", "volume_zscore_30d", "return_zscore_30d", "volatility_30d"):
        op.add_column("anomaly_results", sa.Column(name, sa.Numeric(16, 8), nullable=True))
    for name in ("filing_count_30d", "form_8k_count_30d"):
        op.add_column("anomaly_results", sa.Column(name, sa.Numeric(16, 4), nullable=True))
    for name in ("revenue_growth_qoq", "net_margin", "operating_margin"):
        op.add_column("anomaly_results", sa.Column(name, sa.Numeric(16, 8), nullable=True))

    for name, _ in ADDED:
        op.drop_column("anomaly_results", name)
