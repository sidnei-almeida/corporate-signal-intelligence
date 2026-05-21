"""Model inference schemas."""

from pydantic import BaseModel, Field


class ModelPredictionRequest(BaseModel):
    features: dict[str, float | int | None] = Field(
        ...,
        description="Feature name to numeric value mapping for inference.",
    )


class ModelPredictionResponse(BaseModel):
    anomaly_label: str
    is_anomaly: bool
    anomaly_score: float | None = None
    model_name: str


class ModelInfoResponse(BaseModel):
    model_path: str
    model_exists: bool
    model_type: str | None = None
    expected_feature_count: int | None = None
    feature_names: list[str] = Field(default_factory=list)
    artifact_status: str
