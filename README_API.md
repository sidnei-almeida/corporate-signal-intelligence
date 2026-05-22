# Corporate Signal Intelligence API

Production-ready FastAPI backend for corporate anomaly detection, CSV-backed analytics, and Groq-powered executive briefings.

## Local setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
cp .env.example .env
```

4. Fill in `.env` with your local secrets and configuration.

5. Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. Open interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Required environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | For briefings | Groq API key for executive briefing generation |
| `GROQ_MODEL` | Optional | Groq model name (default: `llama-3.3-70b-versatile`) |
| `DATABASE_URL` | Optional | Neon/PostgreSQL URL (prepared for future use) |
| `SEC_USER_AGENT` | Optional | SEC EDGAR user agent string |
| `STOOQ_API_KEY` | Optional | Stooq API key |
| `ALPHA_VANTAGE_API_KEY` | Optional | Alpha Vantage API key |
| `MODEL_PATH` | Optional | Path to joblib model artifact |
| `PORT` | Optional | Server port (default: `8000`) |
| `APP_ENV` | Optional | Environment name (default: `development`) |
| `DATA_DIR` | Optional | CSV data directory (default: `data`) |
| `MODELS_DIR` | Optional | Model artifacts directory (default: `models`) |

The first API version reads from local CSV files in `data/` and loads the trained model from `models/`. The API still starts when `DATABASE_URL` is missing.

For PostgreSQL/Neon setup, migrations, and CSV loading, see [README_DATABASE.md](README_DATABASE.md).

## Available endpoints

### System
- `GET /` — API metadata
- `GET /health` — Health check

### Companies
- `GET /companies` — List available tickers
- `GET /companies/{ticker}` — Company profile and anomaly stats

### Anomalies
- `GET /anomalies` — Filter anomaly records
- `GET /anomalies/top` — Top anomalous records
- `GET /anomalies/summary` — Summary grouped by ticker
- `GET /anomalies/types` — Anomaly type counts
- `GET /anomalies/{ticker}` — Anomalies for one ticker

### Model
- `GET /model/info` — Model artifact metadata
- `POST /model/predict` — Run anomaly inference

### Briefings
- `POST /briefings/generate` — Generate briefing for ticker/date
- `POST /briefings/generate-from-record` — Generate briefing from record payload
- `GET /briefings/sample` — Generate briefing for top anomaly

## Render deployment

1. Push this repository to GitHub.
2. Create a new **Web Service** on Render using the repo.
3. Use:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`

## Memory optimization (Render)

The API is tuned for Render free-tier memory limits:

- **Only** `anomaly_detection_results.csv` (minimal columns) or PostgreSQL `anomaly_results` is loaded at startup.
- Large files (`model_ready_dataset.csv`, `market_features.csv`, etc.) are **not** loaded unless you call internal loaders explicitly.
- Startup builds lightweight caches: company list, anomaly summary, top anomalies, type counts, company profiles.
- `/health` and `/model/info` do not load the joblib model into RAM (`/model/predict` loads it on demand).
- Use **one Uvicorn worker** on Render (`--workers 1` in `render.yaml`).
- Prefer `DATA_SOURCE=database` in production so the app queries Neon with SQL instead of holding wide CSVs in memory.
4. Add secrets in the Render dashboard:
   - `GROQ_API_KEY`
   - `DATABASE_URL` (optional for MVP)
   - `SEC_USER_AGENT`
   - `STOOQ_API_KEY`
   - `ALPHA_VANTAGE_API_KEY`
5. Ensure `data/` CSV files and `models/*.joblib` are committed or otherwise available in the deployed artifact.

You can also use the included `render.yaml` Blueprint for infrastructure-as-code deployment.

## Quick test commands

```bash
curl http://localhost:8000/health
curl http://localhost:8000/companies
curl "http://localhost:8000/anomalies/top?limit=5"
curl http://localhost:8000/anomalies/summary
curl http://localhost:8000/model/info
```

Generate a briefing:

```bash
curl -X POST http://localhost:8000/briefings/generate \
  -H "Content-Type: application/json" \
  -d '{"ticker":"META","date":"2026-01-29"}'
```
