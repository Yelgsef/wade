import os
import time
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

from minio import Minio
import pyarrow as pa
import pyarrow.parquet as pq


def minio_client() -> Minio:
    endpoint = os.getenv("MINIO_INTERNAL_ENDPOINT") or os.getenv(
        "MINIO_ENDPOINT", "http://localhost:9000"
    )
    parsed = urlparse(endpoint)
    endpoint_host = parsed.netloc or parsed.path

    return Minio(
        endpoint_host,
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=(parsed.scheme == "https"),
        region=os.getenv("MINIO_REGION", "us-east-1"),
    )


def partition_key(source: str, now: datetime) -> str:
    return (
        "bronze"
        f"/weather/source={source}"
        f"/year={now.year}"
        f"/month={now.month:02d}"
        f"/day={now.day:02d}"
        f"/weather_{now.strftime('%Y%m%d_%H%M%S_%f')}.parquet"
    )


def write_minio_parquet(table: pa.Table, source: str, now: datetime) -> str:
    bucket = os.getenv("MINIO_BUCKET", "wade-lake")
    key = partition_key(source, now)
    max_attempts = int(os.getenv("MINIO_WRITE_MAX_ATTEMPTS", "5"))
    retry_delay_seconds = float(os.getenv("MINIO_WRITE_RETRY_DELAY_SECONDS", "5"))

    for attempt in range(1, max_attempts + 1):
        try:
            buffer = BytesIO()
            pq.write_table(table, buffer)
            buffer.seek(0)

            client = minio_client()
            client.put_object(
                bucket,
                key,
                buffer,
                length=buffer.getbuffer().nbytes,
                content_type="application/vnd.apache.parquet",
            )
            break
        except Exception:
            if attempt == max_attempts:
                raise
            time.sleep(retry_delay_seconds)

    return f"s3://{bucket}/{key}"


def write_local_parquet(table: pa.Table, base_path: str, source: str, now: datetime) -> str:
    key = partition_key(source, now)
    output_file = Path(base_path) / key
    output_file.parent.mkdir(parents=True, exist_ok=True)

    pq.write_table(table, output_file)

    return str(output_file)


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
    storage_backend = os.getenv("WADE_STORAGE_BACKEND", "local").lower()

    if storage_backend == "minio":
        output_file = write_minio_parquet(table, source, now)
    elif storage_backend == "local":
        output_file = write_local_parquet(table, base_path, source, now)
    else:
        raise ValueError(
            "Unsupported WADE_STORAGE_BACKEND. Expected 'local' or 'minio', "
            f"got '{storage_backend}'."
        )

    print(f"Wrote {len(records)} records to {output_file}")
    return output_file
