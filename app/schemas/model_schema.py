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


class ScoreInfo(BaseModel):
    """One of the two scores the system computes."""

    name: str
    definition: str | None = None
    role: str | None = None
    requires_fitting: bool | None = None
    threshold: float | None = None
    roc_auc: float | None = None
    precision_at_budget: float | None = None
    precision_lift_over_base_rate: float | None = None
    # Restricted to the quietest 80% of sessions, where triage is hardest.
    precision_at_budget_calm_market: float | None = None
    precision_lift_calm_market: float | None = None


class ModelInfoResponse(BaseModel):
    """What the system scores with.

    The joblib artifact described by ``model_path`` backs the *secondary* score only.
    The score that raises alerts is a parameter-free rule over three standardised
    deviations: it has nothing to load, which is why ``model_exists`` being false does
    not mean the tool is down.
    """

    model_path: str
    model_exists: bool
    model_type: str | None = None
    expected_feature_count: int | None = None
    feature_names: list[str] = Field(default_factory=list)
    artifact_status: str
    primary_score: ScoreInfo | None = None
    secondary_score: ScoreInfo | None = None
