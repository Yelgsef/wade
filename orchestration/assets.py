import os
import subprocess
from datetime import date

from dagster import AssetExecutionContext, RetryPolicy, asset

from ingestion.open_meteo_backfill import run_backfill
from ingestion.openweather_current import main as fetch_openweather_current


@asset(retry_policy=RetryPolicy(max_retries=3, delay=300))
def openweather_current_raw(context: AssetExecutionContext) -> str:
    fetch_openweather_current()
    context.log.info("Fetched current OpenWeather data into bronze lake.")
    return os.getenv("WADE_LAKE_PATH", "lake")


@asset(retry_policy=RetryPolicy(max_retries=3, delay=300))
def open_meteo_backfill_raw(context: AssetExecutionContext) -> str:
    start_date = os.getenv("WADE_BACKFILL_START_DATE", "2025-01-01")
    end_date = os.getenv("WADE_BACKFILL_END_DATE", date.today().isoformat())
    run_backfill(
        cities_csv="configs/cities_vietnam.csv",
        output_base_path=os.getenv("WADE_LAKE_PATH", "lake"),
        start_date=start_date,
        end_date=end_date,
    )
    context.log.info("Backfilled hourly Open-Meteo data from %s to %s.", start_date, end_date)
    return os.getenv("WADE_LAKE_PATH", "lake")


@asset(deps=[openweather_current_raw, open_meteo_backfill_raw])
def dbt_models(context: AssetExecutionContext) -> None:
    result = subprocess.run(
        ["dbt", "run", "--project-dir", "dbt_wade", "--profiles-dir", "dbt_wade"],
        check=True,
        capture_output=True,
        text=True,
    )
    context.log.info(result.stdout)
