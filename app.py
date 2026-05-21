"""
Corporate Signal Intelligence — FastAPI service for financial anomaly scoring.

Loads a scikit-learn-compatible model from model/*.joblib (Render-friendly, CPU-only).
Optional Groq-powered executive briefings when GROQ_API_KEY is set.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"
LEGACY_MODEL_DIR = BASE_DIR / "models"
DEFAULT_MODEL_GLOB = "*.joblib"


def _schema_paths() -> List[Path]:
    return [
        MODEL_DIR / "feature_schema.json",
        LEGACY_MODEL_DIR / "feature_schema.json",
    ]


def _model_search_dirs() -> List[Path]:
    dirs: List[Path] = []
    if MODEL_DIR.is_dir():
        dirs.append(MODEL_DIR)
    if LEGACY_MODEL_DIR.is_dir():
        dirs.append(LEGACY_MODEL_DIR)
    return dirs

MODEL: Any = None
MODEL_PATH: Optional[Path] = None
FEATURE_NAMES: List[str] = []
LABEL_MAP: Dict[str, str] = {"0": "normal", "1": "anomaly"}


def _load_feature_schema() -> tuple[List[str], Dict[str, str]]:
    schema_path = next((p for p in _schema_paths() if p.exists()), None)
    if schema_path is None:
        return [], LABEL_MAP
    try:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        names = [f["name"] for f in data.get("features", []) if "name" in f]
        label_map = {str(k): str(v) for k, v in data.get("label_map", LABEL_MAP).items()}
        return names, label_map
    except Exception:
        return [], LABEL_MAP


def _resolve_model_path() -> Optional[Path]:
    env_path = os.getenv("MODEL_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
    candidates: List[Path] = []
    for directory in _model_search_dirs():
        candidates.extend(sorted(directory.glob(DEFAULT_MODEL_GLOB)))
    return candidates[0] if candidates else None


def _feature_names_from_model(model: Any) -> List[str]:
    if hasattr(model, "feature_names_in_"):
        return [str(x) for x in model.feature_names_in_]
    if hasattr(model, "named_steps"):
        final = model.named_steps.get("classifier") or model.named_steps.get("model")
        if final is not None and hasattr(final, "feature_names_in_"):
            return [str(x) for x in final.feature_names_in_]
    schema_names, _ = _load_feature_schema()
    return schema_names


def load_model() -> tuple[Any, Optional[Path]]:
    path = _resolve_model_path()
    if path is None:
        return None, None
    try:
        model = joblib.load(path)
        return model, path
    except Exception as exc:
        print(f"[load_model] Failed to load {path}: {exc}")
        return None, None


def _row_to_array(payload: Dict[str, float], feature_names: List[str]) -> np.ndarray:
    missing = [n for n in feature_names if n not in payload]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing features: {missing}. Expected: {feature_names}",
        )
    row = [float(payload[n]) for n in feature_names]
    return np.array([row], dtype=np.float64)


def _predict(model: Any, X: np.ndarray) -> tuple[int, float, Optional[Dict[str, float]]]:
    pred = int(model.predict(X)[0])
    proba: Optional[Dict[str, float]] = None
    confidence = 1.0
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)[0]
        confidence = float(probs[pred])
        classes = getattr(model, "classes_", list(range(len(probs))))
        proba = {str(int(c)): float(p) for c, p in zip(classes, probs)}
    return pred, confidence, proba


class PredictRequest(BaseModel):
    features: Dict[str, float] = Field(
        ...,
        description="Map of feature name → numeric value (see GET /model/info).",
    )


class PredictResponse(BaseModel):
    predicted_class: int
    predicted_label: str
    confidence: float
    probabilities: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None


class BatchPredictRequest(BaseModel):
    instances: List[Dict[str, float]]


class BatchPredictResponse(BaseModel):
    predictions: List[PredictResponse]


class BriefingRequest(BaseModel):
    company_name: str = Field(..., min_length=1)
    ticker: Optional[str] = None
    predicted_label: str
    confidence: float
    features: Dict[str, float] = Field(default_factory=dict)
    extra_context: Optional[str] = Field(
        None, description="Optional notes (SEC excerpt, news headline, etc.)."
    )


class BriefingResponse(BaseModel):
    briefing: str
    model_used: str


class ModelInfoResponse(BaseModel):
    status: str
    model_path: Optional[str]
    model_type: Optional[str]
    feature_names: List[str]
    label_map: Dict[str, str]
    groq_configured: bool
    training_metrics: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODEL, MODEL_PATH, FEATURE_NAMES, LABEL_MAP
    schema_names, LABEL_MAP = _load_feature_schema()
    MODEL, MODEL_PATH = load_model()
    if MODEL is not None:
        FEATURE_NAMES = _feature_names_from_model(MODEL) or schema_names
        print(f"Model loaded: {MODEL_PATH} ({MODEL.__class__.__name__})")
    else:
        FEATURE_NAMES = schema_names
        print("WARNING: No .joblib found under model/. Place weights before inference.")
    yield
    MODEL = None


app = FastAPI(
    title="Corporate Signal Intelligence API",
    description="Financial anomaly scoring from a joblib model; optional Groq executive briefings.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "service": "Corporate Signal Intelligence API",
        "docs": "/docs",
        "health": "/health",
        "model_info": "/model/info",
        "predict": "/predict",
        "briefing": "/briefing (POST, requires GROQ_API_KEY)",
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if MODEL is not None else "model_not_loaded",
        model_loaded=MODEL is not None,
    )


def _load_training_metrics() -> Optional[Dict[str, Any]]:
    for path in (MODEL_DIR / "training_metrics.json", LEGACY_MODEL_DIR / "training_metrics.json"):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


@app.get("/model/info", response_model=ModelInfoResponse, tags=["model"])
def model_info() -> ModelInfoResponse:
    return ModelInfoResponse(
        status="loaded" if MODEL is not None else "unavailable",
        model_path=str(MODEL_PATH) if MODEL_PATH else None,
        model_type=MODEL.__class__.__name__ if MODEL is not None else None,
        feature_names=FEATURE_NAMES,
        label_map=LABEL_MAP,
        groq_configured=bool(os.getenv("GROQ_API_KEY")),
        training_metrics=_load_training_metrics(),
    )


@app.post("/predict", response_model=PredictResponse, tags=["inference"])
def predict(req: PredictRequest) -> PredictResponse:
    if MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Add a .joblib file under model/.")
    if not FEATURE_NAMES:
        raise HTTPException(
            status_code=503,
            detail="Feature names unknown. Update model/feature_schema.json or use a sklearn model with feature_names_in_.",
        )
    X = _row_to_array(req.features, FEATURE_NAMES)
    try:
        pred, confidence, proba = _predict(MODEL, X)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
    label = LABEL_MAP.get(str(pred), str(pred))
    return PredictResponse(
        predicted_class=pred,
        predicted_label=label,
        confidence=confidence,
        probabilities=proba,
        model_path=str(MODEL_PATH) if MODEL_PATH else None,
    )


@app.post("/predict/batch", response_model=BatchPredictResponse, tags=["inference"])
def predict_batch(req: BatchPredictRequest) -> BatchPredictResponse:
    if MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    if not req.instances:
        raise HTTPException(status_code=400, detail="instances must not be empty.")
    if not FEATURE_NAMES:
        raise HTTPException(status_code=503, detail="Feature names not configured.")
    out: List[PredictResponse] = []
    for inst in req.instances:
        X = _row_to_array(inst, FEATURE_NAMES)
        pred, confidence, proba = _predict(MODEL, X)
        label = LABEL_MAP.get(str(pred), str(pred))
        out.append(
            PredictResponse(
                predicted_class=pred,
                predicted_label=label,
                confidence=confidence,
                probabilities=proba,
                model_path=str(MODEL_PATH) if MODEL_PATH else None,
            )
        )
    return BatchPredictResponse(predictions=out)


@app.post("/briefing", response_model=BriefingResponse, tags=["briefing"])
def executive_briefing(req: BriefingRequest) -> BriefingResponse:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY not set. Add it in Render Environment or local .env for briefings.",
        )
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"langchain-groq not installed: {exc}") from exc

    system = (
        "You are a corporate intelligence analyst. Write a concise executive briefing "
        "(3–6 sentences, plain English). Be factual; do not invent SEC filing text. "
        "Highlight risk level and suggested follow-ups."
    )
    ticker_line = f"Ticker: {req.ticker}\n" if req.ticker else ""
    features_text = json.dumps(req.features, indent=2) if req.features else "N/A"
    user = f"""Company: {req.company_name}
{ticker_line}ML signal: {req.predicted_label} (confidence {req.confidence:.2%})
Key metrics:
{features_text}
Additional context:
{req.extra_context or "None"}
"""
    llm = ChatGroq(model=model_name, temperature=0.4, max_tokens=512, groq_api_key=api_key)
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    text = response.content if hasattr(response, "content") else str(response)
    return BriefingResponse(briefing=text.strip(), model_used=model_name)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=os.getenv("RENDER") is None)
