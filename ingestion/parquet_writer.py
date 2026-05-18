from pathlib import Path
from datetime import datetime, timezone
import pyarrow as pa
import pyarrow.parquet as pq


def write_partitioned_parquet(records, base_path: str, source: str):
    if not records:
        print("No records to write.")
        return None

    now = datetime.now(timezone.utc)

    for row in records:
        row["source"] = source
        row["ingested_at"] = now.isoformat()
        row["ingestion_year"] = now.year
        row["ingestion_month"] = now.month
        row["ingestion_day"] = now.day

    table = pa.Table.from_pylist(records)

    output_dir = (
        Path(base_path)
        / "bronze"
        / "weather"
        / f"source={source}"
        / f"year={now.year}"
        / f"month={now.month:02d}"
        / f"day={now.day:02d}"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"weather_{now.strftime('%Y%m%d_%H%M%S')}.parquet"

    pq.write_table(table, output_file)

    print(f"Wrote {len(records)} records to {output_file}")
    return str(output_file)