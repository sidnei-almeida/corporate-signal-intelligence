"""Model inference endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.model_schema import ModelInfoResponse, ModelPredictionRequest, ModelPredictionResponse
from app.services import model_service

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/info", response_model=ModelInfoResponse)
def model_info() -> ModelInfoResponse:
    """Return metadata about the trained model artifact."""
    return model_service.get_model_info()


@router.post("/predict", response_model=ModelPredictionResponse)
def predict_anomaly(request: ModelPredictionRequest) -> ModelPredictionResponse:
    """Run anomaly inference for a single feature payload."""
    if not model_service.model_exists():
        raise HTTPException(status_code=503, detail="Model artifact is not available.")
    try:
        return model_service.predict_single(request.features)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Model inference failed.") from exc
