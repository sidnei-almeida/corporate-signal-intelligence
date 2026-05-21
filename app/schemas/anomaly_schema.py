"""Anomaly-related schemas."""

from pydantic import BaseModel, ConfigDict, Field


class AnomalyRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    ticker: str | None = None
    date: str | None = None
    anomaly_score: float | None = None
    is_anomaly: bool | None = None
    anomaly_type: str | None = None
    daily_return: float | None = None
    volume_zscore_30d: float | None = None
    return_zscore_30d: float | None = None
    volatility_30d: float | None = None
    filing_count_30d: float | None = None
    form_8k_count_30d: float | None = None
    revenue_growth_qoq: float | None = None
    net_margin: float | None = None
    operating_margin: float | None = None


class AnomalySummary(BaseModel):
    ticker: str
    rows: int
    anomalies: int
    anomaly_rate: float
    min_score: float | None = None
    avg_score: float | None = None
    max_score: float | None = None


class AnomalyTypeCount(BaseModel):
    anomaly_type: str
    count: int


class AnomalyListResponse(BaseModel):
    count: int
    records: list[dict] = Field(default_factory=list)
