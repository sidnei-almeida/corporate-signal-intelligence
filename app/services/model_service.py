"""Model loading and prediction service."""

from __future__ import annotations

from typing import Any

from app.ml import inference, model_loader
from app.schemas.model_schema import ModelInfoResponse, ModelPredictionResponse


def model_exists() -> bool:
    """Return True when the configured model artifact exists."""
    return model_loader.model_exists()


def load_model() -> Any | None:
    """Load model into memory (POST /model/predict only)."""
    model, _ = model_loader.load_model_artifact()
    return model


def get_model_info() -> ModelInfoResponse:
    """Return metadata without keeping the joblib loaded in memory."""
    meta = model_loader.get_model_metadata_lightweight()
    return ModelInfoResponse(
        model_path=str(meta["path"]),
        model_exists=meta["exists"],
        model_type=meta["model_type"],
        expected_feature_count=len(meta["feature_names"]) if meta["feature_names"] else None,
        feature_names=meta["feature_names"],
        artifact_status=meta["artifact_status"],
    )


def predict_single(features: dict[str, float | int | None]) -> ModelPredictionResponse:
    """Run inference for a single feature payload (loads model on demand)."""
    model, path = model_loader.load_model_artifact()
    if model is None:
        raise RuntimeError("Model is not available for inference.")

    feature_names = model_loader.get_feature_names(model)
    if not feature_names:
        raise RuntimeError("Model feature names could not be determined.")

    anomaly_label, is_anomaly, score = inference.predict_from_features(
        model=model,
        feature_names=feature_names,
        features=features,
    )
    return ModelPredictionResponse(
        anomaly_label=anomaly_label,
        is_anomaly=is_anomaly,
        anomaly_score=score,
        model_name=path.name,
    )
