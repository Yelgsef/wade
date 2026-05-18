import os
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib


DB_PATH = Path(os.getenv("WADE_DUCKDB_PATH", "data/wade.duckdb"))
MODEL_PATH = Path(os.getenv("WADE_MODEL_PATH", "data/isolation_forest.joblib"))
CONTAMINATION = float(os.getenv("WADE_ANOMALY_CONTAMINATION", "0.03"))
FEATURES = [
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_ms",
    "rain_mm",
    "rolling_avg_temp_24h",
    "rolling_min_temp_24h",
    "rolling_max_temp_24h",
    "rolling_std_temp_24h",
    "rolling_var_temp_24h",
    "rolling_avg_temp_7d",
    "rolling_std_temp_7d",
    "temp_lag_1h",
    "temp_lag_2h",
    "humidity_lag_1h",
    "pressure_lag_1h",
    "wind_lag_1h",
    "rolling_avg_humidity_24h",
    "rolling_avg_pressure_24h",
    "rolling_avg_rain_24h",
    "rolling_sum_rain_24h",
    "rolling_max_rain_24h",
    "rolling_avg_wind_7d",
    "rolling_std_wind_7d",
    "temp_delta_1h",
    "temp_delta_2h",
    "humidity_delta_1h",
    "pressure_delta_1h",
    "wind_delta_1h",
    "temp_vs_24h_avg",
    "temp_vs_7d_avg",
    "humidity_vs_24h_avg",
    "pressure_vs_24h_avg",
    "wind_vs_7d_avg",
    "temp_range_24h",
    "dew_point_c",
    "temp_vs_city_month_hour_avg",
    "temp_city_month_hour_zscore",
    "humidity_city_month_hour_zscore",
    "pressure_city_month_hour_zscore",
    "wind_city_month_hour_zscore",
    "rain_city_month_hour_zscore",
    "hour_of_day",
    "day_of_week",
    "month",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]


def load_training_data() -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute("select * from gold_weather_feature_store").df()


def main() -> None:
    df = load_training_data()
    missing_features = sorted(set(FEATURES) - set(df.columns))
    if missing_features:
        raise RuntimeError(
            "Missing feature columns. Run dbt before training: "
            + ", ".join(missing_features)
        )

    training_df = df[FEATURES].copy()
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "forest",
                IsolationForest(
                    contamination=CONTAMINATION,
                    n_estimators=300,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(training_df)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES}, MODEL_PATH)
    print(
        f"Wrote model to {MODEL_PATH} "
        f"using {len(training_df)} rows and {len(FEATURES)} features"
    )


if __name__ == "__main__":
    main()
