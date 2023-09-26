import datetime
import gc
from functools import partial

import pandas as pd
import streamlit as st

from consumer_flex_app.demand_flexibility_service.extract import (
    get_dfs_dataframes,
    get_dfs_paths,
    get_dno_regions,
)
from consumer_flex_app.demand_flexibility_service.render import (
    render_map,
    render_metrics,
)
from consumer_flex_app.demand_flexibility_service.transform import (
    get_bids_by_provider_event,
    get_event_summary,
    get_metrics_by_dfs_event,
    get_regional_flex,
)

gc.enable()


def page_header() -> None:
    st.set_page_config(
        page_title="Demand Flexibility Service",
        page_icon=":zap:",
    )

    st.write("# 🤸‍♀️ Demand Flexibility Service ⚡️")
    st.write("## By [Ryan Jenkinson](https://ryan.eco) 👨‍💻")
    st.write(
        "A simple app showing stats from the [ESO Demand Flexibility Service](https://www.nationalgrideso.com/industry-information/balancing-services/demand-flexibility)."
    )
    st.info(
        """
        This [data is updated in real-time from National Grid ESO](https://data.nationalgrideso.com/dfs/). I am building this app to show:

        1. Open data that is easy to download and use is great - we can build informative tools in an open way
        2. The demand flexibility service has had broad industry participation, and signals an inflection point for the change required in our energy system

        We should use open data more in energy to drive the necessary innovation we need as we rapidly digitise and decarbonise our energy system. I wrote more about this in a [blog on my website](https://ryan.eco/topics/energy_system/data_for_the_future_energy_system/).

        If anything looks wrong with this app, or you'd like to request a feature you can:

        * Raise an issue / query on [Github](https://github.com/RyanJenkinson/consumer-flex-app), where the code is public
        * Email me directly: [hello@ryan.eco](mailto:hello@ryan.eco)
        * Tweet me directly: [@ryancjenkinson](https://twitter.com/ryancjenkinson)

        ⚠️ This app is still being actively developed and improved.
        """
    )


# Load in the data
@st.cache_data(ttl=datetime.timedelta(hours=1))
def get_all_data():
    dno_regions = get_dno_regions()
    paths = get_dfs_paths()
    bids, requirements, summary = get_dfs_dataframes(paths)
    # Start: Hotfix for a weird date parse error from ESO data portal.
    # Some bids on 13th Feb were 13/02/2022 instead of 2022-02-13. TODO: Deal with this better
    bids["Date"] = pd.to_datetime(bids["Date"], infer_datetime_format=True).dt.strftime(
        "%Y-%m-%d"
    )
    requirements["Delivery Date"] = pd.to_datetime(
        requirements["Delivery Date"], infer_datetime_format=True
    ).dt.strftime("%Y-%m-%d")
    summary["Date"] = pd.to_datetime(
        summary["Date"], infer_datetime_format=True
    ).dt.strftime("%Y-%m-%d")
    # End: Hotfix
    event_summary = get_event_summary(requirements, summary)
    dfs_metrics = get_metrics_by_dfs_event(bids, event_summary)
    total_bids_by_date_provider = get_bids_by_provider_event(bids)
    (
        day_ahead_flex_cumulative_by_region,
        day_ahead_flex_by_event_day_region,
    ) = get_regional_flex(dno_regions, bids, dfs_metrics)
    return (
        event_summary,
        dfs_metrics,
        total_bids_by_date_provider,
        day_ahead_flex_by_event_day_region,
        day_ahead_flex_cumulative_by_region,
    )


def _get_previous_dfs_date(dfs_date: str, all_dfs_dates: list[str]) -> str:
    # If the specified dfs_date is first in the list, the previous one equals itself
    return all_dfs_dates[max(0, all_dfs_dates.index(dfs_date) - 1)]


def main(
    event_summary,
    dfs_metrics,
    total_bids_by_date_provider,
    day_ahead_flex_by_event_day_region,
    day_ahead_flex_cumulative_by_region,
) -> None:
    DFS_DATES: list = sorted(event_summary["Date"].unique())
    LATEST_DFS_EVENT_DATE = DFS_DATES[-1]
    get_previous_dfs_date = partial(_get_previous_dfs_date, all_dfs_dates=DFS_DATES)

    tab_overall, tab_latest_event, tab_specific_event, tab_compare_event = st.tabs(
        ["Overall", "Latest DFS Event", "Specific DFS Event", "Compare DFS Events"]
    )

    tab_overall.write("# 🌍 Overall Statistics")
    metric_column = tab_overall.columns(3)
    metric_column[0].metric(label="Number of DFS Events", value=len(DFS_DATES))
    metric_column[1].metric(
        label="Number of Test Events", value=dfs_metrics.dfs_event_type.eq("TEST").sum()
    )
    metric_column[2].metric(
        label="Number of Live Events", value=dfs_metrics.dfs_event_type.eq("LIVE").sum()
    )

    # Render all the metrics, on each of the tabs
    render_metrics(
        dfs_metrics,
        tab_overall,
        LATEST_DFS_EVENT_DATE,
        get_previous_dfs_date(LATEST_DFS_EVENT_DATE),
        overall=True,
    )
    render_metrics(
        dfs_metrics,
        tab_latest_event,
        LATEST_DFS_EVENT_DATE,
        get_previous_dfs_date(LATEST_DFS_EVENT_DATE),
    )
    selected_dfs_event = tab_specific_event.selectbox("Select a DFS Event:", DFS_DATES)
    if selected_dfs_event:
        render_metrics(
            dfs_metrics,
            tab_specific_event,
            selected_dfs_event,
            get_previous_dfs_date(selected_dfs_event),
        )
    dfs_date_1 = tab_compare_event.selectbox(
        "Choose the first DFS event date:", DFS_DATES
    )
    if dfs_date_1:
        dfs_date_2 = tab_compare_event.selectbox(
            "Choose the second DFS Event Date:",
            [date for date in DFS_DATES if date != dfs_date_1],
        )
        if dfs_date_2:
            render_metrics(
                dfs_metrics,
                tab_compare_event,
                dfs_date_1,
                dfs_date_2,
                compare_events=True,
            )

    # Specific charts for the overall tab
    tab_overall.write("## 🤸‍♀️ Flexibility Provided")
    with tab_overall.expander(
        "Find out more about the types of forecasts flexibility service providers make in the DFS, and the difference between procured and settled flexibility"
    ):
        st.write(
            """
            In the bid process, providers make 2 forecasts:\n
                1. Day-ahead (D-1)
                2. The day of the flexibility event (D0)
            We use the second forecast to determine how much flexibility was 'procured' by ESO for the DFS.\n
            After the event has been run, providers have to submit meter readings for settlement with ESO. We present the _settled_ flexibility in a separate line graph.\n
            Note that the more recent events will show the `Settled Volume` of flexibility as 0, since ESO are still finalising all the settlement details.
            """
        )

    tab_overall.line_chart(
        dfs_metrics[["flex_settled_mwh", "flex_procured_mwh"]].rename(
            columns={
                "flex_settled_mwh": "Settled Flexibility (MWh)",
                "flex_procured_mwh": "Procured Flexibility (MWh)",
            }
        )
    )

    tab_overall.write("## 🤝 Bids by provider")
    tab_overall.write("### 👥 By provider")
    tab_overall.write("The top 3 providers of flexibility overall on the DFS are:")
    tab_overall.table(
        total_bids_by_date_provider.groupby(level="DFS Provider")
        .sum()
        .round()
        .astype(int)
        .nlargest(3)
        .rename("Forecasted Flexibility (D0) [MWh]")
    )
    tab_overall.bar_chart(
        total_bids_by_date_provider.groupby(level="DFS Provider")
        .sum()
        .rename("Procured Flexibility [MWh]")
        .round(2)
    )

    tab_overall.write("### 🗓️ By date and provider")
    tab_overall.bar_chart(total_bids_by_date_provider.unstack().round(2))
    render_map(tab_overall, day_ahead_flex_cumulative_by_region, overall=True)
    render_map(
        tab_latest_event, day_ahead_flex_by_event_day_region.loc[LATEST_DFS_EVENT_DATE]
    )
    if selected_dfs_event:
        render_map(
            tab_specific_event,
            day_ahead_flex_by_event_day_region.loc[selected_dfs_event],
        )

    gc.collect()


if __name__ == "__main__":
    page_header()
    # Get all the datasets
    (
        event_summary,
        dfs_metrics,
        total_bids_by_date_provider,
        day_ahead_flex_by_event_day_region,
        day_ahead_flex_cumulative_by_region,
    ) = get_all_data()
    # Run the main loop
    main(
        event_summary,
        dfs_metrics,
        total_bids_by_date_provider,
        day_ahead_flex_by_event_day_region,
        day_ahead_flex_cumulative_by_region,
    )
