with normalized as (
    select
        cast(city_id as integer) as city_id,
        cast(city_name as varchar) as city_name,
        cast(lat as double) as lat,
        cast(lon as double) as lon,
        try_cast(timestamp as timestamp) as timestamp_utc,
        try_cast(temperature as double) as temperature_c,
        try_cast(humidity as double) as humidity_pct,
        try_cast(pressure as double) as pressure_hpa,
        try_cast(wind_speed as double) as wind_speed_ms,
        coalesce(try_cast(rain as double), 0.0) as rain_mm,
        cast(weather_condition as varchar) as weather_condition,
        cast(source as varchar) as source,
        try_cast(ingested_at as timestamp) as ingested_at_utc
    from {{ ref('stg_raw_weather') }}
),

quality_checked as (
    select
        *,
        temperature_c < -10 or temperature_c > 60 as invalid_temperature,
        humidity_pct < 0 or humidity_pct > 100 as invalid_humidity,
        rain_mm < 0 or rain_mm > 1000 as invalid_rain,
        wind_speed_ms < 0 or wind_speed_ms > 80 as invalid_wind_speed
    from normalized
    where city_id is not null
      and timestamp_utc is not null
),

deduped as (
    select
        *,
        row_number() over (
            partition by city_id, timestamp_utc
            order by ingested_at_utc desc nulls last
        ) as row_num
    from quality_checked
)

select
    city_id,
    city_name,
    lat,
    lon,
    timestamp_utc,
    date_trunc('hour', timestamp_utc) as observed_hour_utc,
    cast(timestamp_utc as date) as observed_date,
    temperature_c,
    humidity_pct,
    pressure_hpa,
    wind_speed_ms,
    rain_mm,
    weather_condition,
    source,
    ingested_at_utc,
    invalid_temperature,
    invalid_humidity,
    invalid_rain,
    invalid_wind_speed,
    invalid_temperature
        or invalid_humidity
        or invalid_rain
        or invalid_wind_speed as is_quality_anomaly
from deduped
where row_num = 1
