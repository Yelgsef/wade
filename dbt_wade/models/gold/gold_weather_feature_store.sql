with clean as (
    select *
    from {{ ref('silver_weather_clean') }}
    where not is_quality_anomaly
),

features as (
    select
        city_id,
        city_name,
        lat,
        lon,
        timestamp_utc,
        observed_hour_utc,
        observed_date,
        temperature_c,
        humidity_pct,
        pressure_hpa,
        wind_speed_ms,
        rain_mm,
        weather_condition,
        source,
        avg(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_avg_temp_24h,
        var_samp(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_var_temp_24h,
        lag(temperature_c, 1) over (
            partition by city_id
            order by timestamp_utc
        ) as temp_lag_1h,
        lag(temperature_c, 2) over (
            partition by city_id
            order by timestamp_utc
        ) as temp_lag_2h,
        avg(wind_speed_ms) over (
            partition by city_id
            order by timestamp_utc
            rows between 167 preceding and current row
        ) as rolling_avg_wind_7d,
        extract(hour from timestamp_utc) as hour_of_day,
        extract(month from timestamp_utc) as month,
        extract(dow from timestamp_utc) in (0, 6) as is_weekend
    from clean
)

select *
from features
