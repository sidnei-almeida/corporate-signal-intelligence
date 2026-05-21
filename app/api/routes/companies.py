"""Company endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Path

from app.schemas.company_schema import CompanyListItem, CompanyProfile
from app.services import data_service
from app.utils.ticker import is_plausible_ticker, normalize_ticker

logger = logging.getLogger("app.routes.companies")

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyListItem])
def list_companies() -> list[CompanyListItem]:
    """Return available tickers and basic metadata."""
    logger.info("list_companies")
    tickers = data_service.get_available_companies()
    items: list[CompanyListItem] = []
    for ticker in tickers:
        profile = data_service.get_company_profile(ticker)
        if profile is None:
            items.append(CompanyListItem(ticker=ticker))
            continue
        items.append(
            CompanyListItem(
                ticker=profile["ticker"],
                row_count=profile["row_count"],
                first_date=profile["first_date"],
                last_date=profile["last_date"],
                anomaly_count=profile["anomaly_count"],
                anomaly_rate=profile["anomaly_rate"],
            )
        )
    return items


@router.get("/{ticker}", response_model=CompanyProfile)
def get_company(
    ticker: str = Path(..., min_length=1, max_length=12, description="Stock ticker symbol"),
) -> CompanyProfile:
    """Return profile details for a specific ticker."""
    if not is_plausible_ticker(ticker):
        raise HTTPException(status_code=404, detail=f"Invalid ticker '{ticker}'.")

    normalized = normalize_ticker(ticker)
    logger.info("get_company ticker=%s", normalized)

    profile = data_service.get_company_profile(normalized)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{normalized}' not found.")
    return CompanyProfile(**profile)
