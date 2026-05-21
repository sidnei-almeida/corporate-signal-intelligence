"""Executive briefing schemas."""

from pydantic import BaseModel, ConfigDict, Field


class BriefingRequest(BaseModel):
    ticker: str = Field(..., min_length=1, description="Company ticker symbol.")
    date: str = Field(..., min_length=8, description="Anomaly date (YYYY-MM-DD).")


class BriefingFromRecordRequest(BaseModel):
    record: dict = Field(..., description="Anomaly record payload.")
    company_context: dict | None = Field(
        default=None,
        description="Optional additional company context.",
    )


class BriefingResponse(BaseModel):
    briefing: str
    model_used: str
    ticker: str | None = None
    date: str | None = None
    source_record: dict | None = None
