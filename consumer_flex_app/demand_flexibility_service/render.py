import gc
import math

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import seaborn as sns
import streamlit as st
from millify import millify

from consumer_flex_app.demand_flexibility_service.transform import convert_units_energy

gc.enable()

ENERGY_PREFIXES = ["kWh", "MWh", "GWh"]
POWER_PREFIXES = ["kW", "MW", "GW"]


def calculate_proportion_of_gb_homes_for_one_hour(
    number_of_homes_powered_for_one_hour: float,
    number_of_gb_households: int = 29_000_000,
) -> float:
    return 100 * (number_of_homes_powered_for_one_hour / number_of_gb_households)


def render_metrics(
    dfs_metrics: pd.DataFrame,
    tab,
    # TODO: Maybe change these to datetime.datetime or something
    dfs_date_1: str,
    dfs_date_2: str,
    overall: bool = False,
    compare_events: bool = False,
):
    show_delta = dfs_date_1 != dfs_date_2
    tab.write("# 📊 Event Statistics")
    metric_cols_in_table_display = [
        "settlement_period_start",
        "settlement_period_end",
        "dfs_event_type",
    ]
    dates_to_display = [dfs_date_1, dfs_date_2] if compare_events else [dfs_date_1]
    metrics_table_to_display = dfs_metrics.loc[
        dfs_metrics.index.isin(dates_to_display),
        metric_cols_in_table_display,
    ]
    if not overall:
        tab.table(metrics_table_to_display)

    # Lay out the key metrics
    metric_column = tab.columns(3)

    # TODO: Wrap all of the below into an internal _make_metric_box(col_name, metric_label, dfs_date_1, dfs_date_2) function
    # TODO: Should modularise each of the metrics into a metrics.py or something for better testability of logic

    # Metric: Number of DFS Providers in the event
    dfs_providers_col = f"num_dfs_providers{'_cumulative' if overall else ''}"
    number_of_dfs_providers = dfs_metrics.at[dfs_date_1, dfs_providers_col]
    number_of_dfs_providers_delta = (
        number_of_dfs_providers - dfs_metrics.at[dfs_date_2, dfs_providers_col]
    )
    metric_column[0].metric(
        label="Number of DFS Flexibility Providers",
        value=int(number_of_dfs_providers),
        delta=int(number_of_dfs_providers_delta) if show_delta else None,
        help="The number of unique Demand Flexibility Service (DFS) Providers who made bids to ESO.",
    )

    # Metric: Duration of flex events
    duration_col = f"duration_hours{'_cumulative' if overall else ''}"
    duration = dfs_metrics.at[dfs_date_1, duration_col]
    duration_delta = duration - dfs_metrics.at[dfs_date_2, duration_col]
    metric_column[1].metric(
        label="Duration of Flex Event [hours]",
        value=float(duration),
        delta=float(duration_delta) if show_delta else None,
        help="The duration of the flexibility event, which will be some multiple of 30 minutes.",
    )

    flex_procured_col = f"flex_procured_mwh{'_cumulative' if overall else ''}"
    flex_procured = dfs_metrics.at[dfs_date_1, flex_procured_col] * 1e6
    flex_procured_delta = (
        flex_procured - dfs_metrics.at[dfs_date_2, flex_procured_col] * 1e6
    )
    metric_column[2].metric(
        label="Total Flexibility Procured",
        value=millify(flex_procured, precision=2, prefixes=ENERGY_PREFIXES),
        delta=millify(flex_procured_delta, precision=2, prefixes=ENERGY_PREFIXES)
        if show_delta
        else None,
        help="The total flexibility _procured_ by all the DFS providers, summed up over the event. We use the values forecasted by the providers on the same day as the flexibility event (D0) rather than day-ahead. This is different from the flexibility _settled_ which is based on the actual meter readings sent by providers to ESO post-event.",
    )

    # Get median MW requirements and % met by DFS
    metric_column_2 = tab.columns(3)

    requirement_mw = (
        dfs_metrics.dfs_required_mw.median()
        if overall
        else dfs_metrics.at[dfs_date_1, "dfs_required_mw"]
    ).round(2)
    requirement_mw_2 = dfs_metrics.at[dfs_date_2, "dfs_required_mw"].round(2)
    requirement_mw_delta = None if overall else (requirement_mw - requirement_mw_2)
    # Default to the D0 prediction, if its available
    procured_mw = (
        dfs_metrics.dfs_procured_mw.fillna(
            dfs_metrics.dfs_procured_day_ahead_mw
        ).median()
        if overall
        else dfs_metrics.dfs_procured_mw.fillna(
            dfs_metrics.dfs_procured_day_ahead_mw
        ).at[dfs_date_1]
    ).round(2)
    procured_mw_2 = (
        dfs_metrics.dfs_procured_mw.fillna(dfs_metrics.dfs_procured_day_ahead_mw).at[
            dfs_date_2
        ]
    ).round(2)
    procured_mw_delta = None if overall else (procured_mw - procured_mw_2).round(2)

    proportion_of_requirement_met = procured_mw / requirement_mw
    proportion_of_requirement_met_2 = procured_mw_2 / requirement_mw_2
    proportion_of_requirement_met_delta = (
        None
        if overall
        else (proportion_of_requirement_met - proportion_of_requirement_met_2)
    )

    metric_column_2[0].metric(
        label="DFS Requirement (MW)",
        value=requirement_mw,
        delta=requirement_mw_delta if show_delta else None,
        help="The (median) average DFS requirement in MW across the event, as set by ESO day-ahead",
    )
    metric_column_2[1].metric(
        label="DFS Procured (MW)",
        value=procured_mw,
        delta=procured_mw_delta if show_delta else None,
        help="The (median) average DFS flexibility procured in MW. Will use the day-of-event forecast `D0` if available, else will use day-ahead",
    )
    metric_column_2[2].metric(
        label="DFS Requirement Met (%)",
        value=f"{proportion_of_requirement_met:.1%}",
        delta=f"{proportion_of_requirement_met_delta:.1%}"
        if proportion_of_requirement_met_delta and show_delta
        else None,
        help="The (average) proportion of the DFS requirement that was met by DFS providers.",
    )

    number_of_homes_powered_for_one_hour = math.ceil(
        convert_units_energy(flex_procured, "Wh", "Home per hour")
    )
    if flex_procured:
        tab.write(
            f"""
            That's the equivalent of powering **{number_of_homes_powered_for_one_hour:,}** homes for one hour!
            That's equivalent to **{calculate_proportion_of_gb_homes_for_one_hour(number_of_homes_powered_for_one_hour):.2f}%** of GB homes
            based on this [source](https://www.ukpower.co.uk/home_energy/average-household-gas-and-electricity-usage)!
            """
        )
        with tab.expander(
            "👀 Click to see some other fun comparisons to this amount of flexibility procured"
        ):
            st.write(
                f"""
                The stats below refer to the flexibility as the energy shifted (in watt-hours), not the power reduced (in watts). If you have any suggestions for fun comparisons, then get in touch!

                - 🔌 **{convert_units_energy(flex_procured, "Wh", "EV Charge"):,.1f}** EV's charging [from 0 - 100% with 40kWh battery]
                - ☕️ **{convert_units_energy(flex_procured, "Wh", "Cup of Tea"):,.1f}** large cups of tea [from a 3kW kettle, boiling 300ml water for 52 seconds]
            """
            )

    gc.collect()
    return None


def render_map(tab, gdf: gpd.GeoDataFrame, overall=False):
    gdf = gdf.to_crs("EPSG:4326").sort_values(by="value")
    gdf["fill_color"] = [
        list(255 * x for x in color) for color in sns.color_palette("Blues", len(gdf))
    ]
    gdf["value"] = gdf["value"].astype(int)
    INITIAL_VIEW_STATE = pdk.ViewState(latitude=55.5, longitude=-2, zoom=4)
    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            data=gdf,
            get_fill_color="fill_color",
            filled=True,
            pickable=True,
            wireframe=True,
            auto_highlight=True,
        )
    ]

    tooltip_text = """DNO Region Name: {LongName}
        - Average total day-ahead forecasted MW reduction: {value}MW
    """
    if overall:
        tooltip_text += "- Total day-ahead procured flexibility: {flex_mwh}MWh"

    deck = pdk.Deck(
        layers,
        initial_view_state=INITIAL_VIEW_STATE,
        tooltip={"text": tooltip_text},
    )

    tab.write("# 📌          Flexibility by region")
    with tab.expander("See explanation of how this was calculated"):
        st.write(
            """
            We calculate the flexibility per region by:

            1. Summing up the MW day-ahead forecasts across suppliers / supplier "units" for each settlement period
            2. Calculate the average total MW of flexibility for each settlement period in the flexibility event
            3. Calculate the MWh of flexibility by multiplying the average total MW by the duration of the flexibility event

            :information_source: Good to know: Flexibility events are often at least 1 hour. Meaning there are at least 2 settlement periods per event.
        """
        )
    tab.pydeck_chart(deck, use_container_width=True)
    gc.collect()
    return None
