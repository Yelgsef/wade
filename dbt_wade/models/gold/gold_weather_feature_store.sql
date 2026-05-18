with clean as (
    select *
    from {{ ref('silver_weather_clean') }}
    where not is_quality_anomaly
),

windowed as (
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
        min(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_min_temp_24h,
        max(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_max_temp_24h,
        stddev_samp(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_std_temp_24h,
        var_samp(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_var_temp_24h,
        avg(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 167 preceding and current row
        ) as rolling_avg_temp_7d,
        stddev_samp(temperature_c) over (
            partition by city_id
            order by timestamp_utc
            rows between 167 preceding and current row
        ) as rolling_std_temp_7d,
        lag(temperature_c, 1) over (
            partition by city_id
            order by timestamp_utc
        ) as temp_lag_1h,
        lag(temperature_c, 2) over (
            partition by city_id
            order by timestamp_utc
        ) as temp_lag_2h,
        lag(humidity_pct, 1) over (
            partition by city_id
            order by timestamp_utc
        ) as humidity_lag_1h,
        lag(pressure_hpa, 1) over (
            partition by city_id
            order by timestamp_utc
        ) as pressure_lag_1h,
        lag(wind_speed_ms, 1) over (
            partition by city_id
            order by timestamp_utc
        ) as wind_lag_1h,
        avg(humidity_pct) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_avg_humidity_24h,
        avg(pressure_hpa) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_avg_pressure_24h,
        avg(rain_mm) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_avg_rain_24h,
        sum(rain_mm) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_sum_rain_24h,
        max(rain_mm) over (
            partition by city_id
            order by timestamp_utc
            rows between 23 preceding and current row
        ) as rolling_max_rain_24h,
        avg(wind_speed_ms) over (
            partition by city_id
            order by timestamp_utc
            rows between 167 preceding and current row
        ) as rolling_avg_wind_7d,
        stddev_samp(wind_speed_ms) over (
            partition by city_id
            order by timestamp_utc
            rows between 167 preceding and current row
        ) as rolling_std_wind_7d,
        extract(hour from timestamp_utc) as hour_of_day,
        extract(month from timestamp_utc) as month,
        extract(dow from timestamp_utc) as day_of_week,
        case
            when extract(dow from timestamp_utc) in (0, 6) then 1
            else 0
        end as is_weekend,
        sin(2 * pi() * extract(hour from timestamp_utc) / 24.0) as hour_sin,
        cos(2 * pi() * extract(hour from timestamp_utc) / 24.0) as hour_cos,
        sin(2 * pi() * extract(month from timestamp_utc) / 12.0) as month_sin,
        cos(2 * pi() * extract(month from timestamp_utc) / 12.0) as month_cos,
        avg(temperature_c) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_avg_temp,
        stddev_samp(temperature_c) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_std_temp,
        avg(humidity_pct) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_avg_humidity,
        stddev_samp(humidity_pct) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_std_humidity,
        avg(pressure_hpa) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_avg_pressure,
        stddev_samp(pressure_hpa) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_std_pressure,
        avg(wind_speed_ms) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_avg_wind,
        stddev_samp(wind_speed_ms) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_std_wind,
        avg(rain_mm) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_avg_rain,
        stddev_samp(rain_mm) over (
            partition by city_id, extract(month from timestamp_utc), extract(hour from timestamp_utc)
        ) as city_month_hour_std_rain
    from clean
),

features as (
    select
        *,
        temperature_c - temp_lag_1h as temp_delta_1h,
        temperature_c - temp_lag_2h as temp_delta_2h,
        humidity_pct - humidity_lag_1h as humidity_delta_1h,
        pressure_hpa - pressure_lag_1h as pressure_delta_1h,
        wind_speed_ms - wind_lag_1h as wind_delta_1h,
        temperature_c - rolling_avg_temp_24h as temp_vs_24h_avg,
        temperature_c - rolling_avg_temp_7d as temp_vs_7d_avg,
        humidity_pct - rolling_avg_humidity_24h as humidity_vs_24h_avg,
        pressure_hpa - rolling_avg_pressure_24h as pressure_vs_24h_avg,
        wind_speed_ms - rolling_avg_wind_7d as wind_vs_7d_avg,
        rolling_max_temp_24h - rolling_min_temp_24h as temp_range_24h,
        temperature_c - ((100 - humidity_pct) / 5.0) as dew_point_c,
        temperature_c - city_month_hour_avg_temp
            as temp_vs_city_month_hour_avg,
        (temperature_c - city_month_hour_avg_temp)
            / nullif(city_month_hour_std_temp, 0) as temp_city_month_hour_zscore,
        (humidity_pct - city_month_hour_avg_humidity)
            / nullif(city_month_hour_std_humidity, 0) as humidity_city_month_hour_zscore,
        (pressure_hpa - city_month_hour_avg_pressure)
            / nullif(city_month_hour_std_pressure, 0) as pressure_city_month_hour_zscore,
        (wind_speed_ms - city_month_hour_avg_wind)
            / nullif(city_month_hour_std_wind, 0) as wind_city_month_hour_zscore,
        (rain_mm - city_month_hour_avg_rain)
            / nullif(city_month_hour_std_rain, 0) as rain_city_month_hour_zscore
    from windowed
)

select *
from features
