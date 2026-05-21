"""Load and cache the trained anomaly detection model."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from app.core.config import get_settings


@lru_cache
def load_model_artifact() -> tuple[Any | None, Path]:
    """Load the joblib model from disk and cache it in memory."""
    settings = get_settings()
    path = settings.model_file_path
    if not path.is_file():
        return None, path
    try:
        model = joblib.load(path)
        return model, path
    except Exception:
        return None, path


def model_exists() -> bool:
    """Return True when the configured model file exists."""
    settings = get_settings()
    return settings.model_file_path.is_file()


def get_feature_names(model: Any) -> list[str]:
    """Extract feature names from a sklearn model or pipeline."""
    if model is None:
        return []
    if hasattr(model, "feature_names_in_"):
        return [str(name) for name in model.feature_names_in_]
    if hasattr(model, "named_steps"):
        for step_name in ("classifier", "model", "clf", "isolationforest"):
            step = model.named_steps.get(step_name)
            if step is not None and hasattr(step, "feature_names_in_"):
                return [str(name) for name in step.feature_names_in_]
    return []
