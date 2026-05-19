import os
import time
from datetime import datetime, timezone

import requests
import pandas as pd

from ingestion.parquet_writer import write_partitioned_parquet


OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def safe_get_list(hourly: dict, key: str, length: int):
    values = hourly.get(key)

    if values is None:
        return [None] * length

    return values


def fetch_open_meteo_history(city, start_date: str, end_date: str):
    fetched_at_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "pressure_msl",
            "wind_speed_10m",
            "rain",
        ]),
        "wind_speed_unit": "ms",
        "timezone": "UTC",
    }

    max_attempts = int(os.getenv("WADE_OPEN_METEO_MAX_ATTEMPTS", "5"))
    base_delay_seconds = float(os.getenv("WADE_OPEN_METEO_RETRY_DELAY_SECONDS", "30"))

    for attempt in range(1, max_attempts + 1):
        response = requests.get(
            OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=60,
        )

        if response.status_code != 429:
            response.raise_for_status()
            break

        if attempt == max_attempts:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After")
        delay_seconds = (
            float(retry_after)
            if retry_after and retry_after.isdigit()
            else base_delay_seconds * attempt
        )
        print(f"  -> Rate limited by Open-Meteo. Retrying in {delay_seconds:.0f}s.")
        time.sleep(delay_seconds)

    payload = response.json()
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])

    temperatures = safe_get_list(hourly, "temperature_2m", len(times))
    humidities = safe_get_list(hourly, "relative_humidity_2m", len(times))
    pressures = safe_get_list(hourly, "pressure_msl", len(times))
    wind_speeds = safe_get_list(hourly, "wind_speed_10m", len(times))
    rains = safe_get_list(hourly, "rain", len(times))

    records = []

    for i, ts in enumerate(times):
        timestamp_utc = datetime.fromisoformat(ts)
        if timestamp_utc > fetched_at_utc:
            continue

        records.append({
            "timestamp": ts,
            "city_id": int(city["city_id"]),
            "city_name": city["city_name"],
            "lat": float(city["lat"]),
            "lon": float(city["lon"]),
            "temperature": temperatures[i],
            "humidity": humidities[i],
            "pressure": pressures[i],
            "wind_speed": wind_speeds[i],
            "rain": rains[i],
            "weather_condition": None,
        })

    return records


def run_backfill(
    cities_csv: str,
    output_base_path: str,
    start_date: str,
    end_date: str,
    sleep_seconds: float = 0.2,
):
    cities = pd.read_csv(cities_csv)

    all_records = []
    failed_cities = []

    for _, city in cities.iterrows():
        city_name = city["city_name"]
        print(f"Fetching {city_name} from {start_date} to {end_date}")

        try:
            records = fetch_open_meteo_history(city, start_date, end_date)
            print(f"  -> {len(records)} records")
            all_records.extend(records)

        except Exception as exc:
            print(f"  -> Failed for {city_name}: {exc}")
            failed_cities.append(city_name)

        time.sleep(sleep_seconds)

    if failed_cities:
        raise RuntimeError(
            "Open-Meteo backfill failed for cities: " + ", ".join(failed_cities)
        )

    return write_partitioned_parquet(
        all_records,
        base_path=output_base_path,
        source="open_meteo",
    )


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--cities-csv", default="configs/cities_vietnam.csv")
    parser.add_argument("--output-base-path", default=os.getenv("WADE_LAKE_PATH", "lake"))
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--end-date", default="2025-01-07")
    args = parser.parse_args()

    run_backfill(
        cities_csv=args.cities_csv,
        output_base_path=args.output_base_path,
        start_date=args.start_date,
        end_date=args.end_date,
    )
