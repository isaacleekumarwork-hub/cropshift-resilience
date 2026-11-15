"""Scientific data contracts: required fields, invalid values, gaps and units.

Every number in this file is a fixture chosen to exercise a rule. None is a
real observation or a real agronomic parameter.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src import models
from src.models import DataKind, MissingStatus, TemporalResolution, Unit
from tests.conftest import FIXED_DAY, FIXED_TIME

TOMORROW_PLUS = datetime.now(timezone.utc).date() + timedelta(days=3)


def soil_value(variable: str, value: float | None, unit: Unit, provenance, **extra):
    return models.ScientificValue(variable=variable, value=value, unit=unit, provenance=provenance, **extra)


# --- 1. Geographic location ---------------------------------------------------


def test_location_accepts_valid_coordinates(location):
    assert location.coordinate_reference == "EPSG:4326"


@pytest.mark.parametrize(
    "fields",
    [
        {"latitude": 90.1, "longitude": 0},
        {"latitude": -90.1, "longitude": 0},
        {"latitude": 0, "longitude": 180.1},
        {"latitude": 0, "longitude": -180.1},
        {"latitude": float("nan"), "longitude": 0},
        {"latitude": 0, "longitude": 0, "country_code": "usa"},
        {"latitude": 0, "longitude": 0, "elevation_m": 20000},
    ],
)
def test_location_rejects_invalid_values(fields):
    with pytest.raises(ValidationError):
        models.GeoLocation(**fields)


def test_location_requires_both_coordinates():
    with pytest.raises(ValidationError):
        models.GeoLocation(latitude=1.0)


def test_contracts_are_immutable_and_reject_unknown_fields(location):
    with pytest.raises(ValidationError):
        location.latitude = 0.0
    with pytest.raises(ValidationError):
        models.GeoLocation(latitude=0, longitude=0, altitude=5)


# --- 12. Provenance -----------------------------------------------------------


def test_observation_based_provenance_needs_timestamp_and_citation(reanalysis):
    assert reanalysis.is_observation_based
    base = reanalysis.model_dump()
    with pytest.raises(ValidationError, match="retrieval timestamp"):
        models.ProvenanceRecord(**{**base, "retrieved_at": None})
    with pytest.raises(ValidationError, match="citation"):
        models.ProvenanceRecord(**{**base, "citation": None})


def test_retrieval_timestamp_must_have_a_time_zone_and_not_be_in_the_future(reanalysis):
    base = reanalysis.model_dump()
    with pytest.raises(ValidationError):
        models.ProvenanceRecord(**{**base, "retrieved_at": datetime(2026, 11, 14, 2, 0, 0)})
    with pytest.raises(ValidationError, match="future"):
        models.ProvenanceRecord(
            **{**base, "retrieved_at": datetime.now(timezone.utc) + timedelta(days=2)}
        )


def test_assumed_values_must_state_the_assumption():
    fields = dict(kind=DataKind.ASSUMED, source_id="assumption", source_name="Default")
    with pytest.raises(ValidationError, match="assumption"):
        models.ProvenanceRecord(**fields)
    assert models.ProvenanceRecord(**fields, assumption="Fixture assumption").assumption


def test_literature_values_need_a_citation():
    with pytest.raises(ValidationError, match="citation"):
        models.ProvenanceRecord(kind=DataKind.LITERATURE_VALUE, source_id="ref", source_name="Ref")


@pytest.mark.parametrize("kind", [DataKind.DERIVED, DataKind.MODELED])
def test_calculated_values_must_describe_the_calculation(kind):
    with pytest.raises(ValidationError, match="calculated"):
        models.ProvenanceRecord(kind=kind, source_id="engine", source_name="Engine")


def test_provenance_requires_source_fields():
    with pytest.raises(ValidationError):
        models.ProvenanceRecord(kind=DataKind.USER_REPORTED)
    with pytest.raises(ValidationError):
        models.ProvenanceRecord(kind=DataKind.USER_REPORTED, source_id="user", source_name="   ")


# --- 2. Data source metadata --------------------------------------------------


def source_fields(**overrides):
    fields = dict(
        source_id="test-source",
        name="Test source",
        provider="Test provider",
        kind=DataKind.REANALYSIS,
        description="Fixture source, not a real dataset",
        url="https://example.org/",
        citation="Fixture citation",
        license="Fixture licence",
        spatial_resolution="0.5° x 0.625°",
        spatial_coverage="Global",
        temporal_resolution=TemporalResolution.DAILY,
        coverage_start=date(1981, 1, 1),
        latency="Fixture latency",
        access_method="Fixture API",
        requires_authentication=False,
        variables=("precipitation", "air_temperature_mean"),
    )
    fields.update(overrides)
    return fields


def test_data_source_accepts_valid_metadata():
    source = models.DataSourceMetadata(**source_fields())
    assert source.coverage_end is None  # ongoing record


def test_data_source_rejects_inconsistent_metadata():
    with pytest.raises(ValidationError, match="coverage_end"):
        models.DataSourceMetadata(**source_fields(coverage_end=date(1980, 1, 1)))
    with pytest.raises(ValidationError, match="unknown variable"):
        models.DataSourceMetadata(**source_fields(variables=("not_a_variable",)))
    with pytest.raises(ValidationError, match="repeat"):
        models.DataSourceMetadata(**source_fields(variables=("precipitation", "precipitation")))
    with pytest.raises(ValidationError):
        models.DataSourceMetadata(**source_fields(source_id="Not A Slug"))


def test_data_source_requires_citation_and_licence():
    for name in ("citation", "license", "url", "latency"):
        fields = source_fields()
        del fields[name]
        with pytest.raises(ValidationError):
            models.DataSourceMetadata(**fields)


# --- Variable registry and units ----------------------------------------------


def test_registry_holds_one_unit_per_variable():
    names = [definition.name for definition in models.registered_variables()]
    assert len(names) == len(set(names))
    assert models.get_variable("precipitation").unit is Unit.MILLIMETRE_PER_DAY
    assert models.get_variable("air_temperature_mean").unit is Unit.DEGREE_CELSIUS


def test_registry_can_be_filtered_by_domain():
    soil = models.registered_variables(models.VariableDomain.SOIL)
    assert soil and all(item.domain is models.VariableDomain.SOIL for item in soil)
    # A1 declared no indicators and left them to the A4 engine. The engine
    # declares exactly three descriptive ones; nothing else may appear.
    import src.comparison_engine  # noqa: F401  (registers the A4 indicator variables)

    indicators = models.registered_variables(models.VariableDomain.INDICATOR)
    assert {item.name for item in indicators} == {
        "indicator_season_rainfall_total",
        "indicator_frost_days",
        "indicator_family_count",
    }


def test_unknown_variable_is_rejected(make_observation):
    with pytest.raises(models.UnknownVariableError):
        models.get_variable("made_up_variable")
    with pytest.raises(ValidationError, match="unknown variable"):
        make_observation(variable="made_up_variable")


def test_duplicate_registration_is_rejected():
    existing = models.get_variable("precipitation")
    with pytest.raises(ValueError, match="already registered"):
        models.register_variable(existing)


def test_variable_limits_must_be_ordered():
    with pytest.raises(ValidationError):
        models.VariableDefinition(
            name="bad_limits",
            domain=models.VariableDomain.SOIL,
            unit=Unit.PERCENT,
            description="Fixture",
            valid_min=10,
            valid_max=1,
        )


def test_wrong_unit_is_rejected(make_observation):
    with pytest.raises(ValidationError, match="must use unit 'mm/day'"):
        make_observation(unit=Unit.MILLIMETRE)
    with pytest.raises(ValidationError, match="must use unit 'degC'"):
        make_observation(variable="air_temperature_mean", value=20.0, unit=Unit.PERCENT)


def test_unit_outside_the_vocabulary_is_rejected(make_observation):
    with pytest.raises(ValidationError):
        make_observation(unit="inches")


# --- 3. Environmental observation: values and gaps ----------------------------


def test_valid_observation(make_observation):
    observation = make_observation()
    assert observation.value == 3.2
    assert observation.is_missing is False
    assert observation.quality is models.QualityFlag.NOT_ASSESSED


@pytest.mark.parametrize("missing_field", ["variable", "unit", "provenance", "location", "period_start"])
def test_observation_requires_core_fields(make_observation, missing_field):
    fields = make_observation().model_dump()
    del fields[missing_field]
    with pytest.raises(ValidationError):
        models.EnvironmentalObservation(**fields)


def test_value_must_be_given_explicitly(make_observation):
    fields = make_observation().model_dump()
    del fields["value"]
    with pytest.raises(ValidationError):
        models.EnvironmentalObservation(**fields)


def test_gap_is_represented_explicitly(make_observation):
    gap = make_observation(value=None, missing=MissingStatus.MISSING_AT_SOURCE)
    assert gap.is_missing is True
    assert gap.value is None


def test_missing_number_without_a_reason_is_rejected(make_observation):
    with pytest.raises(ValidationError, match="explicit missing status"):
        make_observation(value=None)


def test_value_flagged_missing_cannot_carry_a_number(make_observation):
    with pytest.raises(ValidationError, match="must not carry a number"):
        make_observation(value=1.0, missing=MissingStatus.NOT_YET_AVAILABLE)


@pytest.mark.parametrize("sentinel", [-999.0, -9999.0, float("nan"), float("inf")])
def test_sentinel_and_non_finite_values_are_rejected(make_observation, sentinel):
    with pytest.raises(ValidationError):
        make_observation(value=sentinel)
    with pytest.raises(ValidationError):
        make_observation(variable="air_temperature_mean", unit=Unit.DEGREE_CELSIUS, value=sentinel)


@pytest.mark.parametrize(
    ("variable", "unit", "value"),
    [
        ("precipitation", Unit.MILLIMETRE_PER_DAY, -0.1),
        ("relative_humidity", Unit.PERCENT, 100.5),
        ("root_zone_soil_wetness", Unit.FRACTION, 1.2),
        ("air_temperature_max", Unit.DEGREE_CELSIUS, 75.0),
    ],
)
def test_physically_impossible_values_are_rejected(make_observation, variable, unit, value):
    with pytest.raises(ValidationError, match="physical"):
        make_observation(variable=variable, unit=unit, value=value)


def test_observation_period_rules(make_observation):
    with pytest.raises(ValidationError, match="before period_start"):
        make_observation(
            period_end=FIXED_DAY - timedelta(days=1), temporal_resolution=TemporalResolution.MONTHLY
        )
    with pytest.raises(ValidationError, match="same day"):
        make_observation(period_end=FIXED_DAY + timedelta(days=1))
    monthly = make_observation(
        period_start=date(2024, 7, 1),
        period_end=date(2024, 7, 31),
        temporal_resolution=TemporalResolution.MONTHLY,
    )
    assert monthly.period_end > monthly.period_start


def test_observation_cannot_be_in_the_future(make_observation):
    with pytest.raises(ValidationError, match="does not forecast"):
        make_observation(period_start=TOMORROW_PLUS, period_end=TOMORROW_PLUS)


def test_observation_cannot_be_modeled_or_assumed(make_observation, modeled):
    with pytest.raises(ValidationError, match="environmental observation must be"):
        make_observation(provenance=modeled)


def test_observation_cannot_hold_a_soil_variable(make_observation):
    with pytest.raises(ValidationError, match="not an environmental variable"):
        make_observation(variable="soil_ph", unit=Unit.PH, value=6.5)


# --- Observation series: no mixing --------------------------------------------


def test_series_accepts_ordered_days_and_counts_gaps(make_observation):
    series = models.ObservationSeries(
        observations=[
            make_observation(),
            make_observation(
                period_start=FIXED_DAY + timedelta(days=1),
                period_end=FIXED_DAY + timedelta(days=1),
                value=None,
                missing=MissingStatus.MISSING_AT_SOURCE,
            ),
        ]
    )
    assert series.variable == "precipitation"
    assert series.unit is Unit.MILLIMETRE_PER_DAY
    assert series.missing_count == 1


def test_series_cannot_be_empty():
    with pytest.raises(ValidationError):
        models.ObservationSeries(observations=[])


def test_series_cannot_mix_variables_resolutions_or_time_standards(make_observation, reanalysis):
    next_day = dict(period_start=FIXED_DAY + timedelta(days=1), period_end=FIXED_DAY + timedelta(days=1))
    first = make_observation()

    with pytest.raises(ValidationError, match="mix variables"):
        models.ObservationSeries(
            observations=[
                first,
                make_observation(variable="air_temperature_mean", unit=Unit.DEGREE_CELSIUS, **next_day),
            ]
        )
    with pytest.raises(ValidationError, match="mix temporal resolutions"):
        models.ObservationSeries(
            observations=[
                first,
                make_observation(
                    period_start=date(2024, 8, 1),
                    period_end=date(2024, 8, 31),
                    temporal_resolution=TemporalResolution.MONTHLY,
                ),
            ]
        )
    local_time = reanalysis.model_copy(update={"time_standard": models.TimeStandard.LOCAL_SOLAR_TIME})
    with pytest.raises(ValidationError, match="mix time standards"):
        models.ObservationSeries(observations=[first, make_observation(provenance=local_time, **next_day)])
    other_source = reanalysis.model_copy(update={"source_id": "another-source"})
    with pytest.raises(ValidationError, match="mix data sources"):
        models.ObservationSeries(observations=[first, make_observation(provenance=other_source, **next_day)])


def test_series_must_be_chronological(make_observation):
    with pytest.raises(ValidationError, match="chronological"):
        models.ObservationSeries(observations=[make_observation(), make_observation()])


# --- 4. Soil information ------------------------------------------------------


def soil_fields(location, provenance, **overrides):
    fields = dict(
        location=location,
        depth_top_cm=0,
        depth_bottom_cm=30,
        texture_class=models.SoilTextureClass.LOAM,
        texture_provenance=provenance,
        properties=(
            soil_value("soil_sand_content", 40.0, Unit.PERCENT, provenance),
            soil_value("soil_silt_content", 40.0, Unit.PERCENT, provenance),
            soil_value("soil_clay_content", 20.0, Unit.PERCENT, provenance),
            soil_value("soil_ph", 6.5, Unit.PH, provenance),
        ),
    )
    fields.update(overrides)
    return fields


def test_valid_soil_information(location, user_reported):
    soil = models.SoilInformation(**soil_fields(location, user_reported))
    assert soil.get("soil_ph").value == 6.5
    assert soil.get("soil_bulk_density") is None  # unknown stays unknown


def test_soil_properties_are_optional_but_gaps_stay_explicit(location, user_reported):
    soil = models.SoilInformation(
        **soil_fields(
            location,
            user_reported,
            properties=(
                soil_value(
                    "soil_organic_carbon",
                    None,
                    Unit.GRAM_PER_KILOGRAM,
                    user_reported,
                    missing=MissingStatus.NOT_PROVIDED,
                ),
            ),
        )
    )
    assert soil.get("soil_organic_carbon").is_missing


def test_soil_texture_fractions_must_total_100(location, user_reported):
    with pytest.raises(ValidationError, match="total 100"):
        models.SoilInformation(
            **soil_fields(
                location,
                user_reported,
                properties=(
                    soil_value("soil_sand_content", 60.0, Unit.PERCENT, user_reported),
                    soil_value("soil_silt_content", 40.0, Unit.PERCENT, user_reported),
                    soil_value("soil_clay_content", 20.0, Unit.PERCENT, user_reported),
                ),
            )
        )


def test_soil_rejects_invalid_values(location, user_reported, make_observation):
    with pytest.raises(ValidationError, match="physical"):
        soil_value("soil_ph", 15.0, Unit.PH, user_reported)
    with pytest.raises(ValidationError, match="depth_bottom_cm"):
        models.SoilInformation(**soil_fields(location, user_reported, depth_top_cm=30, depth_bottom_cm=30))
    with pytest.raises(ValidationError, match="texture class needs provenance"):
        models.SoilInformation(**soil_fields(location, user_reported, texture_provenance=None))
    with pytest.raises(ValidationError, match="not a soil variable"):
        models.SoilInformation(**soil_fields(location, user_reported, properties=(make_observation(),)))
    with pytest.raises(ValidationError, match="must not repeat"):
        models.SoilInformation(
            **soil_fields(
                location,
                user_reported,
                properties=(
                    soil_value("soil_ph", 6.5, Unit.PH, user_reported),
                    soil_value("soil_ph", 6.6, Unit.PH, user_reported),
                ),
            )
        )
    with pytest.raises(ValidationError, match="field capacity"):
        models.SoilInformation(
            **soil_fields(
                location,
                user_reported,
                properties=(
                    soil_value("soil_field_capacity", 0.10, Unit.CUBIC_METRE_PER_CUBIC_METRE, user_reported),
                    soil_value("soil_wilting_point", 0.20, Unit.CUBIC_METRE_PER_CUBIC_METRE, user_reported),
                ),
            )
        )


# --- 5. Crop profile ----------------------------------------------------------


def crop_fields(literature, **overrides):
    fields = dict(
        crop_id="test-crop",
        common_name="Test crop",
        botanical_family="Testaceae",
        functional_group=models.CropFunctionalGroup.LEGUME,
        nitrogen_fixing=True,
        properties=(soil_value("crop_cycle_length", 100.0, Unit.DAY, literature),),
        sources=(literature,),
    )
    fields.update(overrides)
    return fields


def test_valid_crop_profile(literature):
    crop = models.CropProfile(**crop_fields(literature))
    assert crop.get("crop_cycle_length").unit is Unit.DAY
    assert crop.get("crop_max_rooting_depth") is None


def test_crop_profile_requires_evidence_and_identity(literature):
    with pytest.raises(ValidationError):
        models.CropProfile(**crop_fields(literature, sources=()))
    for name in ("crop_id", "common_name", "botanical_family", "functional_group", "nitrogen_fixing"):
        fields = crop_fields(literature)
        del fields[name]
        with pytest.raises(ValidationError):
            models.CropProfile(**fields)


def test_crop_profile_rejects_invalid_parameters(literature):
    with pytest.raises(ValidationError, match="must use unit 'day'"):
        soil_value("crop_cycle_length", 100.0, Unit.MILLIMETRE, literature)
    with pytest.raises(ValidationError, match="physical"):
        soil_value("crop_cycle_length", 0.0, Unit.DAY, literature)
    with pytest.raises(ValidationError, match="not a crop variable"):
        models.CropProfile(
            **crop_fields(literature, properties=(soil_value("soil_ph", 6.5, Unit.PH, literature),))
        )


# --- 6. Crop rotation ---------------------------------------------------------


def rotation(rotation_id="test-rotation", role=models.RotationRole.ALTERNATIVE, crops=("crop-a", "crop-b")):
    return models.CropRotation(
        rotation_id=rotation_id,
        name="Test rotation",
        role=role,
        steps=[models.RotationStep(position=index, crop_id=crop) for index, crop in enumerate(crops, 1)],
        cycle_years=len(crops),
    )


def test_rotation_summaries():
    two_crops = rotation(crops=("crop-a", None, "crop-b"))
    assert two_crops.crop_ids == ("crop-a", "crop-b")
    assert two_crops.distinct_crop_count == 2
    assert two_crops.includes_fallow is True
    assert two_crops.is_monoculture is False
    assert rotation(crops=("crop-a",)).is_monoculture is True


def test_rotation_rejects_invalid_sequences():
    with pytest.raises(ValidationError):
        rotation(crops=())
    with pytest.raises(ValidationError, match="at least one crop"):
        rotation(crops=(None, None))
    with pytest.raises(ValidationError, match="positions"):
        models.CropRotation(
            rotation_id="gap",
            name="Gap",
            role=models.RotationRole.ALTERNATIVE,
            steps=[models.RotationStep(position=1, crop_id="a"), models.RotationStep(position=3, crop_id="b")],
            cycle_years=2,
        )
    with pytest.raises(ValidationError):
        models.RotationStep(position=1, crop_id="a", planting_month=13)
    with pytest.raises(ValidationError):
        models.CropRotation(
            rotation_id="zero",
            name="Zero",
            role=models.RotationRole.ALTERNATIVE,
            steps=[models.RotationStep(position=1, crop_id="a")],
            cycle_years=0,
        )


# --- 7. Historical scenario ---------------------------------------------------


def scenario_fields(location, **overrides):
    fields = dict(
        scenario_id="test-dry",
        category=models.ScenarioCategory.DRY,
        label="Fixture dry season",
        location=location,
        period_start=date(2012, 5, 1),
        period_end=date(2012, 9, 30),
        baseline_start=date(2001, 1, 1),
        baseline_end=date(2024, 12, 31),
        classification_variable="precipitation",
        classification_method="Fixture method",
        percentile_rank=5.0,
        source_ids=("test-reanalysis",),
    )
    fields.update(overrides)
    return fields


def test_valid_historical_scenario(location):
    scenario = models.HistoricalScenario(**scenario_fields(location))
    assert scenario.is_forecast is False


def test_scenario_can_never_be_a_forecast(location):
    with pytest.raises(ValidationError):
        models.HistoricalScenario(**scenario_fields(location, is_forecast=True))
    with pytest.raises(ValidationError, match="future"):
        models.HistoricalScenario(
            **scenario_fields(location, period_start=date(2026, 1, 1), period_end=TOMORROW_PLUS)
        )


def test_scenario_rejects_invalid_values(location):
    with pytest.raises(ValidationError, match="period_end"):
        models.HistoricalScenario(**scenario_fields(location, period_end=date(2011, 1, 1)))
    with pytest.raises(ValidationError):
        models.HistoricalScenario(**scenario_fields(location, percentile_rank=120))
    with pytest.raises(ValidationError):
        models.HistoricalScenario(**scenario_fields(location, category="drought-of-the-century"))
    with pytest.raises(ValidationError, match="environmental variable"):
        models.HistoricalScenario(**scenario_fields(location, classification_variable="soil_ph"))
    with pytest.raises(ValidationError):
        models.HistoricalScenario(**scenario_fields(location, source_ids=()))


# --- 8. Farmer priority -------------------------------------------------------


def test_priority_weights_normalise_to_one():
    profile = models.FarmerPriorityProfile(
        priorities=[
            models.FarmerPriority(dimension=models.PriorityDimension.WATER_USE, weight=0.6),
            models.FarmerPriority(dimension=models.PriorityDimension.EROSION_REDUCTION, weight=0.2),
        ],
        constraints=("Fixture constraint",),
    )
    weights = profile.normalised_weights()
    assert weights[models.PriorityDimension.WATER_USE] == pytest.approx(0.75)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_priority_rejects_invalid_values():
    water = models.PriorityDimension.WATER_USE
    with pytest.raises(ValidationError):
        models.FarmerPriority(dimension=water, weight=1.5)
    with pytest.raises(ValidationError):
        models.FarmerPriority(dimension=water, weight=-0.1)
    with pytest.raises(ValidationError):
        models.FarmerPriority(dimension="profit_guarantee", weight=0.5)
    with pytest.raises(ValidationError):
        models.FarmerPriorityProfile(priorities=[])
    with pytest.raises(ValidationError, match="must not repeat"):
        models.FarmerPriorityProfile(
            priorities=[
                models.FarmerPriority(dimension=water, weight=0.5),
                models.FarmerPriority(dimension=water, weight=0.5),
            ]
        )
    with pytest.raises(ValidationError, match="above zero"):
        models.FarmerPriorityProfile(priorities=[models.FarmerPriority(dimension=water, weight=0)])


# --- 11. Uncertainty ----------------------------------------------------------


def test_uncertainty_requires_a_basis_and_a_limitation(uncertainty):
    assert uncertainty.requires_local_review is True
    with pytest.raises(ValidationError):
        models.UncertaintyStatement(confidence=models.ConfidenceLevel.LOW, confidence_basis="Fixture")
    with pytest.raises(ValidationError):
        models.UncertaintyStatement(
            confidence=models.ConfidenceLevel.LOW, confidence_basis="  ", limitations=("Fixture",)
        )


def test_uncertainty_range_rules():
    base = dict(
        confidence=models.ConfidenceLevel.MODERATE,
        confidence_basis="Fixture",
        limitations=("Fixture",),
    )
    with pytest.raises(ValidationError, match="both"):
        models.UncertaintyStatement(**base, lower_bound=1.0)
    with pytest.raises(ValidationError, match="greater than upper_bound"):
        models.UncertaintyStatement(
            **base, lower_bound=5.0, upper_bound=1.0, unit=Unit.MILLIMETRE, interval_method="Fixture"
        )
    with pytest.raises(ValidationError, match="unit and the method"):
        models.UncertaintyStatement(**base, lower_bound=1.0, upper_bound=5.0)
    stated = models.UncertaintyStatement(
        **base, lower_bound=1.0, upper_bound=5.0, unit=Unit.MILLIMETRE, interval_method="Fixture"
    )
    assert stated.upper_bound == 5.0


# --- 9. Scenario result -------------------------------------------------------


def result(uncertainty, rotation_id="rotation-a", scenario_id="test-dry", indicators=()):
    return models.ScenarioResult(
        rotation_id=rotation_id,
        scenario_id=scenario_id,
        indicators=indicators,
        uncertainty=uncertainty,
        engine_version="0.0-test",
        computed_at=FIXED_TIME,
        input_source_ids=("test-reanalysis",),
    )


def test_scenario_result_holds_modeled_indicators(uncertainty, modeled, test_indicator):
    indicator = soil_value(test_indicator.name, 12.0, Unit.MILLIMETRE, modeled)
    outcome = result(uncertainty, indicators=(indicator,))
    assert outcome.get(test_indicator.name).provenance.kind is DataKind.MODELED


def test_indicator_can_never_be_labelled_as_observed(uncertainty, reanalysis, test_indicator):
    disguised = soil_value(test_indicator.name, 12.0, Unit.MILLIMETRE, reanalysis)
    with pytest.raises(ValidationError, match="modeled or derived"):
        result(uncertainty, indicators=(disguised,))


def test_scenario_result_rejects_non_indicators_and_missing_fields(uncertainty, make_observation):
    with pytest.raises(ValidationError, match="not a indicator variable"):
        result(uncertainty, indicators=(make_observation(),))
    with pytest.raises(ValidationError):
        models.ScenarioResult(rotation_id="a", scenario_id="b", engine_version="0", computed_at=FIXED_TIME)
    with pytest.raises(ValidationError, match="future"):
        models.ScenarioResult(
            rotation_id="a",
            scenario_id="b",
            uncertainty=uncertainty,
            engine_version="0",
            computed_at=datetime.now(timezone.utc) + timedelta(days=2),
            input_source_ids=("x",),
        )


# --- 10. Comparison result ----------------------------------------------------


def comparison_fields(location, uncertainty, **overrides):
    fields = dict(
        comparison_id="test-comparison",
        location=location,
        rotation_ids=("rotation-a", "rotation-b", "rotation-c"),
        scenario_ids=("test-dry", "test-typical", "test-wet"),
        current_practice_rotation_id="rotation-a",
        uncertainty=uncertainty,
        generated_at=FIXED_TIME,
    )
    fields.update(overrides)
    return fields


def test_comparison_tracks_completeness_and_challenge_guidance(location, uncertainty):
    comparison = models.ComparisonResult(
        **comparison_fields(location, uncertainty, results=(result(uncertainty),))
    )
    assert comparison.follows_challenge_guidance is True
    assert comparison.is_complete is False
    assert len(comparison.missing_pairs) == 8
    assert "does not" in comparison.disclaimer and "not weather forecasts" in comparison.disclaimer

    two_rotations = models.ComparisonResult(
        **comparison_fields(location, uncertainty, rotation_ids=("rotation-a", "rotation-b"))
    )
    assert two_rotations.follows_challenge_guidance is False


def test_comparison_rejects_inconsistent_content(location, uncertainty, literature):
    with pytest.raises(ValidationError):
        models.ComparisonResult(**comparison_fields(location, uncertainty, rotation_ids=("rotation-a",)))
    with pytest.raises(ValidationError, match="must not repeat"):
        models.ComparisonResult(
            **comparison_fields(location, uncertainty, rotation_ids=("rotation-a", "rotation-a"))
        )
    with pytest.raises(ValidationError, match="current-practice"):
        models.ComparisonResult(
            **comparison_fields(location, uncertainty, current_practice_rotation_id="somewhere-else")
        )
    with pytest.raises(ValidationError, match="only once"):
        models.ComparisonResult(
            **comparison_fields(location, uncertainty, results=(result(uncertainty), result(uncertainty)))
        )
    with pytest.raises(ValidationError, match="must belong"):
        models.ComparisonResult(
            **comparison_fields(location, uncertainty, results=(result(uncertainty, rotation_id="stranger"),))
        )
    stray = models.RotationAssessment(
        rotation_id="stranger", rationale="Fixture", supporting_evidence=(literature,)
    )
    with pytest.raises(ValidationError, match="assessment must belong"):
        models.ComparisonResult(**comparison_fields(location, uncertainty, assessments=(stray,)))


def test_rotation_assessment_requires_rationale_and_evidence(literature):
    assessment = models.RotationAssessment(
        rotation_id="rotation-a",
        rationale="Fixture rationale",
        supporting_evidence=(literature,),
        information_gaps=("Fixture gap",),
        local_review_risks=("Fixture risk",),
    )
    assert assessment.information_gaps == ("Fixture gap",)
    with pytest.raises(ValidationError):
        models.RotationAssessment(rotation_id="rotation-a", rationale="Fixture", supporting_evidence=())
    with pytest.raises(ValidationError):
        models.RotationAssessment(rotation_id="rotation-a", supporting_evidence=(literature,))


def test_contracts_round_trip_through_json(location, uncertainty, make_observation):
    observation = make_observation()
    assert models.EnvironmentalObservation.model_validate_json(observation.model_dump_json()) == observation
    comparison = models.ComparisonResult(**comparison_fields(location, uncertainty))
    assert models.ComparisonResult.model_validate_json(comparison.model_dump_json()) == comparison
