"""Collect the complete SEC EDGAR filing history for the study universe.

Two problems with a naive collection are fixed here.

**Pagination.** ``/submissions/CIK##########.json`` returns only the most recent
~1,000 filings inline; everything older sits in ``filings.files[]`` as separate
JSON documents. Ignoring them silently truncates the history of any company that
files often.

**Corporate lineage.** A ticker is not an entity. Alphabet Inc. (CIK 1652044)
only exists from October 2015 — Google Inc.'s filings from 2001 to 2015 live
under CIK 1288776. Oracle reorganised in 2005, so ORCL's pre-2006 history is
under Oracle Systems Corp (CIK 777676). Collecting only the current CIK loses
11 years of GOOGL and 12 years of ORCL disclosures.

Predecessor entities keep filing after a successor appears (Section 16 forms for
subsidiary insiders, for instance), so each predecessor is given an explicit
validity window that ends when the successor's first filing lands. Filings are
then deduplicated on accession number.

    python scripts/collect_sec_full_history.py
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "Corporate Signal Intelligence (MBA USP/Esalq research) addoqyn@gmail.com",
)

# SEC asks for no more than 10 requests/second; we stay far below that.
REQUEST_DELAY_SECONDS = 0.4

# ticker -> entities that filed under it, newest first. ``until`` bounds a
# predecessor to the period before its successor's first filing.
ENTITIES: dict[str, list[dict]] = {
    "AAPL": [{"cik": 320193, "name": "Apple Inc."}],
    "MSFT": [{"cik": 789019, "name": "Microsoft Corporation"}],
    "NVDA": [{"cik": 1045810, "name": "NVIDIA Corporation"}],
    "AMZN": [{"cik": 1018724, "name": "Amazon.com, Inc."}],
    "META": [{"cik": 1326801, "name": "Meta Platforms, Inc."}],
    "TSLA": [{"cik": 1318605, "name": "Tesla, Inc."}],
    "AMD": [{"cik": 2488, "name": "Advanced Micro Devices, Inc."}],
    "INTC": [{"cik": 50863, "name": "Intel Corporation"}],
    "GOOGL": [
        {"cik": 1652044, "name": "Alphabet Inc."},
        {"cik": 1288776, "name": "Google Inc.", "until": "2015-10-02"},
    ],
    "ORCL": [
        {"cik": 1341439, "name": "Oracle Corporation"},
        {"cik": 777676, "name": "Oracle Systems Corporation", "until": "2005-10-19"},
    ],
}

TARGET_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "ResearchAndDevelopmentExpense",
]


def sec_get_json(url: str) -> dict:
    response = requests.get(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    time.sleep(REQUEST_DELAY_SECONDS)
    return payload


def _filings_frame(block: dict, ticker: str, entity: dict) -> pd.DataFrame:
    """Turn one ``filings.recent``-shaped block into rows."""
    if not block.get("accessionNumber"):
        return pd.DataFrame()
    return pd.DataFrame({
        "ticker": ticker,
        "cik": entity["cik"],
        "entity_name": entity["name"],
        "accession_number": block["accessionNumber"],
        "filing_date": block["filingDate"],
        "report_date": block["reportDate"],
        "form_type": block["form"],
        "primary_document": block.get("primaryDocument"),
    })


def fetch_entity_filings(ticker: str, entity: dict) -> pd.DataFrame:
    """Every filing for one legal entity, including the paginated archive."""
    cik = entity["cik"]
    submissions = sec_get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")

    frames = [_filings_frame(submissions["filings"]["recent"], ticker, entity)]

    for extra in submissions["filings"].get("files", []):
        older = sec_get_json(f"https://data.sec.gov/submissions/{extra['name']}")
        frames.append(_filings_frame(older, ticker, entity))

    filings = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    filings["filing_date"] = pd.to_datetime(filings["filing_date"], errors="coerce")
    filings["report_date"] = pd.to_datetime(filings["report_date"], errors="coerce")

    if entity.get("until"):
        filings = filings[filings["filing_date"] < pd.Timestamp(entity["until"])]

    return filings


def fetch_entity_facts(ticker: str, entity: dict) -> pd.DataFrame:
    """Selected us-gaap XBRL concepts for one legal entity.

    Entities that predate the 2009 XBRL mandate simply have no company-facts
    document; that is a 404, not a failure of the collection.
    """
    cik = entity["cik"]
    try:
        payload = sec_get_json(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        )
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            print(f"    no XBRL facts for CIK {cik} ({entity['name']})")
            return pd.DataFrame()
        raise

    us_gaap = payload.get("facts", {}).get("us-gaap", {})
    rows = []

    for concept in TARGET_CONCEPTS:
        if concept not in us_gaap:
            continue
        concept_data = us_gaap[concept]
        for unit, observations in concept_data.get("units", {}).items():
            for obs in observations:
                rows.append({
                    "ticker": ticker,
                    "cik": cik,
                    "entity_name": entity["name"],
                    "taxonomy": "us-gaap",
                    "concept": concept,
                    "label": concept_data.get("label"),
                    "description": concept_data.get("description"),
                    "unit": unit,
                    "value": obs.get("val"),
                    "start_date": obs.get("start"),
                    "end_date": obs.get("end"),
                    "filing_date": obs.get("filed"),
                    "form_type": obs.get("form"),
                    "fiscal_year": obs.get("fy"),
                    "fiscal_period": obs.get("fp"),
                })

    facts = pd.DataFrame(rows)
    if facts.empty:
        return facts

    for column in ("start_date", "end_date", "filing_date"):
        facts[column] = pd.to_datetime(facts[column], errors="coerce")

    if entity.get("until"):
        facts = facts[facts["filing_date"] < pd.Timestamp(entity["until"])]

    return facts


def collect() -> tuple[pd.DataFrame, pd.DataFrame]:
    collected_at = datetime.now(timezone.utc)
    filing_frames, fact_frames = [], []

    for ticker, entities in ENTITIES.items():
        for entity in entities:
            window = f" (until {entity['until']})" if entity.get("until") else ""
            print(f"{ticker} | CIK {entity['cik']:010d} — {entity['name']}{window}")

            filings = fetch_entity_filings(ticker, entity)
            filing_frames.append(filings)
            span = (
                f"{filings['filing_date'].min():%Y-%m-%d} → "
                f"{filings['filing_date'].max():%Y-%m-%d}"
                if not filings.empty else "none"
            )
            print(f"    filings: {len(filings):>6}  {span}")

            facts = fetch_entity_facts(ticker, entity)
            if not facts.empty:
                fact_frames.append(facts)
                print(f"    facts:   {len(facts):>6}")

    all_filings = pd.concat(filing_frames, ignore_index=True)
    all_filings = all_filings.drop_duplicates(subset=["ticker", "accession_number"])
    all_filings["source"] = "sec_edgar"
    all_filings["collected_at"] = collected_at
    all_filings = all_filings.sort_values(["ticker", "filing_date"]).reset_index(drop=True)

    all_facts = pd.concat(fact_frames, ignore_index=True)
    all_facts = all_facts.drop_duplicates(
        subset=["ticker", "concept", "unit", "start_date", "end_date",
                "filing_date", "form_type", "fiscal_year", "fiscal_period"]
    )
    all_facts["source"] = "sec_edgar"
    all_facts["collected_at"] = collected_at
    all_facts = all_facts.sort_values(
        ["ticker", "concept", "end_date", "filing_date"]
    ).reset_index(drop=True)

    return all_filings, all_facts


if __name__ == "__main__":
    filings, facts = collect()

    filings_path = DATA_DIR / "sec_filings_full_raw.csv"
    facts_path = DATA_DIR / "sec_company_facts_full_raw.csv"

    filings.to_csv(filings_path, index=False)
    facts.to_csv(facts_path, index=False)

    print(f"\nfilings: {filings.shape} -> {filings_path.relative_to(REPO_ROOT)}")
    print(f"facts:   {facts.shape} -> {facts_path.relative_to(REPO_ROOT)}")
