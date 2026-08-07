"""Anomaly-related schemas."""

from pydantic import BaseModel, ConfigDict, Field

# The conditional score runs the opposite way to the Isolation Forest decision function
# it replaced: a larger value is a larger deviation. Every ordering in the serving layer
# reads this rather than repeating a bare `ascending=True`.
SCORE_SORT_ASCENDING = False


class AnomalyRecord(BaseModel):
    """One issuer-day as the serving layer exposes it.

    The fields mirror the conditional score the pipeline actually ships: the day's score
    is the largest of the three standardised deviations, so those three are what explain
    an alert. Disclosure activity in the two-session reaction window travels alongside
    them as context.
    """

    model_config = ConfigDict(extra="allow")

    ticker: str | None = None
    date: str | None = None

    # Primary (validated) score and its flag.
    anomaly_score: float | None = None
    is_anomaly: bool | None = None
    anomaly_type: str | None = None
    anomaly_label: int | None = None
    # Tightest alert budget the day would still survive: critical / high / moderate /
    # watch. Attached by the service layer, not stored.
    severity: str | None = None

    # Secondary score: unusual feature combinations, context only, raises no alerts.
    structural_score: float | None = None
    is_structural_outlier: bool | None = None

    # The three conditional deviations. The largest one is the score.
    return_zscore_21d: float | None = None
    volume_zscore_21d: float | None = None
    range_zscore_21d: float | None = None

    # Market context for the same day.
    log_return: float | None = None
    realised_volatility_21d: float | None = None
    market_return: float | None = None
    idiosyncratic_zscore: float | None = None

    # Disclosure context in the two-session reaction window.
    filed_8k_2d: float | None = None
    filed_10q_2d: float | None = None
    filed_10k_2d: float | None = None
    in_earnings_window: float | None = None
    days_since_8k: float | None = None


# Fields the service layer computes per request. They are part of the response but not of
# the stored panel, so neither the CSV reader nor the SQL query may ask for them.
COMPUTED_ANOMALY_FIELDS = frozenset({"severity"})

# The columns both backends select. Deriving them from the model above means the CSV
# reader, the SQL query and the response contract cannot drift apart.
SERVED_ANOMALY_COLUMNS = [
    name for name in AnomalyRecord.model_fields if name not in COMPUTED_ANOMALY_FIELDS
]


class AnomalySummary(BaseModel):
    """Per-issuer descriptive counts.

    There is deliberately no "risk" framing here. The score is self-normalising against
    each issuer's own trailing volatility, so under a fixed budget every issuer converges
    on roughly the same alert rate: ranking issuers by that rate measures nothing.
    """

    ticker: str
    rows: int
    anomalies: int
    anomaly_rate: float
    avg_score: float | None = None
    max_score: float | None = None
    latest_alert_date: str | None = None


class AnomalyTypeCount(BaseModel):
    anomaly_type: str
    count: int
    share_pct: float | None = None


class AlertBudget(BaseModel):
    """The operating parameter of the tool: how much analyst attention is on offer."""

    budget_pct: float = Field(description="Share of issuer-days that may raise an alert")
    threshold: float = Field(description="Conditional-score cutoff implied by the budget")
    alerts: int
    rows: int
    alerts_per_year: float | None = None


class AnomalyListResponse(BaseModel):
    count: int
    budget: AlertBudget | None = None
    records: list[dict] = Field(default_factory=list)
