import enum

import geopandas as gpd
import pandas as pd
from clumper import Clumper


class DFSEventType(enum.Enum):
    TEST = 0
    LIVE = 1


# https://data.nationalgrideso.com/dfs
DATAPACKAGE_PATHS = {
    DFSEventType.LIVE: "https://data.nationalgrideso.com/dfs/demand-flexibility-service-live-events/datapackage.json",
    DFSEventType.TEST: "https://data.nationalgrideso.com/dfs/demand-flexibility-service-test-events/datapackage.json",
}

# https://data.nationalgrideso.com/system/gis-boundaries-for-gb-dno-license-areas
ESO_DNO_LICENSE_AREAS_DATAPACKAGE = "https://data.nationalgrideso.com/system/gis-boundaries-for-gb-dno-license-areas/datapackage.json"


def get_paths_from_datapackage(datapackage_path: str) -> pd.DataFrame:
    paths = (
        Clumper.read_json(datapackage_path)
        .unpack("resources")
        .select("title", "path")
        .collect()
    )
    return pd.DataFrame(paths)


def get_dfs_paths() -> pd.DataFrame:
    paths = pd.concat(
        [
            get_paths_from_datapackage(DATAPACKAGE_PATHS[DFSEventType.LIVE]).assign(
                dfs_event_type="LIVE"
            ),
            get_paths_from_datapackage(DATAPACKAGE_PATHS[DFSEventType.TEST]).assign(
                dfs_event_type="TEST"
            ),
        ],
        ignore_index=True,
    )
    return paths


# TODO: Come up with a better way of doing this. It basically just combines the LIVE and TEST dfs dataframes
def combine_live_and_test_dfs_event_dataframe(
    paths: pd.DataFrame,
    filter_str: str,
) -> pd.DataFrame:
    dataframes = []
    for row in paths[paths.title.str.contains(filter_str)].itertuples():
        df = pd.read_csv(row.path)
        df["dfs_event_type"] = row.dfs_event_type
        dataframes += [df]
    return pd.concat(dataframes, ignore_index=True)


def get_dfs_dataframes(paths) -> pd.DataFrame:
    bids = combine_live_and_test_dfs_event_dataframe(paths, "DFS Utilisation Report")
    requirements = combine_live_and_test_dfs_event_dataframe(
        paths, "DFS Service Requirement"
    )
    summary = combine_live_and_test_dfs_event_dataframe(paths, "Summary")
    return bids, requirements, summary


def get_dno_regions() -> pd.DataFrame:
    SHAPEFILE_FILEPATH = (
        Clumper.read_json(ESO_DNO_LICENSE_AREAS_DATAPACKAGE)
        .unpack("resources")
        .keep(lambda d: "shapefile" in d["description"].lower())
        .sort(lambda d: d["last_modified"])
        .select("path")
        .tail(1)
        .collect()[0]["path"]
    )

    dno_regions = gpd.read_file(SHAPEFILE_FILEPATH, crs="EPSG:27700")
    return dno_regions
