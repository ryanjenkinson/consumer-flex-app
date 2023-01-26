import pandas as pd

_forecast_cols = [
    # Day-ahead forecasts
    "North Scotland",
    "South and Central Scotland",
    "North East England",
    "North West England",
    "Yorkshire",
    "East Midlands",
    "West Midlands",
    "London",
    "East England",
    "South East England",
    "South West England",
    "Southern England",
    "North Wales, Merseyside and Cheshire",
    "South Wales",
    "Other",
    "Total",
    # Same-Day forecasts, at 10:00am
    "D0 North Scotland",
    "D0 South and Central Scotland",
    "D0 North East England",
    "D0 North West England",
    "D0 Yorkshire",
    "D0 East Midlands",
    "D0 West Midlands",
    "D0 London",
    "D0 East England",
    "D0 South East England",
    "D0 South West England",
    "D0 Southern England",
    "D0 North Wales Merseyside and Cheshire",
    "D0 South Wales",
    "D0 Other",
    "D0 Total",
]
BID_AGGREGATIONS = {
    **{col: "sum" for col in _forecast_cols + ["DFS Volume (MW)", "Price (£/MWh)"]},
}
DFS_NAME_TO_DNO_NAME_MAPPING = {
    "East England": "_A",
    "East Midlands": "_B",
    "London": "_C",
    "North Wales, Merseyside and Cheshire": "_D",
    "West Midlands": "_E",
    "North East England": "_F",
    "North West England": "_G",
    "Southern England": "_H",
    "South East England": "_J",
    "South Wales": "_K",
    "South West England": "_L",
    "Yorkshire": "_M",
    "South and Central Scotland": "_N",
    "North Scotland": "_P",
}


def append_settlement_periods(df: pd.DataFrame) -> pd.DataFrame:
    df["settlement_period_start"] = pd.to_datetime(
        df["Date"] + " " + df["From (GMT)"]
    ).dt.tz_localize("Europe/London")
    df["settlement_period_end"] = pd.to_datetime(
        df["Date"] + " " + df["To (GMT)"]
    ).dt.tz_localize("Europe/London")
    return df


def get_bids_by_provider_settlement_period(bids: pd.DataFrame) -> pd.DataFrame:
    bids_by_provider_settlement_period = (
        bids.pipe(append_settlement_periods)
        .groupby(
            ["Date", "DFS Provider", "settlement_period_start", "settlement_period_end"]
        )
        .agg(BID_AGGREGATIONS)
    )
    # bids_by_provider_settlement_period.columns = [
    #     f"{column_name} [{aggregation}]"
    #     for column_name, aggregation in bids_by_provider_settlement_period.columns
    # ]
    return bids_by_provider_settlement_period.reset_index()


def get_event_summary(
    requirements: pd.DataFrame,
    summary: pd.DataFrame,
) -> pd.DataFrame:
    requirements_column_renames = {
        "Delivery Date": "Date",
        "From GMT": "From (GMT)",
        "To GMT": "To (GMT)",
    }
    event_summary = pd.merge(
        requirements.rename(columns=requirements_column_renames).pipe(
            append_settlement_periods
        ),
        summary.pipe(append_settlement_periods),
        on=[
            "Date",
            "From (GMT)",
            "To (GMT)",
            "settlement_period_start",
            "settlement_period_end",
            "dfs_event_type",
        ],
    )
    event_summary["Settled Price (£/MW)"] = (
        event_summary["Settled Cost "] / event_summary["Settled Volume"]
    )
    #  Since each row is half an hour
    event_summary["flex_settled_mwh"] = event_summary["Settled Volume"] / 2
    event_summary["flex_procured_mwh"] = event_summary["D0 DFS Procured (MW)"] / 2
    return event_summary


def get_metrics_by_dfs_event(
    bids: pd.DataFrame,
    event_summary: pd.DataFrame,
) -> pd.DataFrame:
    dates, cumcounts, counts, cumunique = [], [], [], set()
    for date, df in bids.groupby("Date"):
        dfs_providers = set(df["DFS Provider"])
        cumunique |= dfs_providers
        dates.append(date)
        cumcounts.append(len(cumunique))
        counts.append(len(dfs_providers))

    dfs_provider_metrics = pd.DataFrame(
        {"num_dfs_providers": counts, "num_dfs_providers_cumulative": cumcounts},
        index=pd.Index(dates, name="Date"),
    )

    event_summary_columns_to_rename = {
        "DFS Required (MW)": "dfs_required_mw",
        "DFS Procured (MW)": "dfs_procured_day_ahead_mw",
        "D0 DFS Procured (MW)": "dfs_procured_mw",
    }
    event_aggregations = {
        "settlement_period_start": "first",
        "settlement_period_end": "last",
        "dfs_event_type": "first",
        "From (GMT)": "count",
        "flex_settled_mwh": "sum",
        "flex_procured_mwh": "sum",
        "dfs_required_mw": "median",
        "dfs_procured_day_ahead_mw": "median",
        "dfs_procured_mw": "median",
    }
    event_metrics = (
        event_summary.rename(columns=event_summary_columns_to_rename)
        .groupby("Date")
        .agg(event_aggregations)
    )
    event_metrics["duration_hours"] = event_metrics["From (GMT)"].div(2)
    event_metrics.drop(columns=["From (GMT)"], inplace=True)
    for column in ["duration_hours", "flex_settled_mwh", "flex_procured_mwh"]:
        event_metrics[f"{column}_cumulative"] = event_metrics[column].cumsum()

    return pd.concat([dfs_provider_metrics, event_metrics], axis=1)


def get_event_by_geometry(bids: pd.DataFrame) -> pd.DataFrame:
    def _get_forecast_type(variable: str) -> str | None:
        if variable in _forecast_cols:
            if "D0" in variable:
                return "Same Day"
            return "Day Ahead"
        return None

    event_by_geography = (
        bids.groupby(["Date", "From (GMT)"])
        # Sum MW over supplier forecasts
        .agg(BID_AGGREGATIONS)
        # Average MW over settlement periods in the flexibility event
        .groupby(level="Date")
        .mean()
        .stack()
        .rename_axis(["date", "variable"])
        .rename("value")
        .reset_index()
    )
    event_by_geography["forecast_type"] = event_by_geography["variable"].map(
        _get_forecast_type
    )
    event_by_geography["dno_region_name"] = (
        event_by_geography["variable"]
        .str.replace("D0 ", "")
        .map(DFS_NAME_TO_DNO_NAME_MAPPING.get)
    )
    return event_by_geography
