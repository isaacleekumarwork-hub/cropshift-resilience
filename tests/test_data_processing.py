"""Daily tables, monthly aggregation and descriptive summaries.

Expected values are computed here directly from the recorded NASA response,
independently of the code under test.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import pytest

from src.data_processing import (
    AGGREGATION_RULES,
    DAILY_COLUMNS,
    MONTHLY_COLUMNS,
    monthly_climatology,
    monthly_summary,
    quality_table,
    to_frame,
    to_wide_frame,
)
from src.data_validation import build_dataset
from src.nasa_client import POWER_PARAMETERS, PowerRequest
from tests.conftest import daily

DAYS_IN_MONTH = {1: 31, 2: 29, 3: 31}  # 2020 was a leap year


def source_values(envelope, parameter: str, month: int) -> list[float]:
    block = envelope["payload"]["properties"]["parameter"][parameter]
    return [value for key, value in sorted(block.items()) if key.startswith(f"2020{month:02d}")]


def row(monthly: pd.DataFrame, variable: str, month: int) -> pd.Series:
    match = monthly[(monthly["variable"] == variable) & (monthly["month"] == month)]
    assert len(match) == 1
    return match.iloc[0]


@pytest.fixture
def dataset(recorded_retrieval):
    return build_dataset(recorded_retrieval)


# --- Daily tables --------------------------------------------------------------------


def test_long_table_has_one_row_per_variable_and_day(dataset):
    frame = to_frame(dataset)
    assert list(frame.columns) == DAILY_COLUMNS
    assert len(frame) == 6 * 91
    assert frame["value"].dtype == "float64" and frame["value"].notna().all()
    assert set(frame["missing"]) == {"present"}
    assert set(frame["unit"]) == {"degC", "mm/day", "MJ/m^2/day", "%"}
    assert set(frame["kind"]) == {"reanalysis", "satellite_retrieval"}
    for _, group in frame.groupby("variable"):
        assert group["date"].is_monotonic_increasing and group["date"].is_unique


def test_wide_table_has_one_row_per_day(dataset):
    wide = to_wide_frame(dataset)
    assert wide.shape == (91, 6)
    assert list(wide.columns) == list(dataset.variables)
    assert wide.index[0] == pd.Timestamp("2020-01-01") and wide.index[-1] == pd.Timestamp("2020-03-31")
    assert wide.index.is_monotonic_increasing


def test_gaps_stay_empty_and_keep_their_reason(make_retrieval):
    gappy = build_dataset(make_retrieval(lambda p: daily(p, "PRECTOTCORR").update({"20200105": -999.0})))
    frame = to_frame(gappy)
    gap = frame[(frame["variable"] == "precipitation") & (frame["date"] == pd.Timestamp("2020-01-05"))].iloc[0]
    assert math.isnan(gap["value"]) and gap["value"] != 0
    assert gap["missing"] == "missing_at_source"
    assert math.isnan(to_wide_frame(gappy).loc[pd.Timestamp("2020-01-05"), "precipitation"])


# --- Monthly aggregation -------------------------------------------------------------


def test_monthly_table_shape_and_columns(dataset):
    monthly = monthly_summary(dataset)
    assert list(monthly.columns) == MONTHLY_COLUMNS
    assert len(monthly) == 6 * 3
    assert monthly["reported"].all()
    assert set(monthly["year"]) == {2020} and set(monthly["month"]) == {1, 2, 3}
    for month, days in DAYS_IN_MONTH.items():
        assert set(monthly[monthly["month"] == month]["days_expected"]) == {days}


@pytest.mark.parametrize("month", [1, 2, 3])
def test_precipitation_is_summed(month, dataset, recorded_envelope):
    values = source_values(recorded_envelope, "PRECTOTCORR", month)
    result = row(monthly_summary(dataset), "precipitation", month)
    assert result["statistic"] == "total"
    assert result["value"] == pytest.approx(sum(values))
    assert result["unit"] == "mm" and result["output_variable"] == "precipitation_total"
    assert result["days_valid"] == DAYS_IN_MONTH[month] and result["completeness_percent"] == 100.0


@pytest.mark.parametrize(
    "parameter", ["T2M", "T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN", "RH2M"]
)
def test_other_variables_are_averaged(parameter, dataset, recorded_envelope):
    variable = POWER_PARAMETERS[parameter].variable
    monthly = monthly_summary(dataset)
    for month in DAYS_IN_MONTH:
        values = source_values(recorded_envelope, parameter, month)
        result = row(monthly, variable, month)
        assert result["statistic"] == "mean"
        assert result["value"] == pytest.approx(sum(values) / len(values))
        assert result["unit"] == POWER_PARAMETERS[parameter].unit.value
        assert result["output_variable"] == variable


def test_totals_and_means_are_not_interchangeable(dataset, recorded_envelope):
    monthly = monthly_summary(dataset)
    rain = source_values(recorded_envelope, "PRECTOTCORR", 1)
    total = row(monthly, "precipitation", 1)["value"]
    assert total == pytest.approx(31 * sum(rain) / len(rain))  # total = mean rate x days
    assert total != pytest.approx(sum(rain) / len(rain))
    warmest_day = max(source_values(recorded_envelope, "T2M_MAX", 1))
    mean_of_maxima = row(monthly, "air_temperature_max", 1)["value"]
    assert mean_of_maxima < warmest_day  # a mean of daily maxima, not the month's peak


def test_every_supported_variable_has_a_documented_rule():
    for parameter in POWER_PARAMETERS.values():
        rule = AGGREGATION_RULES[parameter.variable]
        assert rule.statistic in {"total", "mean"} and rule.method
    assert AGGREGATION_RULES["precipitation"].statistic == "total"
    assert all(
        rule.statistic == "mean" for name, rule in AGGREGATION_RULES.items() if name != "precipitation"
    )


# --- Months with gaps ----------------------------------------------------------------


def test_a_total_is_not_reported_for_a_month_with_any_gap(make_retrieval, recorded_envelope):
    def blank_one_day(payload):
        daily(payload, "PRECTOTCORR")["20200215"] = -999.0
        daily(payload, "T2M")["20200215"] = -999.0

    monthly = monthly_summary(build_dataset(make_retrieval(blank_one_day)))
    rain = row(monthly, "precipitation", 2)
    assert rain["reported"] == False and math.isnan(rain["value"])  # noqa: E712
    assert rain["days_valid"] == 28 and rain["completeness_percent"] == pytest.approx(96.55)

    temperature = row(monthly, "air_temperature_mean", 2)
    kept = [v for k, v in sorted(recorded_envelope["payload"]["properties"]["parameter"]["T2M"].items())
            if k.startswith("202002") and k != "20200215"]
    assert temperature["reported"] == True  # noqa: E712
    assert temperature["value"] == pytest.approx(sum(kept) / len(kept))
    assert row(monthly, "precipitation", 1)["reported"] == True  # noqa: E712


def test_a_mean_is_not_reported_when_too_many_days_are_missing(make_retrieval):
    def blank_a_week(payload):
        for day in range(1, 8):
            daily(payload, "T2M")[f"202003{day:02d}"] = -999.0

    monthly = monthly_summary(build_dataset(make_retrieval(blank_a_week)))
    march = row(monthly, "air_temperature_mean", 3)
    assert march["days_valid"] == 24 and march["completeness_percent"] == pytest.approx(77.42)
    assert march["reported"] == False and math.isnan(march["value"])  # noqa: E712


def test_month_thresholds_are_configurable(make_retrieval):
    def blank_one_day(payload):
        daily(payload, "PRECTOTCORR")["20200215"] = -999.0

    gappy = build_dataset(make_retrieval(blank_one_day))
    lenient = monthly_summary(gappy, total_min_completeness_percent=90)
    assert row(lenient, "precipitation", 2)["reported"] == True  # noqa: E712
    strict = monthly_summary(build_dataset(make_retrieval()), mean_min_completeness_percent=100)
    assert strict["reported"].all()
    for invalid in (-1, 101):
        with pytest.raises(ValueError, match="between 0 and 100"):
            monthly_summary(gappy, mean_min_completeness_percent=invalid)


def test_a_partly_requested_month_counts_as_incomplete(make_retrieval, recorded_request):
    shorter = PowerRequest(**{**recorded_request.model_dump(), "end": date(2020, 3, 15)})
    monthly = monthly_summary(build_dataset(make_retrieval(request=shorter)))
    march = row(monthly, "precipitation", 3)
    assert march["days_expected"] == 31 and march["days_valid"] == 15
    assert march["reported"] == False  # noqa: E712
    assert row(monthly, "air_temperature_mean", 3)["reported"] == False  # noqa: E712
    assert row(monthly, "precipitation", 2)["reported"] == True  # noqa: E712


def test_a_month_with_no_valid_days_is_not_reported(make_retrieval):
    def blank_january(payload):
        for key in list(daily(payload, "RH2M")):
            if key.startswith("202001"):
                daily(payload, "RH2M")[key] = -999.0

    monthly = monthly_summary(build_dataset(make_retrieval(blank_january)), mean_min_completeness_percent=0)
    january = row(monthly, "relative_humidity", 1)
    assert january["days_valid"] == 0 and january["reported"] == False  # noqa: E712
    assert math.isnan(january["value"])


# --- Descriptive summaries -----------------------------------------------------------


def test_climatology_averages_reported_months_only(make_retrieval, dataset):
    monthly = monthly_summary(dataset)
    climatology = monthly_climatology(monthly)
    assert len(climatology) == 6 * 3
    january = climatology[(climatology["variable"] == "precipitation") & (climatology["month"] == 1)].iloc[0]
    assert january["mean_value"] == pytest.approx(row(monthly, "precipitation", 1)["value"])
    assert january["lowest"] == january["highest"] == january["mean_value"]  # one year on record
    assert (january["years_used"], january["years_available"]) == (1, 1)
    assert january["statistic"] == "total" and january["unit"] == "mm"

    gappy = build_dataset(make_retrieval(lambda p: daily(p, "PRECTOTCORR").update({"20200215": -999.0})))
    thin = monthly_climatology(monthly_summary(gappy))
    february = thin[(thin["variable"] == "precipitation") & (thin["month"] == 2)].iloc[0]
    assert (february["years_used"], february["years_available"]) == (0, 1)
    assert math.isnan(february["mean_value"])


def test_quality_table_matches_the_quality_report(dataset):
    table = quality_table(dataset)
    assert len(table) == 6
    assert set(table["completeness_percent"]) == {100.0}
    assert list(table["variable"]) == list(dataset.variables)
    assert {"nasa_parameter", "days_expected", "days_valid", "days_missing", "minimum", "mean", "maximum"} <= set(table.columns)


def test_processing_module_implements_no_agronomy():
    import src.data_processing as module

    public = {name for name in vars(module) if not name.startswith("_")}
    forbidden = ("yield", "suitab", "score", "recommend", "forecast", "predict", "optimi")
    assert not [name for name in public if any(word in name.lower() for word in forbidden)]
