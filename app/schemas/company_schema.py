"""Company-related schemas."""

from pydantic import BaseModel, Field


class CompanyListItem(BaseModel):
    ticker: str
    row_count: int | None = None
    first_date: str | None = None
    last_date: str | None = None
    anomaly_count: int | None = None
    anomaly_rate: float | None = None


class CompanyProfile(BaseModel):
    ticker: str
    row_count: int
    first_date: str | None = None
    last_date: str | None = None
    anomaly_count: int
    anomaly_rate: float
    latest_anomaly: dict | None = None
