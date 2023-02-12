import pytest

from consumer_flex_app.demand_flexibility_service.transform import (
    ENERGY_CONVERSIONS,
    convert_units_energy,
)


class TestEnergyComparisons:
    @pytest.mark.parametrize("fun_metric", ["Home per hour", "EV Charge", "Cup of Tea"])
    def test_energy_conversions_contains_fun_metric(self, fun_metric):
        assert fun_metric in ENERGY_CONVERSIONS

    def test_cup_of_tea_less_than_ev_charge(self):
        assert ENERGY_CONVERSIONS["Cup of Tea"] < ENERGY_CONVERSIONS["EV Charge"]


class TestConvertUnitsEnergy:
    def test_one_kwh_equals_one_thousand_watt_hour(self):
        assert convert_units_energy(1, from_units="kWh", to_units="Wh") == 1_000
