from dagster import DefaultScheduleStatus, ScheduleDefinition, define_asset_job


weather_refresh_job = define_asset_job(
    "weather_refresh_job",
    selection=["openweather_current_raw", "dbt_models"],
)

weather_backfill_job = define_asset_job(
    "weather_backfill_job",
    selection=["open_meteo_backfill_raw", "dbt_models"],
)

hourly_weather_refresh_schedule = ScheduleDefinition(
    job=weather_refresh_job,
    cron_schedule="0 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
    default_status=DefaultScheduleStatus.RUNNING,
)
