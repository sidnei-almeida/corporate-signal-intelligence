"""Validation-protocol endpoints.

What makes the score trustworthy is not the score but the protocol behind it: ten
detectors under one temporal split, a criterion built only from information after the
scoring date, significance testing across issuer-year blocks, and walk-forward refitting.
These endpoints serve that evidence so the interface can show it rather than assert it.
"""

import logging

from fastapi import APIRouter, HTTPException, Path

from app.services import validation_service

logger = logging.getLogger("app.routes.validation")

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/protocol")
def protocol() -> dict:
    """The evaluation criterion, the selected score, and the headline evidence."""
    logger.info("validation_protocol")
    result = validation_service.get_protocol()
    if not result.get("criterion"):
        raise HTTPException(
            status_code=503,
            detail="Validation artifacts are not available. Run the evaluation notebook.",
        )
    return result


@router.get("/artifacts")
def artifacts() -> dict:
    """List the exported validation tables that are present."""
    return {"artifacts": validation_service.available_artifacts()}


@router.get("/detectors")
def detectors() -> dict:
    """The benchmark: every detector's discrimination, precision at budget and rank."""
    logger.info("validation_detectors")
    records = validation_service.get_artifact("detectors")
    if not records:
        raise HTTPException(status_code=503, detail="Detector benchmark not available.")
    return {"count": len(records), "records": records}


@router.get("/walk-forward")
def walk_forward() -> dict:
    """Year-by-year performance under annual refitting on an expanding window."""
    return {"records": validation_service.get_artifact("walk_forward")}


@router.get("/attribution")
def attribution() -> dict:
    """Which features drive the score, and what dominates on flagged days."""
    return {
        "features": validation_service.get_artifact("shap_attribution"),
        "drivers": validation_service.get_artifact("alert_drivers"),
    }


@router.get("/{artifact}")
def artifact(
    artifact: str = Path(..., description="Name from /validation/artifacts"),
) -> dict:
    """Serve any exported validation table by name."""
    if artifact not in validation_service.ARTIFACTS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown validation artifact '{artifact}'. "
                f"Available: {', '.join(validation_service.available_artifacts())}."
            ),
        )
    records = validation_service.get_artifact(artifact)
    if not records:
        raise HTTPException(
            status_code=503, detail=f"Artifact '{artifact}' is not available on disk."
        )
    return {"artifact": artifact, "count": len(records), "records": records}
