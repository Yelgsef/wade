# WADE

Real-time Weather Anomaly Detection Engine for Vietnam weather data.

```text
External APIs -> Bronze Lake -> Silver Clean Tables -> Gold Analytical Tables -> Dashboard / ML
```

## Project Structure

```text
wade/
  configs/          Static configuration, city registry, DuckDB extension setup
  ingestion/        Python API collectors and Parquet writer
  lake/             Runtime data lake partitions: bronze/silver/gold
  dbt_wade/         DuckDB + dbt transformation project
  orchestration/    Dagster assets and jobs
  dashboard/        Streamlit dashboard
  ml/               Isolation Forest training and scoring scripts
  data/             Runtime DuckDB database and scored anomaly outputs
  models/           Runtime ML model artifacts
```

## Data Layers

- `lake/bronze/weather/source=.../year=YYYY/month=MM/day=DD/`: raw API payload normalized only enough to write Parquet, with `source` and `ingested_at`.
- `dbt_wade/models/silver/`: clean hourly weather observations, UTC timestamps, physical validity flags, and deduplication by `(city_id, timestamp_utc)`.
- `dbt_wade/models/gold/`: analytical outputs for dashboard and ML:
  - `gold_weather_feature_store`: hourly ML feature store with rolling weather baselines, lag and delta features, seasonal city/hour normal values, z-scores, cyclical time features, and source lineage.
  - `gold_extreme_events_daily`: daily count of sudden temperature jumps, high wind, and heavy rain.
  - `gold_monthly_climate_delta`: year-over-year monthly temperature and humidity deltas.

## Anomaly Detection

The anomaly model is an Isolation Forest trained on the `gold_weather_feature_store` table. Feature engineering is handled in dbt so the dashboard and ML code read from the same curated feature layer.

Current feature groups include:

- Current observations: temperature, humidity, pressure, wind speed, and rain.
- Rolling context: 24h temperature min/max/std/range, 24h rain totals, 24h humidity and pressure averages, and 7d temperature/wind baselines.
- Short-term movement: 1h and 2h temperature deltas, plus humidity, pressure, and wind deltas.
- Local seasonal context: city + month + hour averages and z-scores for temperature, humidity, pressure, wind, and rain.
- Calendar encoding: hour, day of week, month, weekend flag, and cyclical sine/cosine hour/month features.

Training uses median imputation, standard scaling, and a configurable anomaly rate:

```env
WADE_ANOMALY_CONTAMINATION=0.03
```

Model and scored anomaly outputs are runtime artifacts:

```text
models/isolation_forest.joblib
data/weather_anomalies.parquet
```

## Setup

```bash
cd wade
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add `OPENWEATHER_API_KEY` to `.env` if you want current weather ingestion.

Optional settings:

```env
WADE_BACKFILL_START_DATE=2025-01-01
WADE_ANOMALY_CONTAMINATION=0.03
```

## Run Locally

Backfill historical weather from Open-Meteo:

```bash
python -m ingestion.open_meteo_backfill --start-date 2024-01-01 --end-date 2024-01-31
```

Fetch current weather from OpenWeather:

```bash
python -m ingestion.openweather_current
```

Run dbt models:

```bash
cd dbt_wade
dbt run --profiles-dir .
```

Train and score the anomaly model:

```bash
python -m ml.train_isolation_forest
python -m ml.score_anomalies
```

Run orchestration and dashboard:

```bash
docker compose up
```

Dagster: <http://localhost:3000>

Streamlit: <http://localhost:8501>

MinIO API: <http://localhost:9000>

MinIO console: <http://localhost:9001>
