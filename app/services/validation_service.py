"""Access to the evidence the evaluation notebook produced.

These artifacts are what separates the tool from a generic anomaly dashboard: the
benchmark that put ten detectors under one protocol, the prospective criterion they were
scored against, and the walk-forward and attribution results. They are read from disk
rather than restated in code, so the numbers served are the ones the last notebook run
measured.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

SUMMARY_FILE = "validation_summary.json"
TRAINING_METRICS_FILE = "training_metrics.json"

# Artifact name -> file. Each is a table the notebook computed and exported.
ARTIFACTS: dict[str, str] = {
    "detectors": "validation_detector_metrics.csv",
    "horizon": "validation_horizon_sensitivity.csv",
    "pairwise": "validation_pairwise_tests.csv",
    "walk_forward": "validation_walk_forward.csv",
    "ensembles": "validation_ensembles.csv",
    "training_window": "validation_training_window.csv",
    "issuer_year_blocks": "validation_issuer_year_blocks.csv",
    "shap_attribution": "validation_shap_attribution.csv",
    "alert_drivers": "validation_alert_drivers.csv",
    "regime_behaviour": "validation_regime_behaviour.csv",
    "alert_concentration": "validation_alert_concentration.csv",
    "budget_stability": "validation_budget_stability.csv",
    "feature_ablation": "validation_feature_ablation.csv",
    "model_jaccard": "validation_model_jaccard.csv",
    "model_spearman": "validation_model_spearman.csv",
    "monthly_alert_rate": "validation_monthly_alert_rate.csv",
    "model_timings": "model_timings.csv",
}


def _data_path(filename: str) -> Path:
    return get_settings().data_path / filename


def _model_path(filename: str) -> Path:
    # The notebooks write metadata to <repo>/model, alongside the <repo>/models artifact
    # directory. model_loader resolves feature_schema.json the same way.
    return PROJECT_ROOT / "model" / filename


@lru_cache(maxsize=1)
def get_summary() -> dict[str, Any]:
    """Protocol scalars: criterion, budget, base rate, Friedman, walk-forward, alerts."""
    path = _model_path(SUMMARY_FILE)
    if not path.is_file():
        logger.warning("validation summary missing at %s", path)
        return {}
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def get_training_metrics() -> dict[str, Any]:
    """Which score ships, which is context only, and what each measured."""
    path = _model_path(TRAINING_METRICS_FILE)
    if not path.is_file():
        logger.warning("training metrics missing at %s", path)
        return {}
    return json.loads(path.read_text())


@lru_cache(maxsize=len(ARTIFACTS))
def _load_artifact(name: str) -> tuple[dict[str, Any], ...]:
    """Read one exported table as records. Cached: these files change only on a re-run."""
    filename = ARTIFACTS.get(name)
    if filename is None:
        raise KeyError(name)
    path = _data_path(filename)
    if not path.is_file():
        logger.warning("validation artifact %s missing at %s", name, path)
        return ()
    frame = pd.read_csv(path)
    # The index column carries the entity name (model, feature, year); keep it explicit.
    frame = frame.rename(columns={frame.columns[0]: frame.columns[0] or "key"})
    return tuple(
        {key: (None if pd.isna(value) else value) for key, value in record.items()}
        for record in frame.to_dict(orient="records")
    )


def get_artifact(name: str) -> list[dict[str, Any]]:
    """Return one exported validation table."""
    return [dict(record) for record in _load_artifact(name)]


def available_artifacts() -> list[str]:
    """Artifact names whose files are present on disk."""
    return sorted(name for name, file in ARTIFACTS.items() if _data_path(file).is_file())


def get_protocol() -> dict[str, Any]:
    """The headline claim, assembled from the summary and the selected-score metrics."""
    summary = get_summary()
    metrics = get_training_metrics()
    primary = metrics.get("primary_score", {})
    secondary = metrics.get("secondary_score", {})
    return {
        "criterion": summary.get("criterion"),
        "forward_horizon": summary.get("forward_horizon"),
        "stress_multiple": summary.get("stress_multiple"),
        "alert_budget": summary.get("alert_budget"),
        "base_rate": summary.get("base_rate"),
        "test_window": summary.get("test_window"),
        "universe": summary.get("universe", []),
        "primary_score": primary,
        "secondary_score": secondary,
        "friedman": summary.get("friedman", {}),
        "walk_forward": summary.get("walk_forward", {}),
        "calm_market": summary.get("calm_market", {}),
        "alerts": summary.get("alerts", {}),
    }


def clear_cache() -> None:
    """Drop cached artifacts (used after a pipeline re-run)."""
    get_summary.cache_clear()
    get_training_metrics.cache_clear()
    _load_artifact.cache_clear()
