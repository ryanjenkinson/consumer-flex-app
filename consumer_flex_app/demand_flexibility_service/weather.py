import geopandas as gpd
import pandas as pd
from meteostat import Hourly, Point


def create_event_times_from_summary(event_summary: pd.DataFrame) -> pd.DataFrame:
    event_times = event_summary.groupby("Date").agg(
        {"settlement_period_start": min, "settlement_period_end": max}
    )
    event_times["weather_start_utc"] = (
        event_times["settlement_period_start"]
        .dt.floor("1H")
        .dt.tz_convert("UTC")
        .dt.tz_convert(None)
    )
    event_times["weather_end_utc"] = (
        event_times["settlement_period_end"]
        .dt.ceil("1H")
        .dt.tz_convert("UTC")
        .dt.tz_convert(None)
    )
    return event_times


def get_region_points(dno_regions: gpd.GeoDataFrame) -> list[Point]:
    points = [
        Point(centroid.y, centroid.x)
        for centroid in dno_regions.centroid.to_crs("EPSG:4326")
    ]
    return points


def get_weather_by_events_and_region(
    event_times: pd.DataFrame,
    region_names: list,
    region_points: list[Point],
):
    weather = []
    for event in event_times.itertuples():
        for name, point in zip(region_names, region_points):
            data = Hourly(
                point, start=event.weather_start_utc, end=event.weather_end_utc
            )
            if not data.fetch().empty:
                weather += [data.fetch().resample("30min").ffill().assign(region=name)]

    return pd.concat(weather)
