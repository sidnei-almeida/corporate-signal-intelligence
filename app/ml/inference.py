"""Model inference helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _decision_score(model: Any, features: np.ndarray) -> float | None:
    """Return anomaly score from decision_function when available."""
    estimator = model
    if hasattr(model, "named_steps"):
        estimator = model.named_steps.get("isolationforest") or model
    if hasattr(model, "decision_function"):
        return float(model.decision_function(features)[0])
    if hasattr(estimator, "decision_function"):
        return float(estimator.decision_function(features)[0])
    if hasattr(model, "score_samples"):
        return float(model.score_samples(features)[0])
    if hasattr(estimator, "score_samples"):
        return float(estimator.score_samples(features)[0])
    return None


def predict_from_features(
    model: Any,
    feature_names: list[str],
    features: dict[str, float | int | None],
) -> tuple[str, bool, float | None]:
    """Run a single inference using the loaded model."""
    missing = [name for name in feature_names if name not in features]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    row = [float(features[name]) for name in feature_names]
    frame = pd.DataFrame([row], columns=feature_names)
    prediction = int(model.predict(frame)[0])
    is_anomaly = prediction == -1
    anomaly_label = "anomaly" if is_anomaly else "normal"

    score = _decision_score(model, frame.to_numpy(dtype=np.float64))
    return anomaly_label, is_anomaly, score
