<h1 align="center">Database Layer</h1>

<p align="center">
  <strong>PostgreSQL / Neon — schema, migrations, and CSV ingestion</strong><br />
  <em>Persistent storage for production; CSV remains available as a local fallback.</em>
</p>

<p align="center">
  <a href="README.md">← Project overview</a>
  &nbsp;·&nbsp;
  <a href="README_API.md">API reference →</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ORM-SQLAlchemy_2.0-red?logo=sqlalchemy" alt="SQLAlchemy" />
  <img src="https://img.shields.io/badge/Migrations-Alembic-4169E1" alt="Alembic" />
  <img src="https://img.shields.io/badge/Driver-psycopg_3-4169E1?logo=postgresql&logoColor=white" alt="psycopg3" />
</p>

---

## Table of contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick setup](#quick-setup)
- [Data source modes](#data-source-modes)
- [Schema](#schema)
- [CSV mapping](#csv-mapping)
- [Loader script](#loader-script)
- [API integration](#api-integration)
- [Operations](#operations)
- [Troubleshooting](#troubleshooting)

---

## Overview

The database layer adds **PostgreSQL (Neon)** as the primary data store for the FastAPI API. Research artifacts stay in `data/*.csv`; a one-time (or scheduled) loader hydrates Neon for low-latency SQL reads in production.

```mermaid
flowchart LR
  CSV[data/*.csv]
  LOAD[scripts/load_csv_to_db.py]
  NEON[(Neon PostgreSQL)]
  API[app.main:app]
  CSV --> LOAD --> NEON
  NEON --> API
  CSV -.->|DATA_SOURCE=csv| API
```

| Component | Path |
|-----------|------|
| ORM models | `app/models/database_models.py` |
| Migrations | `alembic/versions/` |
| Repository | `app/repositories/db_repository.py` |
| Loader | `scripts/load_csv_to_db.py` |
| Resolver | `app/core/data_source.py` |

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Python 3.11+ | Same as API |
| `DATABASE_URL` | Neon connection string in `.env` or Render secrets |
| Dependencies | `pip install -r requirements.txt` |

**Connection string format**

```env
DATABASE_URL=postgresql+psycopg://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

> The app normalizes `postgres://` and `postgresql://` URLs to `postgresql+psycopg://` automatically.

---

## Quick setup

### Step 1 — Environment

```bash
cp .env.example .env
# Set DATABASE_URL and optionally DATA_SOURCE=database
```

### Step 2 — Migrations

```bash
alembic upgrade head
```

Creates all tables defined in the initial migration (`20260521_0001_initial_schema.py`).

### Step 3 — Load data

```bash
python scripts/load_csv_to_db.py --truncate
```

Expected output includes row counts per table (e.g. ~27k `anomaly_results` rows).

### Step 4 — Run API and verify

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
curl -s http://localhost:8000/health | jq
```

Success indicators:

```json
{
  "data_source": "database",
  "database_connected": true,
  "database_populated": true
}
```

---

## Data source modes

Set `DATA_SOURCE` in `.env` or Render:

| Value | Behaviour |
|-------|-----------|
| `auto` | Use DB when connected **and** `anomaly_results` has rows; otherwise CSV |
| `database` | Prefer PostgreSQL; fall back to CSV if DB unavailable |
| `csv` | Always read from `data/*.csv` |

**Recommendation for Render:** `DATA_SOURCE=database` once Neon is loaded.

After a full reload, restart the API or call `clear_data_source_cache()` via a redeploy so `auto` re-resolves the active source.

---

## Schema

### Tables

| Table | Purpose | Used by API at runtime |
|-------|---------|------------------------|
| `companies` | Ticker metadata (name, CIK) | Loader only |
| `market_features` | Daily OHLCV-derived features | Loader only |
| `filing_features` | SEC filing activity features | Loader only |
| `financial_features` | XBRL / ratio features | Loader only |
| `anomaly_results` | Scored anomaly rows | **Yes — primary API table** |
| `sec_filings` | Cleaned filing records | Loader only |
| `ai_briefings` | Cached Groq outputs (optional) | Schema ready; not wired yet |

### `anomaly_results` (API-facing)

Key columns exposed to endpoints:

| Column | Description |
|--------|-------------|
| `ticker` | Uppercase symbol |
| `date` | Observation date |
| `anomaly_score` | Isolation Forest score (lower = more anomalous) |
| `anomaly_label` | `-1` / `1` |
| `is_anomaly` | Boolean flag for clients |
| `anomaly_type` | Rule-based signal tags |
| `daily_return`, `volume_zscore_30d`, … | Context features for briefings |

Indexes: `(ticker, date)` unique, `is_anomaly`, `anomaly_score`.

---

## CSV mapping

| PostgreSQL table | Source CSV | Notes |
|------------------|------------|--------|
| `companies` | `clean_company_metadata.csv` | Plus tickers from `anomaly_detection_results.csv` |
| `market_features` | `market_features.csv` | Upsert on `(ticker, date)` |
| `filing_features` | `filing_features.csv` | Upsert on `(ticker, date)` |
| `financial_features` | `financial_features_selected.csv` | Key: `(ticker, reference_date)` |
| `anomaly_results` | `anomaly_detection_results.csv` | **Required for API DB mode** |
| `sec_filings` | `clean_sec_filings.csv` | Upsert on ticker + accession + form |

---

## Loader script

**Full reload (truncate all tables)**

```bash
python scripts/load_csv_to_db.py --truncate
```

**Selected tables only**

```bash
python scripts/load_csv_to_db.py --only companies anomaly_results
```

**Available table keys**

`companies` · `market_features` · `filing_features` · `financial_features` · `anomaly_results` · `sec_filings`

| Flag | Effect |
|------|--------|
| `--truncate` | `TRUNCATE … CASCADE` before insert |
| `--only` | Load comma-separated subset |

The loader uses batched PostgreSQL `INSERT … ON CONFLICT` upserts (batch size 1000).

---

## API integration

When `data_source` is `database`:

| Concern | Implementation |
|---------|----------------|
| Hot reads | SQL in `db_repository.py` — no full-table pandas per request |
| Startup | `fetch_anomaly_minimal_dataframe()` builds in-memory caches once |
| Queries | `query_anomalies`, `find_anomaly_record`, `get_company_anomaly_records` |
| Health | `database_connected`, `database_populated`, `data_source` |

Existing REST routes are unchanged; only the backing store switches between CSV and SQL.

---

## Operations

### Re-sync after notebook refresh

```bash
# 1. Regenerate CSVs in notebooks
# 2. Reload Neon
python scripts/load_csv_to_db.py --truncate
# 3. Redeploy or restart API on Render
```

### New migration

```bash
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

### Local dev without Neon

Omit `DATABASE_URL` or set `DATA_SOURCE=csv`. The API reads from `data/` automatically.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `data_source: "csv"` in production | Missing `DATABASE_URL` or empty `anomaly_results` | Set secret; run loader |
| `database_connected: false` | Wrong URL, SSL, or network | Verify Neon string; use `sslmode=require` |
| `database_populated: false` | Migrations OK but no data | Run `load_csv_to_db.py` |
| Briefing 404 for ticker/date | Row not in `anomaly_results` | Check date format `YYYY-MM-DD` |
| DetachedInstanceError (historical) | ORM read outside session | Fixed in repository — pull latest `app/` |

---

<p align="center">
  <a href="README.md">← Back to project overview</a>
  &nbsp;·&nbsp;
  <a href="README_API.md">API reference →</a>
</p>
