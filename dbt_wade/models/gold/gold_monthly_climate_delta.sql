with monthly as (
    select
        city_id,
        city_name,
        date_trunc('month', timestamp_utc) as observed_month,
        avg(temperature_c) as avg_temp_c,
        avg(humidity_pct) as avg_humidity_pct,
        sum(rain_mm) as total_rain_mm
    from {{ ref('silver_weather_clean') }}
    where not is_quality_anomaly
    group by 1, 2, 3
)

select
    city_id,
    city_name,
    observed_month,
    avg_temp_c,
    avg_temp_c - lag(avg_temp_c, 12) over (
        partition by city_id
        order by observed_month
    ) as temp_delta_yoy_c,
    avg_humidity_pct,
    avg_humidity_pct - lag(avg_humidity_pct, 12) over (
        partition by city_id
        order by observed_month
    ) as humidity_delta_yoy_pct,
    total_rain_mm
from monthly
