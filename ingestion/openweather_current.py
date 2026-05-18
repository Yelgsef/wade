import os
import time
from pathlib import Path

import pandas as pd
import requests

from ingestion.city_registry import load_cities
from ingestion.parquet_writer import write_partitioned_parquet


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_SLEEP_SECONDS = 1.5
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def load_local_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def fetch_current_weather(api_key: str) -> pd.DataFrame:
    rows = []
    for _, city in load_cities().iterrows():
        params = {
            "lat": city["lat"],
            "lon": city["lon"],
            "appid": api_key,
            "units": "metric",
        }
        response = requests.get(OPENWEATHER_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        rows.append(
            {
                "timestamp": pd.to_datetime(payload["dt"], unit="s", utc=True).isoformat(),
                "city_id": int(city["city_id"]),
                "city_name": city["city_name"],
                "lat": float(city["lat"]),
                "lon": float(city["lon"]),
                "temperature": payload["main"].get("temp"),
                "humidity": payload["main"].get("humidity"),
                "pressure": payload["main"].get("pressure"),
                "wind_speed": payload.get("wind", {}).get("speed"),
                "rain": payload.get("rain", {}).get("1h", 0.0),
                "weather_condition": payload.get("weather", [{}])[0].get("main"),
            }
        )
        time.sleep(REQUEST_SLEEP_SECONDS)
    return pd.DataFrame(rows)


def main() -> None:
    load_local_env()
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENWEATHER_API_KEY before fetching current weather.")

    df = fetch_current_weather(api_key)
    path = write_partitioned_parquet(
        df.to_dict("records"),
        base_path=os.getenv("WADE_LAKE_PATH", "lake"),
        source="openweather",
    )
    print(f"Wrote {len(df)} rows to {path}")


if __name__ == "__main__":
    main()
