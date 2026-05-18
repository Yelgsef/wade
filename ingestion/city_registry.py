from pathlib import Path

import pandas as pd


DEFAULT_CITY_PATH = Path(__file__).resolve().parents[1] / "configs" / "cities_vietnam.csv"


def load_cities(path: str | Path = DEFAULT_CITY_PATH) -> pd.DataFrame:
    cities = pd.read_csv(path)
    expected = {"city_id", "city_name", "lat", "lon"}
    missing = expected.difference(cities.columns)
    if missing:
        raise ValueError(f"Missing required city columns: {sorted(missing)}")
    return cities
