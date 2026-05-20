with hourly_events as (
    select
        city_id,
        city_name,
        lat,
        lon,
        observed_date,
        timestamp_utc,
        temperature_c,
        wind_speed_ms,
        rain_mm,
        temperature_c - temp_lag_2h > 5 as sudden_temp_jump,
        wind_speed_ms > rolling_avg_wind_7d * 3 as high_wind_vs_week,
        rain_mm >= 50 as heavy_rain_hour
    from {{ ref('gold_weather_feature_store') }}
)

select
    city_id,
    city_name,
    lat,
    lon,
    observed_date,
    count_if(sudden_temp_jump) as sudden_temp_jump_count,
    count_if(high_wind_vs_week) as high_wind_count,
    count_if(heavy_rain_hour) as heavy_rain_count,
    count_if(sudden_temp_jump or high_wind_vs_week or heavy_rain_hour) as extreme_event_count,
    max(temperature_c) as max_temperature_c,
    max(wind_speed_ms) as max_wind_speed_ms,
    sum(rain_mm) as total_rain_mm
from hourly_events
group by 1, 2, 3, 4, 5
having extreme_event_count > 0
