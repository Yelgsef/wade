from dagster import Definitions

from orchestration.assets import dbt_models, open_meteo_backfill_raw, openweather_current_raw
from orchestration.jobs import hourly_weather_refresh_schedule, weather_refresh_job


defs = Definitions(
    assets=[openweather_current_raw, open_meteo_backfill_raw, dbt_models],
    jobs=[weather_refresh_job],
    schedules=[hourly_weather_refresh_schedule],
)
