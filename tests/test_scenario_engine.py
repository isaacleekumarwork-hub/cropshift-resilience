"""A4.3 and A4.4: season windows, pilot configuration and historical scenarios.

Unit tests use small daily tables built in memory and labelled as test inputs;
those values never leave the test. Integration tests use the real bundled NASA
pilot dataset, read offline.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from src.data_validation import build_dataset
from src.models import GeoLocation, ScenarioCategory
from src.pilot_sites import KATUMANI
from src.scenario_engine import (
    MIN_SEASONS_FOR_CLASSIFICATION,
    ScenarioEngineError,
    _classify,
    _season,
    build_scenarios,
)
from src.season_config import (
    LONG_RAINS,
    PILOT_WINDOWS,
    SHORT_RAINS,
    PilotStatus,
    SeasonWindow,
    WindowSource,
    pilot_configuration,
)

SITE = GeoLocation(latitude=-1.58, longitude=37.24, name="Test site")


def window(**fields) -> SeasonWindow:
    base = dict(
        season_id="test-window", name="Test window", start_month=3, end_month=5,
        source_status=WindowSource.USER_DEFINED, basis="Test input.", limitations=("Test.",),
    )
    base.update(fields)
    return SeasonWindow(**base)


def daily_table(start: str, end: str, rain=1.0, tmean=20.0, tmin=12.0, tmax=28.0) -> pd.DataFrame:
    """A synthetic daily table for unit tests only. Not NASA data."""
    days = pd.date_range(start, end, freq="D")
    frame = pd.DataFrame(
        {
            "precipitation": rain if not callable(rain) else [rain(day) for day in days],
            "air_temperature_mean": tmean,
            "air_temperature_min": tmin,
            "air_temperature_max": tmax,
        },
        index=days,
    )
    return frame.astype("float64")


# --- A4.3: windows and pilot configuration --------------------------------------------


def test_pilot_windows_are_the_cited_giews_windows():
    assert [(item.start_month, item.end_month) for item in PILOT_WINDOWS] == [(3, 5), (10, 12)]
    for item in PILOT_WINDOWS:
        assert item.source_status is WindowSource.CITED and item.source_ids == ("fao-giews-kenya",)
        assert not item.is_sowing_date
        assert any("not a sowing date" in text for text in item.limitations)


def test_window_dates_and_length():
    assert LONG_RAINS.dates_for(2020) == (date(2020, 3, 1), date(2020, 5, 31))
    assert LONG_RAINS.length_days(2020) == 92
    assert SHORT_RAINS.length_days(2021) == 92
    assert not LONG_RAINS.crosses_year


def test_year_crossing_window():
    crossing = window(start_month=11, end_month=2)
    assert crossing.crosses_year
    assert crossing.dates_for(2023) == (date(2023, 11, 1), date(2024, 2, 29))  # 2024 is a leap year
    assert crossing.dates_for(2021) == (date(2021, 11, 1), date(2022, 2, 28))
    assert crossing.label_for(2023) == "Test window 2023/2024"


@pytest.mark.parametrize(
    "fields, message",
    [
        (dict(start_day=31, start_month=4), "start_day"),
        (dict(end_day=30, end_month=2), "end_day"),
        (dict(is_sowing_date=True), "sowing date"),
        (dict(source_status=WindowSource.CITED), "name its source"),
        (dict(source_ids=("fao-giews-kenya",)), "no source"),
        (dict(start_month=13), "less than or equal"),
    ],
)
def test_invalid_windows_are_rejected(fields, message):
    with pytest.raises(ValidationError, match=message):
        window(**fields)


def test_pilot_is_provisional_with_unchanged_coordinates():
    config = pilot_configuration()
    assert config.status is PilotStatus.PROVISIONAL
    assert (config.location.latitude, config.location.longitude) == (-1.58, 37.24)
    assert config.location == KATUMANI.location
    assert "not approved" in config.approval_note
    assert any("Machakos County, Kenya" in item.result for item in config.location_checks)


def test_approved_status_requires_an_approved_site():
    from src.season_config import PilotConfiguration

    with pytest.raises(ValidationError, match="approved"):
        PilotConfiguration(site=KATUMANI, status=PilotStatus.APPROVED, windows=PILOT_WINDOWS, approval_note="x")


def test_pilot_configuration_is_replaceable():
    other = KATUMANI.model_copy(update={"site_id": "elsewhere", "name": "Elsewhere"})
    config = pilot_configuration(other, (SHORT_RAINS,))
    assert config.site.site_id == "elsewhere" and config.location_checks == ()
    assert [item.season_id for item in config.windows] == ["short-rains"]


# --- A4.4: one season from a daily table ----------------------------------------------


def test_seasonal_rainfall_total_and_window_are_respected():
    # 1 mm every day from January to June, but 5 mm inside March-May: the total must be 5 x 92.
    table = daily_table("2020-01-01", "2020-06-30", rain=lambda day: 5.0 if 3 <= day.month <= 5 else 1.0)
    season = _season(LONG_RAINS, 2020, table, (date(2020, 1, 1), date(2020, 6, 30)), SITE, 100.0)
    assert season.rainfall_total_mm == 460.0 and season.days_expected == 92
    assert [(item.month, item.total_mm) for item in season.monthly_rainfall] == [(3, 155.0), (4, 150.0), (5, 155.0)]
    assert season.complete and season.within_observation_period


def test_rain_day_dry_spell_and_heavy_rain_counts():
    pattern = {date(2020, 3, 2): 0.5, date(2020, 3, 3): 0.0, date(2020, 3, 4): 0.99, date(2020, 3, 10): 25.0, date(2020, 3, 11): 12.0}
    table = daily_table("2020-03-01", "2020-05-31", rain=lambda day: pattern.get(day.date(), 1.0))
    season = _season(LONG_RAINS, 2020, table, (date(2020, 3, 1), date(2020, 5, 31)), SITE, 100.0)
    assert season.dry_days == 3 and season.wet_days == 89  # 1.0 mm counts as wet (at least 1 mm)
    assert season.longest_dry_spell_days == 3
    assert season.heavy_rain_days_10mm == 2 and season.heavy_rain_days_20mm == 1
    assert season.max_daily_rainfall_mm == 25.0


def test_frost_days_use_the_etccdi_definition():
    table = daily_table("2020-03-01", "2020-05-31", tmin=5.0)
    table.loc["2020-03-05", "air_temperature_min"] = 0.0  # not below 0: not a frost day
    table.loc["2020-03-06", "air_temperature_min"] = -0.1
    season = _season(LONG_RAINS, 2020, table, (date(2020, 3, 1), date(2020, 5, 31)), SITE, 100.0)
    assert season.frost_days == 1 and season.lowest_daily_min_c == -0.1


def test_missing_days_make_the_season_incomplete():
    table = daily_table("2020-03-01", "2020-05-31")
    table.loc["2020-04-10", "precipitation"] = float("nan")
    season = _season(LONG_RAINS, 2020, table, (date(2020, 3, 1), date(2020, 5, 31)), SITE, 100.0)
    assert not season.complete and season.rainfall_total_mm is None
    assert season.precipitation_days_valid == 91
    assert any("1 of 92 days" in item for item in season.issues)


def test_lower_threshold_reports_a_total_and_flags_its_bias():
    table = daily_table("2020-03-01", "2020-05-31")
    table.loc["2020-04-10", "precipitation"] = float("nan")
    season = _season(LONG_RAINS, 2020, table, (date(2020, 3, 1), date(2020, 5, 31)), SITE, 95.0)
    assert season.complete and season.rainfall_total_mm == 91.0
    assert any("biased low" in item for item in season.issues)


def test_season_partly_outside_the_record_is_incomplete():
    crossing = window(start_month=11, end_month=2)
    table = daily_table("2020-01-01", "2020-12-31")
    season = _season(crossing, 2020, table, (date(2020, 1, 1), date(2020, 12, 31)), SITE, 100.0)
    assert not season.within_observation_period and not season.complete
    assert season.end == date(2021, 2, 28)


def test_cross_year_season_totals_span_both_years():
    crossing = window(start_month=12, end_month=1)
    table = daily_table("2020-01-01", "2021-12-31", rain=2.0)
    season = _season(crossing, 2020, table, (date(2020, 1, 1), date(2021, 12, 31)), SITE, 100.0)
    assert season.complete and season.rainfall_total_mm == 2.0 * 62
    assert [item.year for item in season.monthly_rainfall] == [2020, 2021]


def test_season_entirely_outside_the_record_is_not_created():
    table = daily_table("2020-01-01", "2020-12-31")
    assert _season(LONG_RAINS, 2015, table, (date(2020, 1, 1), date(2020, 12, 31)), SITE, 100.0) is None


# --- A4.4: classification ---------------------------------------------------------


def _seasons(totals: dict[int, float]):
    """Synthetic seasons with given totals (1 day of rain each); unit tests only."""
    seasons = []
    for year, total in totals.items():
        table = daily_table(f"{year}-03-01", f"{year}-05-31", rain=lambda day, t=total: t if day.day == 1 and day.month == 3 else 0.0)
        seasons.append(_season(LONG_RAINS, year, table, (date(year, 1, 1), date(year, 12, 31)), SITE, 100.0))
    return seasons


def test_terciles_with_25_seasons_give_8_9_8():
    result = _classify(LONG_RAINS, _seasons({2000 + i: float(10 * i) for i in range(1, 26)}), SITE, (date(2001, 1, 1), date(2025, 12, 31)))
    counts = {category: len(result.by_category(category)) for category in ScenarioCategory}
    assert counts == {ScenarioCategory.DRY: 8, ScenarioCategory.TYPICAL: 9, ScenarioCategory.WET: 8}
    assert result.dry_upper_mm == 80.0 and result.wet_lower_mm == 180.0
    assert result.representative == {
        ScenarioCategory.DRY: "long-rains-2004",
        ScenarioCategory.TYPICAL: "long-rains-2013",
        ScenarioCategory.WET: "long-rains-2021",
    }


def test_classification_is_deterministic_and_ties_are_ordered_by_year():
    totals = {2001: 50.0, 2002: 50.0, 2003: 10.0, 2004: 90.0, 2005: 90.0, 2006: 30.0, 2007: 70.0, 2008: 60.0, 2009: 20.0}
    first = _classify(LONG_RAINS, _seasons(totals), SITE, (date(2001, 1, 1), date(2009, 12, 31)))
    again = _classify(LONG_RAINS, list(reversed(_seasons(totals))), SITE, (date(2001, 1, 1), date(2009, 12, 31)))
    ranks = {item.season_year: item.rank for item in first.classified()}
    assert ranks == {item.season_year: item.rank for item in again.classified()}
    assert ranks[2001] < ranks[2002] and ranks[2004] < ranks[2005]


def test_too_few_seasons_are_not_classified():
    result = _classify(LONG_RAINS, _seasons({2001 + i: float(i) for i in range(MIN_SEASONS_FOR_CLASSIFICATION - 1)}), SITE, (date(2001, 1, 1), date(2010, 12, 31)))
    assert result.classified_count == 0 and not result.classified()
    assert "at least" in result.excluded[-1]


def test_incomplete_seasons_are_excluded_from_classification_with_a_reason():
    seasons = _seasons({2000 + i: float(i) for i in range(1, 11)})
    table = daily_table("2011-03-01", "2011-05-31")
    table.loc["2011-04-01", "precipitation"] = float("nan")
    seasons.append(_season(LONG_RAINS, 2011, table, (date(2011, 1, 1), date(2011, 12, 31)), SITE, 100.0))
    result = _classify(LONG_RAINS, seasons, SITE, (date(2001, 1, 1), date(2011, 12, 31)))
    assert result.classified_count == 10
    assert any(item.startswith("Long rains 2011") for item in result.excluded)


def test_classified_seasons_carry_a_historical_scenario_that_is_not_a_forecast():
    result = _classify(LONG_RAINS, _seasons({2000 + i: float(i) for i in range(1, 13)}), SITE, (date(2001, 1, 1), date(2012, 12, 31)))
    for item in result.classified():
        assert item.scenario.is_forecast is False
        assert item.scenario.scenario_id == item.season_id
        assert item.scenario.classification_variable == "precipitation_total"
        assert (item.scenario.period_start, item.scenario.period_end) == (item.start, item.end)


# --- A4.4: the real pilot record ----------------------------------------------------


@pytest.fixture(scope="module")
def scenarios(pilot_dataset):
    return build_scenarios(pilot_dataset, PILOT_WINDOWS)


def test_pilot_record_coverage_is_verified_not_assumed(scenarios):
    assert scenarios.complete_years == 25
    assert (scenarios.first_valid_day, scenarios.last_valid_day) == (date(2001, 1, 1), date(2025, 12, 31))
    for item in scenarios.windows:
        assert item.classified_count == 25 and item.excluded == ()


def test_pilot_scenarios_trace_back_to_the_nasa_record(scenarios, pilot_dataset):
    assert scenarios.dataset_id == pilot_dataset.dataset_id
    assert scenarios.payload_sha256 == pilot_dataset.provenance.payload_sha256
    assert scenarios.dataset_citations == pilot_dataset.provenance.citations
    assert scenarios.location == pilot_dataset.location
    assert "etccdi-indices" in scenarios.method_source_ids


def test_pilot_season_total_equals_the_sum_of_nasa_daily_values(scenarios, pilot_dataset):
    from src.data_processing import to_wide_frame

    wide = to_wide_frame(pilot_dataset)
    expected = round(float(wide.loc["2019-03-01":"2019-05-31", "precipitation"].sum()), 2)
    assert scenarios.season("long-rains-2019").rainfall_total_mm == expected


def test_pilot_season_total_matches_the_monthly_summary(scenarios, pilot_dataset):
    from src.data_processing import monthly_summary

    monthly = monthly_summary(pilot_dataset)
    rows = monthly[(monthly["variable"] == "precipitation") & (monthly["year"] == 2011) & monthly["month"].between(10, 12)]
    assert scenarios.season("short-rains-2011").rainfall_total_mm == pytest.approx(rows["value"].sum(), abs=0.01)


def test_pilot_classification_is_reproducible(pilot_dataset, scenarios):
    again = build_scenarios(pilot_dataset, PILOT_WINDOWS)
    assert again.model_dump() == scenarios.model_dump()


def test_pilot_daily_values_are_nasa_values_unchanged(scenarios, pilot_dataset):
    series = pilot_dataset.get("precipitation")
    first_day = next(item for item in series.observations if item.period_start == date(2003, 3, 1))
    assert scenarios.season("long-rains-2003").daily_precipitation_mm[0] == round(first_day.value, 2)


def test_rejected_dataset_cannot_produce_scenarios(make_retrieval):
    def empty_rain(payload):
        rain = payload["properties"]["parameter"]["PRECTOTCORR"]
        for key in rain:
            rain[key] = -999.0

    dataset = build_dataset(make_retrieval(empty_rain))
    with pytest.raises(Exception, match="not accepted"):
        build_scenarios(dataset, PILOT_WINDOWS)


def test_short_record_reports_why_nothing_was_classified(recorded_retrieval):
    dataset = build_dataset(recorded_retrieval)  # 91 days, January to March 2020
    result = build_scenarios(dataset, (LONG_RAINS, window(season_id="jan-feb", start_month=1, end_month=2)))
    long_rains = result.window("long-rains")
    assert long_rains.classified_count == 0
    assert any("outside the observation period" in item for item in long_rains.excluded)
    assert result.window("jan-feb").season("jan-feb-2020").complete


def test_invalid_threshold_is_rejected(pilot_dataset):
    with pytest.raises(ScenarioEngineError):
        build_scenarios(pilot_dataset, PILOT_WINDOWS, min_completeness_percent=0)
