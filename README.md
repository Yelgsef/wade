# WADE

Real-time Weather Anomaly Detection Engine for Vietnam weather data. The project follows the flow in `../docs/docs.md`:

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
  - `gold_weather_feature_store`: rolling 24h temperature, lag features, calendar features.
  - `gold_extreme_events_daily`: daily count of sudden temperature jumps, high wind, and heavy rain.
  - `gold_monthly_climate_delta`: year-over-year monthly temperature and humidity deltas.

## Setup

```bash
cd wade
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add `OPENWEATHER_API_KEY` to `.env` if you want current weather ingestion.

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
