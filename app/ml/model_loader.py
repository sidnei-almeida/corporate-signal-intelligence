"""Load and cache the trained anomaly detection model."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from app.core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def load_model_artifact() -> tuple[Any | None, Path]:
    """Load the joblib model from disk and cache it in memory (inference only)."""
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


def _schema_paths() -> list[Path]:
    settings = get_settings()
    return [
        PROJECT_ROOT / "model" / "feature_schema.json",
        settings.models_path / "feature_schema.json",
    ]


def get_feature_names_from_schema() -> list[str]:
    """Read feature names from JSON schema without loading the joblib artifact."""
    for path in _schema_paths():
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [str(item["name"]) for item in data.get("features", []) if "name" in item]
        except Exception:
            continue
    return []


def get_feature_names(model: Any | None = None) -> list[str]:
    """Extract feature names from model or fall back to feature_schema.json."""
    if model is not None:
        if hasattr(model, "feature_names_in_"):
            return [str(name) for name in model.feature_names_in_]
        if hasattr(model, "named_steps"):
            for step_name in ("classifier", "model", "clf", "isolationforest"):
                step = model.named_steps.get(step_name)
                if step is not None and hasattr(step, "feature_names_in_"):
                    return [str(name) for name in step.feature_names_in_]
    return get_feature_names_from_schema()


def get_model_metadata_lightweight() -> dict[str, Any]:
    """Return model file metadata without loading the joblib into RAM."""
    settings = get_settings()
    path = settings.model_file_path
    exists = path.is_file()
    feature_names = get_feature_names_from_schema()
    model_type = "Pipeline" if exists else None
    status = "available" if exists else "missing"
    return {
        "path": path,
        "exists": exists,
        "model_type": model_type,
        "feature_names": feature_names,
        "artifact_status": status,
    }
