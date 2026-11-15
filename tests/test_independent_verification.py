"""A8: independent verification of the numbers the app shows.

Every expected value here is recalculated along a separate, deliberately simple
path: the raw NASA JSON is read with the standard library only (no data layer,
no pandas, no validation code), and the soil equations are worked by hand from
FAO-56 Equations 82 and 83. The tests then compare those values with what the
engines produce. A disagreement means one of the two paths is wrong.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import random
from datetime import date, timedelta

import pytest

from src.config import PROJECT_ROOT
from src.models import ScenarioCategory

RAW_FILE = PROJECT_ROOT / "data" / "demo" / "4f87119a04095bb22483ce976c27c9947ffc065ca8d23f538212328d753a6956.json"


@pytest.fixture(scope="module")
def raw():
    return json.loads(RAW_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def daily(raw):
    """Parameter -> {date: value}, straight from NASA's JSON."""
    out = {}
    for name, series in raw["payload"]["properties"]["parameter"].items():
        out[name] = {date(int(key[:4]), int(key[4:6]), int(key[6:])): value for key, value in series.items()}
    return out


@pytest.fixture(scope="module")
def scenarios(pilot_dataset):
    from src.scenario_engine import build_scenarios
    from src.season_config import PILOT_WINDOWS

    return build_scenarios(pilot_dataset, PILOT_WINDOWS)


def days(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def simple_total(daily, start: date, end: date) -> float:
    return round(sum(daily["PRECTOTCORR"][day] for day in days(start, end)), 2)


# --- The raw file itself ---------------------------------------------------------------


def test_raw_file_fingerprint_matches_the_recorded_one(raw):
    canonical = json.dumps(raw["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == raw["payload_sha256"]
    assert raw["payload_sha256"] == "1c2ed230e2661199ac278e4ac68b179c4b5750284091c094745de4a920e0edaf"


def test_raw_request_is_the_documented_one(raw):
    request = raw["request"]
    assert (request["latitude"], request["longitude"]) == (-1.58, 37.24)
    assert request["community"] == "AG" and request["time_standard"] == "UTC"
    assert raw["url"].startswith("https://power.larc.nasa.gov/api/temporal/daily/point?")
    assert "time-standard=UTC" in raw["url"] and "PRECTOTCORR" in raw["url"]
    assert raw["payload"]["geometry"]["coordinates"][:2] == [37.24, -1.58]  # NASA echoes longitude, latitude


def test_raw_units_are_the_units_the_app_states(raw):
    units = {name: meta["units"] for name, meta in raw["payload"]["parameters"].items()}
    assert units["PRECTOTCORR"] == "mm/day" and units["T2M"] == units["T2M_MAX"] == units["T2M_MIN"] == "C"


def test_every_day_including_leap_days_is_present_and_valid(daily):
    expected = list(days(date(2001, 1, 1), date(2025, 12, 31)))
    assert len(expected) == 25 * 365 + 6  # 2004, 2008, 2012, 2016, 2020, 2024
    for name, series in daily.items():
        assert sorted(series) == expected, name
        assert all(value != -999 for value in series.values()), name
    assert date(2024, 2, 29) in daily["PRECTOTCORR"]


# --- Season totals and temperatures, recalculated ---------------------------------------------


SAMPLE = [
    ("long-rains", 2001), ("long-rains", 2009), ("long-rains", 2018), ("long-rains", 2019), ("long-rains", 2022),
    ("short-rains", 2005), ("short-rains", 2011), ("short-rains", 2019), ("short-rains", 2024), ("short-rains", 2025),
]


@pytest.mark.parametrize("window_id, year", SAMPLE)
def test_season_rainfall_total_recalculated_from_raw_json(daily, scenarios, window_id, year):
    months = (3, 5) if window_id == "long-rains" else (10, 12)
    start, end = date(year, months[0], 1), date(year, months[1], calendar.monthrange(year, months[1])[1])
    season = scenarios.season(f"{window_id}-{year}")
    assert season.rainfall_total_mm == pytest.approx(simple_total(daily, start, end), abs=0.011)
    assert season.days_expected == (end - start).days + 1 == 92


@pytest.mark.parametrize("window_id, year", SAMPLE[:4])
def test_season_temperature_statistics_recalculated_from_raw_json(daily, scenarios, window_id, year):
    months = (3, 5) if window_id == "long-rains" else (10, 12)
    span = list(days(date(year, months[0], 1), date(year, months[1], calendar.monthrange(year, months[1])[1])))
    season = scenarios.season(f"{window_id}-{year}")
    assert season.mean_temperature_c == pytest.approx(sum(daily["T2M"][d] for d in span) / len(span), abs=0.006)
    assert season.lowest_daily_min_c == pytest.approx(min(daily["T2M_MIN"][d] for d in span), abs=0.006)
    assert season.highest_daily_max_c == pytest.approx(max(daily["T2M_MAX"][d] for d in span), abs=0.006)
    assert season.frost_days == sum(1 for d in span if daily["T2M_MIN"][d] < 0)


def test_wet_days_and_dry_spell_recalculated(daily, scenarios):
    span = list(days(date(2019, 3, 1), date(2019, 5, 31)))
    rain = [daily["PRECTOTCORR"][d] for d in span]
    longest = run = 0
    for value in rain:
        run = run + 1 if value < 1.0 else 0
        longest = max(longest, run)
    season = scenarios.season("long-rains-2019")
    assert season.wet_days == sum(1 for value in rain if value >= 1.0)
    assert season.longest_dry_spell_days == longest


def test_year_crossing_window_on_the_real_record(pilot_dataset, daily):
    from src.scenario_engine import build_scenarios
    from src.season_config import SeasonWindow, WindowSource

    window = SeasonWindow(
        season_id="nov-feb", name="November to February", start_month=11, end_month=2,
        source_status=WindowSource.USER_DEFINED, basis="Test window.", limitations=("Test.",),
    )
    result = build_scenarios(pilot_dataset, (window,)).window("nov-feb")
    season = result.season("nov-feb-2011")  # 1 Nov 2011 to 29 Feb 2012: a leap year
    assert (season.start, season.end) == (date(2011, 11, 1), date(2012, 2, 29))
    assert season.rainfall_total_mm == pytest.approx(simple_total(daily, date(2011, 11, 1), date(2012, 2, 29)), abs=0.011)
    assert not result.season("nov-feb-2025").within_observation_period  # would end in 2026
    assert result.classified_count == 24  # 2001/02 to 2024/25


def test_annual_totals_recalculated(daily, scenarios):
    for item in scenarios.annual_rainfall:
        assert item.total_mm == pytest.approx(simple_total(daily, date(item.year, 1, 1), date(item.year, 12, 31)), abs=0.011)


# --- Tercile classification, reproduced independently -----------------------------------------


@pytest.mark.parametrize("window_id, months", [("long-rains", (3, 5)), ("short-rains", (10, 12))])
def test_terciles_reproduced_independently(daily, scenarios, window_id, months):
    totals = {
        year: simple_total(daily, date(year, months[0], 1), date(year, months[1], calendar.monthrange(year, months[1])[1]))
        for year in range(2001, 2026)
    }
    ranked = sorted(totals, key=lambda year: (totals[year], year))
    expected = {year: ScenarioCategory.DRY for year in ranked[:8]}
    expected.update({year: ScenarioCategory.TYPICAL for year in ranked[8:17]})
    expected.update({year: ScenarioCategory.WET for year in ranked[17:]})
    window = scenarios.window(window_id)
    assert {item.season_year: item.category for item in window.classified()} == expected
    assert window.dry_upper_mm == pytest.approx(totals[ranked[7]], abs=0.011)
    assert window.wet_lower_mm == pytest.approx(totals[ranked[17]], abs=0.011)
    median_dry = ranked[3]  # lower middle of 8
    assert window.representative[ScenarioCategory.DRY] == f"{window_id}-{median_dry}"


def test_classification_does_not_depend_on_record_order(pilot_dataset):
    """Metamorphic: shuffling the daily observations of each series changes nothing."""
    from src.data_validation import EnvironmentalDataset
    from src.models import ObservationSeries
    from src.scenario_engine import build_scenarios
    from src.season_config import PILOT_WINDOWS

    rng = random.Random(15112026)
    shuffled = []
    for series in pilot_dataset.series:
        items = list(series.observations)
        rng.shuffle(items)
        # Bypass the chronological-order check on purpose: the engine must not rely on input order.
        shuffled.append(ObservationSeries.model_construct(observations=tuple(items)))
    scrambled = EnvironmentalDataset.model_construct(**{**dict(pilot_dataset), "series": tuple(shuffled)})
    original = build_scenarios(pilot_dataset, PILOT_WINDOWS)
    again = build_scenarios(scrambled, PILOT_WINDOWS)
    for first, second in zip(original.windows, again.windows):
        assert [(s.season_id, s.rainfall_total_mm, s.category) for s in first.seasons] == [
            (s.season_id, s.rainfall_total_mm, s.category) for s in second.seasons
        ]


# --- Soil equations worked by hand --------------------------------------------------------------


@pytest.mark.parametrize(
    "crop_id, available_water, taw, raw",
    [
        # FAO-56 Eq. 82: TAW = 1000 x (θFC − θWP) x Zr ; Eq. 83: RAW = p x TAW
        ("maize", 0.15, (150.0, 255.0), (82.5, 140.2)),  # Zr 1.0-1.7 m, p 0.55 (Table 22)
        ("sorghum", 0.12, (120.0, 240.0), (66.0, 132.0)),  # Zr 1.0-2.0 m, p 0.55
        ("common-bean", 0.10, (60.0, 90.0), (27.0, 40.5)),  # Zr 0.6-0.9 m, p 0.45
        ("cowpea", 0.20, (120.0, 200.0), (54.0, 90.0)),  # Zr 0.6-1.0 m, p 0.45
    ],
)
def test_soil_water_worked_by_hand(kb, gate, crop_id, available_water, taw, raw):
    from src.models import GeoLocation
    from src.soil_inputs import SoilProfileInput, SoilValueInput, resolve_soil, root_zone_water

    soil = resolve_soil(
        SoilProfileInput(available_water_capacity=SoilValueInput(value=available_water * 1000, source_class="user_reported")),
        location=GeoLocation(latitude=-1.58, longitude=37.24), gate=gate,
    )
    result, _ = root_zone_water(kb.get_crop(crop_id), soil, gate)
    assert (result.taw_min_mm, result.taw_max_mm) == taw
    assert (result.raw_min_mm, result.raw_max_mm) == raw


def test_soil_boundaries(kb, gate):
    from src.models import GeoLocation
    from src.soil_inputs import SoilProfileInput, SoilValueInput, resolve_soil, root_zone_water

    location = GeoLocation(latitude=-1.58, longitude=37.24)
    zero = resolve_soil(SoilProfileInput(available_water_capacity=SoilValueInput(value=0, source_class="user_reported")), location=location, gate=gate)
    result, _ = root_zone_water(kb.get_crop("maize"), zero, gate)
    assert (result.taw_min_mm, result.taw_max_mm, result.raw_max_mm) == (0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        SoilProfileInput(available_water_capacity=SoilValueInput(value=-1, source_class="user_reported"))
    with pytest.raises(ValueError):
        SoilProfileInput(soil_ph=SoilValueInput(value=float("nan"), source_class="user_reported"))


# --- Comparison indicators, recalculated ----------------------------------------------------------


def test_rainfall_indicator_positions_recalculated(daily, kb, gate, scenarios):
    from src.comparison_engine import compare_strategies
    from src.season_config import CONTINUOUS_MAIZE, pilot_configuration

    report = compare_strategies((CONTINUOUS_MAIZE,), scenarios=scenarios, kb=kb, gate=gate, config=pilot_configuration())
    (result,) = report.strategy("continuous-maize").indicator("rainfall_vs_crop_water_use", window_id="short-rains")
    for finding in result.season_findings:
        total = simple_total(daily, date(finding.year, 10, 1), date(finding.year, 12, 31))
        expected = "below" if total < 500 else ("above" if total > 800 else "within")
        assert finding.position == expected
    assert [item.position for item in result.season_findings].count("below") == 25


def test_temperature_share_recalculated(daily, kb, gate, scenarios):
    from src.comparison_engine import compare_strategies
    from src.season_config import CONTINUOUS_MAIZE, pilot_configuration

    report = compare_strategies((CONTINUOUS_MAIZE,), scenarios=scenarios, kb=kb, gate=gate, config=pilot_configuration())
    (result,) = report.strategy("continuous-maize").indicator("temperature_vs_documented_range", window_id="long-rains")
    finding = next(item for item in result.season_findings if item.year == 2018)
    span = list(days(date(2018, 3, 1), date(2018, 5, 31)))
    inside = sum(1 for d in span if 18 <= round(daily["T2M"][d], 2) <= 21)
    assert finding.value == pytest.approx(round(100 * inside / len(span), 1))
