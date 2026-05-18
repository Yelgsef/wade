select
    *
from read_parquet(
    '{{ env_var("WADE_LAKE_PATH", "../lake") }}/bronze/weather/**/*.parquet',
    union_by_name = true
)
