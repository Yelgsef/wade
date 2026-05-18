import os
from pathlib import Path

import duckdb
import joblib
import pandas as pd


DB_PATH = Path(os.getenv("WADE_DUCKDB_PATH", "data/wade.duckdb"))
MODEL_PATH = Path(os.getenv("WADE_MODEL_PATH", "data/isolation_forest.joblib"))
OUTPUT_PATH = Path(os.getenv("WADE_ANOMALY_PATH", "data/weather_anomalies.parquet"))


def main() -> None:
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    features = bundle["features"]

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        df = con.execute("select * from gold_weather_feature_store").df()

    missing_features = sorted(set(features) - set(df.columns))
    if missing_features:
        raise RuntimeError(
            "Missing feature columns. Run dbt and retrain the model before scoring: "
            + ", ".join(missing_features)
        )

    scored = df.copy()
    scored["anomaly_score"] = model.decision_function(scored[features])
    scored["is_anomaly"] = model.predict(scored[features]) == -1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    scored.to_parquet(OUTPUT_PATH, index=False)
    print(f"Wrote {len(scored)} scored rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
