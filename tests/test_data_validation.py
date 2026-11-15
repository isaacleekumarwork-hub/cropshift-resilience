"""Validation and normalisation of NASA POWER responses.

The unaltered fixture is a real NASA response. Wherever a test changes a copy
of it, the changed values are test inputs and say so; they are never NASA data.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.data_validation import (
    LATENCY_WINDOW_DAYS,
    NOT_ENDORSED,
    POWER_REFERENCE,
    DatasetRejectedError,
    EnvironmentalDataset,
    IssueSeverity,
    StructuralValidationError,
    UnitMismatchError,
    ValidationLevel,
    build_dataset,
    classify_value,
)
from src.models import (
    DataKind,
    DataOrigin,
    MissingStatus,
    QualityFlag,
    TemporalResolution,
    TimeStandard,
    Unit,
)
from src.nasa_client import PowerRequest
from tests.conftest import daily

EXPECTED_DAYS = 91  # 1 January to 31 March 2020


def observation(dataset: EnvironmentalDataset, variable: str, day: date):
    series = dataset.get(variable)
    return next(item for item in series.observations if item.period_start == day)


def quality(dataset: EnvironmentalDataset, variable: str):
    return next(item for item in dataset.quality.variables if item.variable == variable)


def codes(dataset: EnvironmentalDataset) -> dict[str, int]:
    return {issue.code: issue.count for issue in dataset.quality.issues}


# --- The real response ---------------------------------------------------------------


def test_real_response_becomes_typed_observations(recorded_retrieval, recorded_envelope):
    dataset = build_dataset(recorded_retrieval, site_name="Fixture site")
    assert dataset.variables == (
        "solar_irradiance",
        "precipitation",
        "relative_humidity",
        "air_temperature_mean",
        "air_temperature_max",
        "air_temperature_min",
    )
    for series in dataset.series:
        assert len(series.observations) == EXPECTED_DAYS
        assert series.missing_count == 0
        assert series.observations[0].period_start == date(2020, 1, 1)
        assert series.observations[-1].period_start == date(2020, 3, 31)
    assert dataset.quality.accepted is True
    assert dataset.quality.issues == ()
    assert dataset.dataset_id == recorded_retrieval.request.cache_key()


def test_numbers_are_carried_over_unchanged(recorded_retrieval, recorded_envelope):
    dataset = build_dataset(recorded_retrieval)
    source = recorded_envelope["payload"]["properties"]["parameter"]
    for parameter, variable in [("T2M", "air_temperature_mean"), ("PRECTOTCORR", "precipitation")]:
        values = [item.value for item in dataset.get(variable).observations]
        assert values == [float(source[parameter][key]) for key in sorted(source[parameter])]


def test_each_value_keeps_its_unit_place_time_and_source(recorded_retrieval):
    dataset = build_dataset(recorded_retrieval, site_name="Fixture site")
    rain = observation(dataset, "precipitation", date(2020, 1, 1))
    assert rain.unit is Unit.MILLIMETRE_PER_DAY
    assert (rain.location.latitude, rain.location.longitude) == (-1.58, 37.24)
    assert rain.location.name == "Fixture site"
    assert rain.temporal_resolution is TemporalResolution.DAILY
    assert rain.quality is QualityFlag.PASSED and rain.missing is MissingStatus.PRESENT
    record = rain.provenance
    assert record.kind is DataKind.REANALYSIS
    assert record.source_id == "nasa-power" and "MERRA-2" in record.source_name
    assert record.source_version == "v2.10.3"
    assert record.retrieved_at == recorded_retrieval.retrieved_at
    assert record.time_standard is TimeStandard.UTC
    assert "0.5°" in record.spatial_resolution
    assert record.url == recorded_retrieval.url
    assert record.citation == POWER_REFERENCE

    sun = observation(dataset, "solar_irradiance", date(2020, 1, 1))
    assert sun.provenance.kind is DataKind.SATELLITE_RETRIEVAL
    assert sun.unit is Unit.MEGAJOULE_PER_M2_PER_DAY and "1°" in sun.provenance.spatial_resolution
    assert observation(dataset, "air_temperature_mean", date(2020, 1, 1)).unit is Unit.DEGREE_CELSIUS


def test_dataset_survives_a_json_round_trip(recorded_retrieval):
    dataset = build_dataset(recorded_retrieval)
    assert EnvironmentalDataset.model_validate_json(dataset.model_dump_json()) == dataset


# --- Provenance ----------------------------------------------------------------------


def test_dataset_provenance_is_complete(recorded_retrieval):
    record = build_dataset(recorded_retrieval).provenance
    assert record.service_name == "NASA POWER Daily API" and record.service_version == "v2.10.3"
    assert record.official_url == "https://power.larc.nasa.gov/"
    assert record.request_url == recorded_retrieval.url
    assert record.request_parameters["time-standard"] == "UTC"
    assert record.request_parameters["community"] == "AG"
    assert (record.requested_location.latitude, record.requested_location.longitude) == (-1.58, 37.24)
    assert record.returned_location.elevation_m == pytest.approx(1327.62)
    assert (record.requested_start, record.requested_end) == (date(2020, 1, 1), date(2020, 3, 31))
    assert (record.returned_start, record.returned_end) == (date(2020, 1, 1), date(2020, 3, 31))
    assert record.retrieved_at == recorded_retrieval.retrieved_at
    assert record.origin is DataOrigin.NETWORK
    assert record.payload_sha256 == recorded_retrieval.payload_sha256
    assert "MERRA2" in record.upstream_products
    assert record.temporal_resolution is TemporalResolution.DAILY
    assert record.time_standard is TimeStandard.UTC
    assert "0.5°" in record.spatial_resolution and "1°" in record.spatial_resolution
    assert record.units["precipitation"] is Unit.MILLIMETRE_PER_DAY
    assert record.units["air_temperature_mean"] is Unit.DEGREE_CELSIUS
    assert any("no change to any number" in step for step in record.transformations)
    assert "Nothing is interpolated, filled or replaced with zero" in record.missing_data_treatment


def test_citations_follow_the_nasa_power_referencing_guide(recorded_retrieval):
    citations = build_dataset(recorded_retrieval).provenance.citations
    assert citations[0] == POWER_REFERENCE
    assert citations[1] == "The data was obtained from the POWER Project's Daily v2.10.3 version on 2026/11/14."
    assert any("MERRA-2" in item and "10.1175/JCLI-D-16-0758.1" in item for item in citations)


def test_caveats_state_the_limits_and_never_imply_endorsement(recorded_retrieval):
    caveats = " ".join(build_dataset(recorded_retrieval).provenance.caveats)
    assert "not measurements from an individual farm" in caveats
    assert "not a forecast" in caveats
    assert "reanalysis" in caveats
    assert NOT_ENDORSED in caveats


def test_near_real_time_sources_add_a_caveat(make_retrieval):
    def use_recent_systems(payload):
        payload["header"]["sources"] = ["GEOSIT", "FLASHFLUX"]  # test input

    caveats = " ".join(build_dataset(make_retrieval(use_recent_systems)).provenance.caveats)
    assert "may be revised" in caveats


def test_origin_is_carried_into_provenance(make_retrieval):
    for origin in DataOrigin:
        assert build_dataset(make_retrieval(origin=origin)).provenance.origin is origin


# --- Level 1: structure --------------------------------------------------------------


@pytest.mark.parametrize(
    ("alter", "expected"),
    [
        (lambda p: p.pop("header"), "no 'header' section"),
        (lambda p: p.pop("properties"), "no 'properties.parameter' section"),
        (lambda p: p["header"].pop("fill_value"), "fill_value is missing"),
        (lambda p: p["header"].update(fill_value="none"), "fill_value is missing or not a number"),
        (lambda p: p["header"].update(time_standard="LST"), "time standard 'LST'"),
        (lambda p: p.pop("geometry"), "geometry.coordinates"),
        (lambda p: p["geometry"].update(coordinates=["east", "south"]), "geometry.coordinates"),
        (lambda p: p["geometry"].update(coordinates=[10.0, 50.0, 100.0]), "different coordinates"),
        (lambda p: p.pop("parameters"), "metadata section is missing"),
        (lambda p: p["parameters"]["T2M"].pop("units"), "no unit is given for T2M"),
        (lambda p: p["properties"]["parameter"].pop("PRECTOTCORR"), "PRECTOTCORR is missing"),
        (lambda p: p["properties"]["parameter"].update(T2M={}), "T2M is missing"),
        (lambda p: p["properties"]["parameter"].update(T2M=[1, 2]), "T2M is missing"),
        (lambda p: daily(p, "T2M").update({"2020-01-05": 20.0}), "invalid date key"),
        (lambda p: daily(p, "T2M").update({"20201345": 20.0}), "invalid date key"),
        (lambda p: daily(p, "T2M").update({"": 20.0}), "invalid date key"),
    ],
)
def test_structural_failures_reject_the_whole_response(alter, expected, make_retrieval):
    with pytest.raises(StructuralValidationError, match=expected):
        build_dataset(make_retrieval(alter))


def test_many_structural_problems_are_summarised(make_retrieval):
    def break_many(payload):
        for index in range(12):
            daily(payload, "T2M")[f"bad-{index}"] = 1.0

    with pytest.raises(StructuralValidationError, match=r"and 7 more"):
        build_dataset(make_retrieval(break_many))


def test_unexpected_parameters_are_ignored_with_a_warning(make_retrieval):
    def add_extra(payload):
        payload["properties"]["parameter"]["WS2M"] = {"20200101": 3.0}  # test input

    dataset = build_dataset(make_retrieval(add_extra))
    assert "wind_speed" not in dataset.variables
    issue = next(item for item in dataset.quality.issues if item.code == "unexpected_parameters")
    assert issue.severity is IssueSeverity.WARNING and "WS2M" in issue.message
    assert issue.level is ValidationLevel.STRUCTURAL


def test_dates_outside_the_request_are_ignored_with_a_note(make_retrieval):
    def add_stray(payload):
        daily(payload, "T2M")["20200401"] = 21.0  # test input

    dataset = build_dataset(make_retrieval(add_stray))
    assert len(dataset.get("air_temperature_mean").observations) == EXPECTED_DAYS
    assert codes(dataset) == {"dates_outside_request": 1}


def test_requesting_fewer_parameters_than_returned_still_works(make_retrieval, recorded_request):
    narrow = PowerRequest(**{**recorded_request.model_dump(), "parameters": ("T2M", "PRECTOTCORR")})
    dataset = build_dataset(make_retrieval(request=narrow))
    assert dataset.variables == ("precipitation", "air_temperature_mean")


# --- Level 2: units ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("parameter", "unit"),
    [("T2M", "K"), ("PRECTOTCORR", "mm/hour"), ("ALLSKY_SFC_SW_DWN", "kW-hr/m^2/day"), ("RH2M", "1")],
)
def test_unexpected_units_are_refused_not_converted(parameter, unit, make_retrieval):
    def change_unit(payload):
        payload["parameters"][parameter]["units"] = unit  # test input

    with pytest.raises(UnitMismatchError, match="refusing to guess"):
        build_dataset(make_retrieval(change_unit))


# --- Level 2: missing values ---------------------------------------------------------


def test_fill_value_becomes_an_explicit_gap_never_zero(make_retrieval):
    def blank_one_day(payload):
        daily(payload, "PRECTOTCORR")["20200105"] = -999.0  # the source's own marker

    dataset = build_dataset(make_retrieval(blank_one_day))
    gap = observation(dataset, "precipitation", date(2020, 1, 5))
    assert gap.value is None and gap.value != 0
    assert gap.missing is MissingStatus.MISSING_AT_SOURCE
    assert gap.quality is QualityFlag.NOT_ASSESSED
    assert dataset.get("precipitation").missing_count == 1
    assert codes(dataset) == {"fill_value": 1}


def test_fill_value_is_read_from_the_response_header(make_retrieval):
    def use_other_marker(payload):
        payload["header"]["fill_value"] = -9999.0
        daily(payload, "T2M")["20200110"] = -9999.0

    dataset = build_dataset(make_retrieval(use_other_marker))
    assert observation(dataset, "air_temperature_mean", date(2020, 1, 10)).missing is MissingStatus.MISSING_AT_SOURCE


def test_null_becomes_an_explicit_gap(make_retrieval):
    dataset = build_dataset(make_retrieval(lambda p: daily(p, "T2M").update({"20200203": None})))
    gap = observation(dataset, "air_temperature_mean", date(2020, 2, 3))
    assert gap.value is None and gap.missing is MissingStatus.MISSING_AT_SOURCE
    assert "Null" in gap.quality_note
    assert codes(dataset) == {"null_value": 1}


@pytest.mark.parametrize("bad", ["12.5", "n/a", True, [1.0], {"v": 1}])
def test_non_numeric_values_are_discarded_not_coerced(bad, make_retrieval):
    dataset = build_dataset(make_retrieval(lambda p: daily(p, "RH2M").update({"20200115": bad})))
    rejected = observation(dataset, "relative_humidity", date(2020, 1, 15))
    assert rejected.value is None
    assert rejected.missing is MissingStatus.REJECTED_BY_VALIDATION
    assert rejected.quality is QualityFlag.FAILED
    issue = next(item for item in dataset.quality.issues if item.code == "non_numeric_value")
    assert issue.severity is IssueSeverity.ERROR


def test_missing_dates_become_gaps(make_retrieval):
    def drop_days(payload):
        for key in ("20200210", "20200211"):
            del daily(payload, "ALLSKY_SFC_SW_DWN")[key]

    dataset = build_dataset(make_retrieval(drop_days))
    series = dataset.get("solar_irradiance")
    assert len(series.observations) == EXPECTED_DAYS  # every expected day is still represented
    gap = observation(dataset, "solar_irradiance", date(2020, 2, 10))
    assert gap.value is None and "absent" in gap.quality_note
    assert codes(dataset) == {"missing_date": 2}
    assert quality(dataset, "solar_irradiance").missing_count == 2


def test_recent_trailing_gaps_are_labelled_not_yet_available(make_retrieval):
    def blank_tail(payload):
        for key in ("20200329", "20200330", "20200331"):
            daily(payload, "T2M")[key] = -999.0
        daily(payload, "T2M")["20200301"] = -999.0  # an older gap, not a trailing one

    soon_after = datetime(2020, 4, 5, tzinfo=timezone.utc)
    dataset = build_dataset(make_retrieval(blank_tail, retrieved_at=soon_after))
    assert observation(dataset, "air_temperature_mean", date(2020, 3, 31)).missing is MissingStatus.NOT_YET_AVAILABLE
    assert observation(dataset, "air_temperature_mean", date(2020, 3, 29)).missing is MissingStatus.NOT_YET_AVAILABLE
    assert observation(dataset, "air_temperature_mean", date(2020, 3, 1)).missing is MissingStatus.MISSING_AT_SOURCE
    assert codes(dataset) == {"fill_value": 1, "not_yet_available": 3}

    much_later = build_dataset(make_retrieval(blank_tail))  # retrieved in November 2026
    assert LATENCY_WINDOW_DAYS < 2000
    assert observation(much_later, "air_temperature_mean", date(2020, 3, 31)).missing is MissingStatus.MISSING_AT_SOURCE


# --- Level 2: impossible and suspicious values ---------------------------------------


@pytest.mark.parametrize(
    ("parameter", "variable", "value"),
    [
        ("PRECTOTCORR", "precipitation", -5.0),
        ("RH2M", "relative_humidity", 150.0),
        ("T2M", "air_temperature_mean", 95.0),
        ("ALLSKY_SFC_SW_DWN", "solar_irradiance", -1.0),
        ("T2M_MIN", "air_temperature_min", -9999.0),
    ],
)
def test_impossible_values_are_discarded_and_flagged(parameter, variable, value, make_retrieval):
    dataset = build_dataset(make_retrieval(lambda p: daily(p, parameter).update({"20200120": value})))
    rejected = observation(dataset, variable, date(2020, 1, 20))
    assert rejected.value is None
    assert rejected.missing is MissingStatus.REJECTED_BY_VALIDATION
    assert rejected.quality is QualityFlag.FAILED and "physically impossible" in rejected.quality_note
    summary = quality(dataset, variable)
    assert summary.rejected_count == 1 and summary.valid_count == EXPECTED_DAYS - 1
    issue = next(item for item in dataset.quality.issues if item.code == "impossible_value")
    assert issue.severity is IssueSeverity.ERROR and issue.level is ValidationLevel.PHYSICAL


@pytest.mark.parametrize(
    ("parameter", "variable", "value"),
    [
        ("PRECTOTCORR", "precipitation", 650.0),
        ("T2M_MAX", "air_temperature_max", 57.0),
        ("ALLSKY_SFC_SW_DWN", "solar_irradiance", 45.0),
    ],
)
def test_unusual_values_are_kept_and_flagged_suspect(parameter, variable, value, make_retrieval):
    dataset = build_dataset(make_retrieval(lambda p: daily(p, parameter).update({"20200120": value})))
    kept = observation(dataset, variable, date(2020, 1, 20))
    assert kept.value == value  # not altered, not removed
    assert kept.missing is MissingStatus.PRESENT and kept.quality is QualityFlag.SUSPECT
    summary = quality(dataset, variable)
    assert summary.suspect_count == 1 and summary.valid_count == EXPECTED_DAYS
    assert any(item.code == "suspicious_value" and item.severity is IssueSeverity.WARNING for item in dataset.quality.issues)
    assert dataset.quality.accepted is True  # unusual is not the same as invalid


def test_temperatures_out_of_order_are_flagged_suspect(make_retrieval):
    def swap(payload):
        daily(payload, "T2M_MIN")["20200125"] = 30.0  # above that day's mean: test input

    dataset = build_dataset(make_retrieval(swap))
    for variable in ("air_temperature_min", "air_temperature_mean", "air_temperature_max"):
        assert observation(dataset, variable, date(2020, 1, 25)).quality is QualityFlag.SUSPECT
    assert observation(dataset, "air_temperature_mean", date(2020, 1, 26)).quality is QualityFlag.PASSED
    assert codes(dataset)["temperature_order"] == 1


def test_classification_never_changes_a_valid_number():
    cell = classify_value(12.345678, fill_value=-999.0, variable="precipitation", day=date(2020, 1, 1))
    assert cell.value == 12.345678 and cell.quality is QualityFlag.PASSED
    zero = classify_value(0, fill_value=-999.0, variable="precipitation", day=date(2020, 1, 1))
    assert zero.value == 0.0 and zero.missing is MissingStatus.PRESENT  # a real dry day stays zero


# --- Level 3: completeness -----------------------------------------------------------


def test_completeness_is_counted_per_variable(make_retrieval):
    def blank_nine(payload):
        for day in range(1, 10):
            daily(payload, "PRECTOTCORR")[f"202002{day:02d}"] = -999.0

    dataset = build_dataset(make_retrieval(blank_nine))
    rain = quality(dataset, "precipitation")
    assert (rain.expected_count, rain.valid_count, rain.missing_count) == (91, 82, 9)
    assert rain.completeness_percent == pytest.approx(90.11)
    assert (rain.first_valid_date, rain.last_valid_date) == (date(2020, 1, 1), date(2020, 3, 31))
    other = quality(dataset, "air_temperature_mean")
    assert (other.valid_count, other.completeness_percent) == (91, 100.0)
    assert dataset.quality.expected_days == 91
    assert dataset.quality.lowest_completeness_percent == pytest.approx(90.11)
    assert dataset.quality.accepted is True  # 90.11 % meets the 90 % minimum


def test_descriptive_statistics_ignore_gaps(make_retrieval, recorded_envelope):
    source = recorded_envelope["payload"]["properties"]["parameter"]["T2M"]
    kept = [value for key, value in source.items() if key != "20200101"]
    dataset = build_dataset(make_retrieval(lambda p: daily(p, "T2M").update({"20200101": -999.0})))
    summary = quality(dataset, "air_temperature_mean")
    assert summary.minimum == min(kept) and summary.maximum == max(kept)
    assert summary.mean == pytest.approx(sum(kept) / len(kept), abs=1e-4)
    assert summary.first_valid_date == date(2020, 1, 2)


def test_dataset_below_the_threshold_is_not_accepted(make_retrieval):
    def blank_ten(payload):
        for day in range(1, 11):
            daily(payload, "PRECTOTCORR")[f"202002{day:02d}"] = -999.0

    dataset = build_dataset(make_retrieval(blank_ten))
    assert quality(dataset, "precipitation").completeness_percent == pytest.approx(89.01)
    assert dataset.quality.accepted is False
    error = dataset.quality.errors[0]
    assert error.code == "completeness_below_threshold" and error.level is ValidationLevel.COMPLETENESS
    assert "PRECTOTCORR is 89.01% complete, below the required 90%" in error.message
    with pytest.raises(DatasetRejectedError, match="89.01% complete"):
        dataset.require_accepted()


def test_completeness_threshold_is_configurable(make_retrieval):
    def blank_ten(payload):
        for day in range(1, 11):
            daily(payload, "PRECTOTCORR")[f"202002{day:02d}"] = -999.0

    retrieval = make_retrieval(blank_ten)
    lenient = build_dataset(retrieval, min_completeness_percent=80)
    assert lenient.quality.accepted is True and lenient.require_accepted() is lenient
    strict = build_dataset(make_retrieval(), min_completeness_percent=100)
    assert strict.quality.accepted is True
    assert build_dataset(retrieval, min_completeness_percent=100).quality.accepted is False
    for invalid in (-1, 100.5):
        with pytest.raises(ValueError, match="between 0 and 100"):
            build_dataset(retrieval, min_completeness_percent=invalid)


def test_a_variable_with_no_valid_values_is_reported_honestly(make_retrieval):
    def blank_all(payload):
        for key in daily(payload, "RH2M"):
            daily(payload, "RH2M")[key] = -999.0

    dataset = build_dataset(make_retrieval(blank_all))
    summary = quality(dataset, "relative_humidity")
    assert summary.valid_count == 0 and summary.completeness_percent == 0.0
    assert summary.minimum is None and summary.mean is None and summary.first_valid_date is None
    assert dataset.quality.accepted is False


def test_passing_validation_is_not_presented_as_proof_of_accuracy():
    import src.data_validation as module

    assert "does not show that the values are accurate" in module.__doc__
