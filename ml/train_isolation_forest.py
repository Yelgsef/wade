import os
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib


DB_PATH = Path(os.getenv("WADE_DUCKDB_PATH", "data/wade.duckdb"))
MODEL_PATH = Path(os.getenv("WADE_MODEL_PATH", "data/isolation_forest.joblib"))
FEATURES = [
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_ms",
    "rain_mm",
    "rolling_avg_temp_24h",
    "rolling_var_temp_24h",
    "temp_lag_1h",
    "hour_of_day",
    "month",
]


def load_training_data() -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute("select * from gold_weather_feature_store").df()


def main() -> None:
    df = load_training_data().dropna(subset=FEATURES)
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("forest", IsolationForest(contamination=0.05, random_state=42)),
        ]
    )
    model.fit(df[FEATURES])
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES}, MODEL_PATH)
    print(f"Wrote model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
