from dagster import Definitions

from orchestration.assets import (
    dbt_models_after_backfill,
    dbt_models_after_current,
    open_meteo_backfill_raw,
    openweather_current_raw,
)
from orchestration.jobs import (
    hourly_weather_refresh_schedule,
    weather_backfill_job,
    weather_refresh_job,
)


defs = Definitions(
    assets=[
        openweather_current_raw,
        open_meteo_backfill_raw,
        dbt_models_after_current,
        dbt_models_after_backfill,
    ],
    jobs=[weather_refresh_job, weather_backfill_job],
    schedules=[hourly_weather_refresh_schedule],
)
