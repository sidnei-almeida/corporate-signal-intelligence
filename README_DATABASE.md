# PostgreSQL / Neon Database Layer

Corporate Signal Intelligence supports **CSV mode** (default fallback) and **PostgreSQL mode** (Neon).

## Prerequisites

- `DATABASE_URL` in `.env` or Render secrets
- Example: `postgresql+psycopg://user:pass@host/neondb?sslmode=require`

## 1. Run migrations

```bash
pip install -r requirements.txt
alembic upgrade head
```

## 2. Load CSV data into Neon

```bash
python scripts/load_csv_to_db.py --truncate
```

Load specific tables only:

```bash
python scripts/load_csv_to_db.py --only companies anomaly_results
```

## 3. Data source mode

| `DATA_SOURCE` | Behavior |
|---------------|----------|
| `auto` (default) | Use DB when connected and `anomaly_results` has rows; else CSV |
| `database` | Prefer DB; fall back to CSV if unavailable |
| `csv` | Always use local CSV files |

## Tables

- `companies` — monitored tickers
- `market_features` — daily market features
- `filing_features` — SEC filing activity features
- `financial_features` — consolidated XBRL metrics
- `anomaly_results` — API anomaly records
- `sec_filings` — cleaned SEC filings
- `ai_briefings` — cached Groq briefings (optional)

## Health check

`GET /health` returns:

```json
{
  "data_source": "database",
  "database_connected": true,
  "database_populated": true
}
```

## CSV files mapped

| Table | CSV file |
|-------|----------|
| companies | `clean_company_metadata.csv` + tickers from anomalies |
| market_features | `market_features.csv` |
| filing_features | `filing_features.csv` |
| financial_features | `financial_features_selected.csv` |
| anomaly_results | `anomaly_detection_results.csv` |
| sec_filings | `clean_sec_filings.csv` |

## Notes

- Existing API routes are unchanged.
- CSV files remain in the repo for fallback and local dev without Neon.
- After loading data, restart the API or rely on `auto` mode on next request.
