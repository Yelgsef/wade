{% macro minio_endpoint_host() -%}
    {{ env_var('MINIO_ENDPOINT', 'http://localhost:9000')
        | replace('http://', '')
        | replace('https://', '') }}
{%- endmacro %}

{% macro minio_use_ssl() -%}
    {{ 'true' if env_var('MINIO_ENDPOINT', 'http://localhost:9000').startswith('https://') else 'false' }}
{%- endmacro %}

{% macro configure_minio() %}
    {% if env_var('WADE_STORAGE_BACKEND', 'local') | lower == 'minio' %}
        INSTALL httpfs;
        LOAD httpfs;
        SET s3_endpoint='{{ minio_endpoint_host() }}';
        SET s3_access_key_id='{{ env_var("MINIO_ACCESS_KEY", "minioadmin") }}';
        SET s3_secret_access_key='{{ env_var("MINIO_SECRET_KEY", "minioadmin") }}';
        SET s3_region='{{ env_var("MINIO_REGION", "us-east-1") }}';
        SET s3_use_ssl={{ minio_use_ssl() }};
        SET s3_url_style='path';
    {% endif %}
{% endmacro %}
