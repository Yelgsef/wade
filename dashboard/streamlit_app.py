import os
from datetime import timedelta
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


DB_PATH = Path(os.getenv("WADE_DUCKDB_PATH", "data/wade.duckdb"))
LOCAL_TIMEZONE = "Asia/Ho_Chi_Minh"
LOCAL_TIME_LABEL = "ICT"


st.set_page_config(page_title="WADE Weather Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
    [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #243244;
        border-radius: 8px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] {
        color: #a7b0bd;
    }
    [data-testid="stMetricValue"] {
        color: #f8fafc;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #243244;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading weather features")
def load_features(db_mtime_ns: int) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(
            """
            select
                city_id,
                city_name,
                lat,
                lon,
                timestamp_utc,
                observed_date,
                temperature_c,
                humidity_pct,
                pressure_hpa,
                wind_speed_ms,
                rain_mm,
                weather_condition,
                source,
                rolling_avg_temp_24h,
                rolling_var_temp_24h,
                temp_lag_1h,
                temp_lag_2h,
                rolling_avg_wind_7d,
                hour_of_day,
                month,
                is_weekend
            from gold_weather_feature_store
            order by timestamp_utc
            """
        ).df()


@st.cache_data(show_spinner="Loading extreme events")
def load_extreme_events(db_mtime_ns: int) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(
            """
            select *
            from gold_extreme_events_daily
            order by observed_date
            """
        ).df()


def format_number(value: float, suffix: str = "", decimals: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}{suffix}"


def latest_delta(frame: pd.DataFrame, column: str) -> str | None:
    values = frame[column].dropna()
    if len(values) < 2:
        return None
    delta = values.iloc[-1] - values.iloc[-2]
    return format_number(delta, " vs prev", 1)


db_mtime_ns = DB_PATH.stat().st_mtime_ns if DB_PATH.exists() else 0

df = load_features(db_mtime_ns)
if df.empty:
    st.title("WADE Weather Dashboard")
    st.info("No modeled weather data yet. Run ingestion and dbt first.")
    st.stop()

events = load_extreme_events(db_mtime_ns)
df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
df["timestamp_ict"] = (
    df["timestamp_utc"].dt.tz_convert(LOCAL_TIMEZONE).dt.tz_localize(None)
)
df["observed_date_ict"] = df["timestamp_ict"].dt.date
df["rain_mm"] = df["rain_mm"].fillna(0)

if not events.empty:
    events["observed_date_ict"] = pd.to_datetime(events["observed_date"]).dt.date

min_date = df["observed_date_ict"].min()
max_date = df["observed_date_ict"].max()
default_start = max(min_date, max_date - timedelta(days=30))

with st.sidebar:
    st.header("Filters")
    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()

    cities = sorted(df["city_name"].dropna().unique())
    default_city_index = cities.index("Ha Noi") if "Ha Noi" in cities else 0
    selected_city = st.selectbox("City", cities, index=default_city_index)

    start_date = st.date_input(
        "Start date",
        value=default_start,
        min_value=min_date,
        max_value=max_date,
    )
    end_date = st.date_input(
        "End date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

    sources = sorted(df["source"].dropna().unique())
    selected_sources = st.multiselect("Sources", sources, default=sources)

    st.divider()
    st.caption(f"Rows: {len(df):,}")
    st.caption(
        f"Updated: {df['timestamp_ict'].max():%Y-%m-%d %H:%M} {LOCAL_TIME_LABEL}"
    )

if start_date > end_date:
    st.warning("Start date is after end date, so the dates were swapped.")
    start_date, end_date = end_date, start_date

filtered = df[
    (df["observed_date_ict"] >= start_date)
    & (df["observed_date_ict"] <= end_date)
    & (df["source"].isin(selected_sources))
].copy()

city_df = filtered[filtered["city_name"] == selected_city].copy()
if city_df.empty:
    st.title("WADE Weather Dashboard")
    st.info("No data for this filter.")
    st.stop()

latest = city_df.iloc[-1]
previous_day = city_df[
    city_df["timestamp_ict"] >= latest["timestamp_ict"] - pd.Timedelta(hours=24)
]
period_events = pd.DataFrame()
if not events.empty:
    period_events = events[
        (events["observed_date_ict"] >= start_date)
        & (events["observed_date_ict"] <= end_date)
    ].copy()

st.title("WADE Weather Dashboard")
st.caption(
    f"{selected_city} | {start_date} to {end_date} | "
    f"{len(city_df):,} hourly observations | times shown in {LOCAL_TIME_LABEL}"
)

metric_cols = st.columns(5)
metric_cols[0].metric(
    "Latest temp",
    format_number(latest["temperature_c"], " C"),
    latest_delta(city_df, "temperature_c"),
)
metric_cols[1].metric(
    "24h average",
    format_number(latest["rolling_avg_temp_24h"], " C"),
)
metric_cols[2].metric(
    "Rain in range",
    format_number(city_df["rain_mm"].sum(), " mm"),
)
metric_cols[3].metric(
    "Peak wind",
    format_number(city_df["wind_speed_ms"].max(), " m/s"),
)
metric_cols[4].metric(
    "Humidity",
    format_number(latest["humidity_pct"], "%"),
    latest_delta(city_df, "humidity_pct"),
)

overview_tab, trends_tab, events_tab, map_tab, data_tab = st.tabs(
    ["Overview", "City Trends", "Extreme Events", "Map", "Data"]
)

with overview_tab:
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("Temperature")
        temperature_chart = city_df.set_index("timestamp_ict")[
            ["temperature_c", "rolling_avg_temp_24h"]
        ]
        st.line_chart(temperature_chart, height=340)

    with right_col:
        st.subheader("Last 24 Hours")
        last_24h = previous_day.set_index("timestamp_ict")
        st.area_chart(last_24h[["rain_mm"]], height=155)
        st.line_chart(last_24h[["wind_speed_ms"]], height=155)

    daily_city = (
        city_df.groupby("observed_date_ict", as_index=False)
        .agg(
            avg_temp_c=("temperature_c", "mean"),
            max_temp_c=("temperature_c", "max"),
            rain_mm=("rain_mm", "sum"),
            avg_wind_ms=("wind_speed_ms", "mean"),
        )
        .sort_values("observed_date_ict")
    )
    daily_city = daily_city.set_index("observed_date_ict")

    st.subheader("Daily Summary")
    summary_cols = st.columns(2)
    summary_cols[0].line_chart(daily_city[["avg_temp_c", "max_temp_c"]], height=260)
    summary_cols[1].bar_chart(daily_city[["rain_mm"]], height=260)

with trends_tab:
    compare_cities = st.multiselect(
        "Compare cities",
        cities,
        default=[selected_city],
        max_selections=8,
    )
    compare_df = filtered[filtered["city_name"].isin(compare_cities)]
    daily_compare = (
        compare_df.groupby(["observed_date_ict", "city_name"], as_index=False)[
            "temperature_c"
        ]
        .mean()
        .pivot(index="observed_date_ict", columns="city_name", values="temperature_c")
        .sort_index()
    )
    st.subheader("Average Temperature by City")
    st.line_chart(daily_compare, height=420)

    city_rank = (
        filtered.groupby("city_name", as_index=False)
        .agg(
            avg_temp_c=("temperature_c", "mean"),
            total_rain_mm=("rain_mm", "sum"),
            peak_wind_ms=("wind_speed_ms", "max"),
        )
        .sort_values("avg_temp_c", ascending=False)
    )
    rank_cols = st.columns(3)
    rank_cols[0].dataframe(
        city_rank[["city_name", "avg_temp_c"]].head(10),
        use_container_width=True,
        hide_index=True,
    )
    rank_cols[1].dataframe(
        city_rank.sort_values("total_rain_mm", ascending=False)[
            ["city_name", "total_rain_mm"]
        ].head(10),
        use_container_width=True,
        hide_index=True,
    )
    rank_cols[2].dataframe(
        city_rank.sort_values("peak_wind_ms", ascending=False)[
            ["city_name", "peak_wind_ms"]
        ].head(10),
        use_container_width=True,
        hide_index=True,
    )

with events_tab:
    if period_events.empty:
        st.info("No extreme events in this range.")
    else:
        event_totals = (
            period_events.groupby("city_name", as_index=False)
            .agg(
                extreme_event_count=("extreme_event_count", "sum"),
                sudden_temp_jump_count=("sudden_temp_jump_count", "sum"),
                high_wind_count=("high_wind_count", "sum"),
                heavy_rain_count=("heavy_rain_count", "sum"),
            )
            .sort_values("extreme_event_count", ascending=False)
        )

        event_cols = st.columns([1, 2])
        with event_cols[0]:
            st.subheader("Top Cities")
            st.dataframe(event_totals.head(12), use_container_width=True, hide_index=True)

        with event_cols[1]:
            selected_events = period_events[period_events["city_name"] == selected_city]
            st.subheader(f"{selected_city} Events")
            if selected_events.empty:
                st.info("No extreme events for this city.")
            else:
                event_series = selected_events.set_index("observed_date_ict")[
                    [
                        "sudden_temp_jump_count",
                        "high_wind_count",
                        "heavy_rain_count",
                    ]
                ]
                st.bar_chart(event_series, height=360)

with map_tab:
    latest_by_city = (
        filtered.sort_values("timestamp_ict")
        .groupby("city_name", as_index=False)
        .tail(1)
        .rename(columns={"lat": "latitude", "lon": "longitude"})
    )
    map_cols = st.columns([2, 1])
    with map_cols[0]:
        st.map(
            latest_by_city[
                ["latitude", "longitude", "temperature_c"]
            ].dropna(),
            size=60,
            color="#38bdf8",
        )
    with map_cols[1]:
        st.subheader("Latest City Readings")
        st.dataframe(
            latest_by_city[
                [
                    "city_name",
                    "timestamp_ict",
                    "temperature_c",
                    "humidity_pct",
                    "wind_speed_ms",
                    "rain_mm",
                    "source",
                ]
            ].sort_values("temperature_c", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

with data_tab:
    st.subheader("Filtered Observations")
    st.dataframe(
        city_df[
            [
                "timestamp_ict",
                "timestamp_utc",
                "temperature_c",
                "rolling_avg_temp_24h",
                "humidity_pct",
                "pressure_hpa",
                "wind_speed_ms",
                "rain_mm",
                "source",
            ]
        ].sort_values("timestamp_ict", ascending=False),
        use_container_width=True,
        hide_index=True,
        height=480,
    )
