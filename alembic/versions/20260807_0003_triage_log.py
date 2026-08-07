"""Add the triage log.

The business case argues financial viability from an assumption: roughly ten to fifteen
minutes of analyst time per issuer per cycle. This table is what turns that assumption
into a measurement, by recording what actually happened when a human worked an alert.

It also records the analyst's verdict, which is a different quantity from the model's
precision. Precision is measured against the prospective criterion — an abnormal move in
the following session. The verdict here is a judgement about whether the day deserved the
attention. Keeping the two apart is deliberate.

Revision ID: 20260807_0003
Revises: 20260807_0002
Create Date: 2026-08-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260807_0003"
down_revision: Union[str, None] = "20260807_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "triage_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        # Not a foreign key to anomaly_results on purpose: the panel is rebuilt on every
        # pipeline run, and a recorded review must outlive the row that prompted it.
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("reviewer", sa.String(128), nullable=True),
        sa.Column("seconds_spent", sa.Integer(), nullable=True),
        sa.Column("disposition", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("anomaly_score_at_review", sa.Numeric(16, 8), nullable=True),
        sa.Column("budget_pct_at_review", sa.Numeric(8, 4), nullable=True),
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
        sa.CheckConstraint(
            "disposition IN ('material', 'not_material', 'follow_up')",
            name="ck_triage_log_disposition",
        ),
        sa.CheckConstraint(
            "seconds_spent IS NULL OR seconds_spent >= 0",
            name="ck_triage_log_seconds_non_negative",
        ),
    )
    op.create_index("ix_triage_log_ticker", "triage_log", ["ticker"])
    op.create_index("ix_triage_log_date", "triage_log", ["date"])
    op.create_index("ix_triage_log_ticker_date", "triage_log", ["ticker", "date"])
    op.create_index("ix_triage_log_disposition", "triage_log", ["disposition"])


def downgrade() -> None:
    op.drop_index("ix_triage_log_disposition", table_name="triage_log")
    op.drop_index("ix_triage_log_ticker_date", table_name="triage_log")
    op.drop_index("ix_triage_log_date", table_name="triage_log")
    op.drop_index("ix_triage_log_ticker", table_name="triage_log")
    op.drop_table("triage_log")
