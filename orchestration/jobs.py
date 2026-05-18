from dagster import DefaultScheduleStatus, ScheduleDefinition, define_asset_job


weather_refresh_job = define_asset_job("weather_refresh_job")

hourly_weather_refresh_schedule = ScheduleDefinition(
    job=weather_refresh_job,
    cron_schedule="0 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
    default_status=DefaultScheduleStatus.RUNNING,
)
