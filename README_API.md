<h1 align="center">API Reference</h1>

<p align="center">
  <strong>Corporate Signal Intelligence — FastAPI backend</strong><br />
  <em>Anomaly analytics, company profiles, model inference, and Groq executive briefings.</em>
</p>

<p align="center">
  <a href="README.md">← Project overview</a>
  &nbsp;·&nbsp;
  <a href="README_DATABASE.md">Database layer →</a>
  &nbsp;·&nbsp;
  <a href="http://localhost:8000/docs">OpenAPI /docs</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Entrypoint-app.main:app-009688?logo=fastapi&logoColor=white" alt="FastAPI entrypoint" />
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Data-auto_|_database_|_csv-4169E1" alt="Data sources" />
</p>

---

## Table of contents

- [Overview](#overview)
- [Quick start](#quick-start)
- [Environment variables](#environment-variables)
- [Data sources](#data-sources)
- [Endpoints](#endpoints)
- [Anomaly fields](#anomaly-fields)
- [Memory optimization (Render)](#memory-optimization-render)
- [Render deployment](#render-deployment)
- [Quick test commands](#quick-test-commands)

---

## Overview

The API is a modular FastAPI application under `app/`. It serves precomputed anomaly intelligence from **PostgreSQL (Neon)** in production, with **CSV fallback** for local development.

| Capability | Description |
|------------|-------------|
| **Companies** | Ticker list, date ranges, anomaly rates, latest flagged row |
| **Anomalies** | Filter, top scores, per-ticker history, type counts |
| **Model** | Artifact metadata and on-demand Isolation Forest inference |
| **Briefings** | Groq-generated executive summaries grounded in anomaly records |

**Entrypoint**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Interactive docs:** `/docs` · **ReDoc:** `/redoc`

---

## Quick start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .env.example .env
```

Edit `.env` locally. **Never commit** `.env` — it is listed in `.gitignore`.

### 3. Run locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/companies | jq
```

For Neon-backed reads, complete [README_DATABASE.md](README_DATABASE.md) first, then set `DATABASE_URL` and `DATA_SOURCE=database`.

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Briefings only | — | Groq API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Model for executive briefings |
| `DATABASE_URL` | DB mode | — | PostgreSQL URL (`postgresql+psycopg://…`) |
| `DATA_SOURCE` | No | `auto` | `auto` · `database` · `csv` |
| `MODEL_PATH` | No | `models/isolation_forest_anomaly_pipeline.joblib` | Joblib artifact path |
| `DATA_DIR` | No | `data` | CSV directory (fallback) |
| `MODELS_DIR` | No | `models` | Model artifacts directory |
| `APP_ENV` | No | `development` | `development` or `production` |
| `PORT` | Render | `8000` | HTTP port |
| `BRIEFING_PROMPT_VERSION` | No | `v2` | Briefing prompt identifier |
| `SEC_USER_AGENT` | Ingestion scripts | — | SEC EDGAR user agent (not used at API runtime) |
| `STOOQ_API_KEY` | Ingestion scripts | — | Stooq key (not used at API runtime) |
| `ALPHA_VANTAGE_API_KEY` | Ingestion scripts | — | Alpha Vantage key (not used at API runtime) |

> API routes do **not** call external market or SEC APIs on each request. Data is read from Neon or local CSVs. Groq is invoked only for briefing endpoints.

---

## Data sources

Resolved at startup via `DATA_SOURCE` and `GET /health`:

| Mode | When active |
|------|-------------|
| `auto` | Database reachable **and** `anomaly_results` has rows → `database`; else `csv` |
| `database` | Prefer PostgreSQL; fall back to CSV if unavailable |
| `csv` | Always read from `data/*.csv` |

**Health response example (production):**

```json
{
  "status": "ok",
  "data_source": "database",
  "database_connected": true,
  "database_populated": true,
  "model_available": true
}
```

---

## Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service name, version, doc links |
| `GET` | `/health` | Status, data source, DB flags, model on disk |

`/health` does **not** load CSVs or the joblib model into memory.

---

### Companies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/companies` | All tickers with row counts and anomaly rates |
| `GET` | `/companies/{ticker}` | Profile: date range, anomaly count, latest flagged record |

**Example**

```bash
curl -s http://localhost:8000/companies/META | jq
```

---

### Anomalies

Static routes are registered **before** `/{ticker}` to avoid routing conflicts.

| Method | Path | Query params | Description |
|--------|------|--------------|-------------|
| `GET` | `/anomalies` | `ticker`, `limit`, `only_anomalies`, `sort_by`, `ascending` | Filtered anomaly records |
| `GET` | `/anomalies/top` | `limit` (default 20) | Most anomalous rows by score |
| `GET` | `/anomalies/summary` | — | Aggregated stats per ticker |
| `GET` | `/anomalies/types` | — | Frequency of `anomaly_type` labels |
| `GET` | `/anomalies/{ticker}` | — | All flagged rows for one ticker |

**Examples**

```bash
curl -s "http://localhost:8000/anomalies?limit=10&only_anomalies=true" | jq
curl -s "http://localhost:8000/anomalies/top?limit=5" | jq
curl -s http://localhost:8000/anomalies/summary | jq
curl -s http://localhost:8000/anomalies/META | jq
```

---

### Model

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/model/info` | Path, feature names from schema, artifact status — **no joblib load** |
| `POST` | `/model/predict` | Single-row inference (loads model on demand) |

**Predict request body**

```json
{
  "features": {
    "daily_return": 0.02,
    "volume_zscore_30d": 2.1,
    "volatility_30d": 0.35
  }
}
```

Feature names must match `model/feature_schema.json` or `models/feature_schema.json`.

---

### Briefings

Requires `GROQ_API_KEY`. Returns structured executive text grounded in the anomaly record.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/briefings/generate` | Briefing for `{ "ticker", "date" }` |
| `POST` | `/briefings/generate-from-record` | Briefing from a full record payload |
| `GET` | `/briefings/sample` | Briefing for the current top anomaly |

**Example**

```bash
curl -s -X POST http://localhost:8000/briefings/generate \
  -H "Content-Type: application/json" \
  -d '{"ticker":"META","date":"2026-01-29"}' | jq
```

---

## Anomaly fields

| Field | Type | Client guidance |
|-------|------|-----------------|
| `is_anomaly` | boolean | **Primary flag** for UI and filters |
| `anomaly_label` | int | `-1` = anomaly, `1` = normal (Isolation Forest) |
| `anomaly_score` | float | Lower = more anomalous |
| `anomaly_type` | string | Comma-separated rule tags (e.g. `price_spike`, `filing_activity`) |

Common `anomaly_type` values: `price_spike`, `volume_spike`, `high_volatility`, `filing_activity`, `revenue_shift`, `negative_margin`, `combined_signal`.

---

## Memory optimization (Render)

The API is tuned for Render free-tier memory limits:

| Practice | Detail |
|----------|--------|
| Minimal startup load | Only `anomaly_results` (SQL or minimal CSV columns) |
| Startup caches | Company list, summary, top anomalies, type counts, profiles |
| Lazy model load | `/model/info` and `/health` never load joblib |
| On-demand inference | `/model/predict` loads the pipeline when called |
| Single worker | `--workers 1` in `render.yaml` |
| Production data | Prefer `DATA_SOURCE=database` to avoid holding wide CSVs in RAM |

Large files (`model_ready_dataset.csv`, `market_features.csv`, etc.) are **not** loaded unless internal loaders are called explicitly.

---

## Render deployment

### Blueprint (`render.yaml`)

| Setting | Value |
|---------|--------|
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| `DATA_SOURCE` | `auto` (set `database` in dashboard for explicit DB-only intent) |

### Dashboard secrets

Configure in **Environment** (never in the repo):

- `GROQ_API_KEY`
- `DATABASE_URL`
- `SEC_USER_AGENT`
- `STOOQ_API_KEY`
- `ALPHA_VANTAGE_API_KEY`

### Checklist

1. Push to GitHub.
2. Create Web Service → connect repository.
3. Add secrets above.
4. Run `alembic upgrade head` and `load_csv_to_db.py` against Neon (one-time or CI).
5. Confirm `GET /health` returns `"data_source": "database"`.

**Live example**

```text
https://corporate-signal-intelligence.onrender.com
```

---

## Quick test commands

```bash
# Health & metadata
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/ | jq

# Companies & anomalies
curl -s http://localhost:8000/companies | jq
curl -s "http://localhost:8000/anomalies/top?limit=5" | jq
curl -s http://localhost:8000/anomalies/summary | jq
curl -s http://localhost:8000/anomalies/types | jq

# Model
curl -s http://localhost:8000/model/info | jq

# Briefing (requires GROQ_API_KEY)
curl -s -X POST http://localhost:8000/briefings/generate \
  -H "Content-Type: application/json" \
  -d '{"ticker":"META","date":"2026-01-29"}' | jq
```

---

<p align="center">
  <a href="README.md">← Back to project overview</a>
  &nbsp;·&nbsp;
  <a href="README_DATABASE.md">Database setup →</a>
</p>
