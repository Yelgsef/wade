{% if env_var("WADE_STORAGE_BACKEND", "local") | lower == "minio" %}
    {% set weather_path = "s3://" ~ env_var("MINIO_BUCKET", "wade-lake") ~ "/bronze/weather/**/*.parquet" %}
{% else %}
    {% set weather_path = env_var("WADE_LAKE_PATH", "../lake") ~ "/bronze/weather/**/*.parquet" %}
{% endif %}

select
    *
from read_parquet(
    '{{ weather_path }}',
    union_by_name = true
)
