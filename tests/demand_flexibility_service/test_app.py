import pytest

from consumer_flex_app.demand_flexibility_service.app import _get_previous_dfs_date


@pytest.fixture
def fake_dfs_dates() -> list[str]:
    return ["2023-01-01", "2023-01-04", "2023-01-22"]


class TestGetPreviousDFSDate:
    def test_get_previous_dfs_date_returns_previous_value_in_list(self, fake_dfs_dates):
        for dfs_date, previous_dfs_date in zip(fake_dfs_dates[1:], fake_dfs_dates[:-1]):
            assert _get_previous_dfs_date(dfs_date, fake_dfs_dates) == previous_dfs_date

    def test_get_previous_dfs_date_returns_initial_value_on_first_date(
        self, fake_dfs_dates
    ):
        first_dfs_date = fake_dfs_dates[0]
        assert _get_previous_dfs_date(first_dfs_date, fake_dfs_dates) == first_dfs_date
