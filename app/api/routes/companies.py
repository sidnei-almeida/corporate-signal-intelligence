"""Company endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.company_schema import CompanyListItem, CompanyProfile
from app.services import data_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyListItem])
def list_companies() -> list[CompanyListItem]:
    """Return available tickers and basic metadata."""
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
def get_company(ticker: str) -> CompanyProfile:
    """Return profile details for a specific ticker."""
    profile = data_service.get_company_profile(ticker)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found.")
    return CompanyProfile(**profile)
