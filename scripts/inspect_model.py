#!/usr/bin/env python3
"""Inspect model/*.joblib and sync feature_schema.json + training_metrics template."""

from __future__ import annotations

import json
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
LEGACY = ROOT / "models"


def _find_joblib() -> Path | None:
    for directory in (MODEL_DIR, LEGACY):
        if not directory.is_dir():
            continue
        files = sorted(directory.glob("*.joblib"))
        if files:
            return files[0]
    return None


def main() -> None:
    path = _find_joblib()
    if path is None:
        print("No .joblib in model/ or models/")
        raise SystemExit(1)

    model = joblib.load(path)
    print(f"Model file: {path.relative_to(ROOT)}")
    print(f"Type: {type(model).__name__}")

    names: list[str] = []
    if hasattr(model, "feature_names_in_"):
        names = [str(x) for x in model.feature_names_in_]
        print("feature_names_in_:", names)
    elif hasattr(model, "named_steps"):
        for step in ("classifier", "model", "clf"):
            est = model.named_steps.get(step)
            if est is not None and hasattr(est, "feature_names_in_"):
                names = [str(x) for x in est.feature_names_in_]
                print(f"feature_names_in_ ({step}):", names)
                break

    if names:
        schema = {
            "description": "Synced from sklearn feature_names_in_",
            "features": [{"name": n, "type": "float"} for n in names],
            "label_map": {"0": "normal", "1": "anomaly"},
        }
        out = MODEL_DIR / "feature_schema.json"
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        print(f"Wrote {out.relative_to(ROOT)}")

    if hasattr(model, "classes_"):
        print("classes_:", list(model.classes_))

    metrics_path = MODEL_DIR / "training_metrics.json"
    if not metrics_path.exists():
        template = {
            "model_file": path.name,
            "estimator": type(model).__name__,
            "note": "Fill metrics from your training notebook (classification report, ROC-AUC, etc.).",
            "metrics": {
                "accuracy": None,
                "precision_anomaly": None,
                "recall_anomaly": None,
                "f1_anomaly": None,
                "roc_auc": None,
            },
            "train_test_split": {"train": None, "test": None},
        }
        metrics_path.write_text(json.dumps(template, indent=2), encoding="utf-8")
        print(f"Created template {metrics_path.relative_to(ROOT)} — edit with real values.")


if __name__ == "__main__":
    main()
