import time
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

    response = requests.get(
        OPEN_METEO_ARCHIVE_URL,
        params=params,
        timeout=60,
    )
    response.raise_for_status()

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

    for _, city in cities.iterrows():
        city_name = city["city_name"]
        print(f"Fetching {city_name} from {start_date} to {end_date}")

        try:
            records = fetch_open_meteo_history(city, start_date, end_date)
            print(f"  -> {len(records)} records")
            all_records.extend(records)

        except Exception as exc:
            print(f"  -> Failed for {city_name}: {exc}")

        time.sleep(sleep_seconds)

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
