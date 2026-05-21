"""Model loading and prediction service."""

from __future__ import annotations

from typing import Any

from app.ml import inference, model_loader
from app.schemas.model_schema import ModelInfoResponse, ModelPredictionResponse


def model_exists() -> bool:
    """Return True when the configured model artifact exists."""
    return model_loader.model_exists()


def load_model() -> Any | None:
    """Return the cached model object."""
    model, _ = model_loader.load_model_artifact()
    return model


def get_model_info() -> ModelInfoResponse:
    """Return metadata about the trained model artifact."""
    model, path = model_loader.load_model_artifact()
    feature_names = model_loader.get_feature_names(model) if model is not None else []
    exists = path.is_file()
    status = "loaded" if model is not None else ("missing" if not exists else "failed_to_load")
    return ModelInfoResponse(
        model_path=str(path),
        model_exists=exists,
        model_type=type(model).__name__ if model is not None else None,
        expected_feature_count=len(feature_names) if feature_names else None,
        feature_names=feature_names,
        artifact_status=status,
    )


def predict_single(features: dict[str, float | int | None]) -> ModelPredictionResponse:
    """Run inference for a single feature payload."""
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
