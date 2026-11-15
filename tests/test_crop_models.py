"""Crop, soil and evidence models added in phase A3.

Numbers in this file are fixtures chosen to exercise a rule. None is an
agronomic value, and none is presented as one.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src import models
from src.models import (
    CropLifeCycle,
    CropRequirement,
    DataKind,
    EvidenceConfidence,
    Explanation,
    KnowledgeStatus,
    QualitativeAttribute,
    RequirementBasis,
    SoilDrainageClass,
    SoilEvidenceCategory,
    Unit,
    UnknownAttribute,
)


def cited(**overrides) -> models.ProvenanceRecord:
    fields = dict(
        kind=DataKind.LITERATURE_VALUE,
        source_id="test-source",
        source_name="Fixture source",
        citation="Fixture citation (not a real publication)",
        locator="Fixture table 1",
        confidence=EvidenceConfidence.DIRECTLY_SUPPORTED,
        applicability="Fixture crop",
    )
    fields.update(overrides)
    return models.ProvenanceRecord(**fields)


def requirement(**overrides) -> CropRequirement:
    fields = dict(
        requirement_id="test-requirement",
        variable="crop_temperature_requirement",
        minimum=10.0,
        maximum=20.0,
        unit=Unit.DEGREE_CELSIUS,
        basis=RequirementBasis.OPTIMAL,
        statement="Fixture statement.",
        limitation="Fixture limitation.",
        provenance=cited(),
    )
    fields.update(overrides)
    return CropRequirement(**fields)


def profile(**overrides) -> models.CropProfile:
    fields = dict(
        crop_id="test-crop",
        common_name="Test crop",
        botanical_family="Testaceae",
        functional_group=models.CropFunctionalGroup.LEGUME,
        nitrogen_fixing=True,
        sources=(cited(),),
    )
    fields.update(overrides)
    return models.CropProfile(**fields)


# --- Evidence on the provenance record ----------------------------------------------


def test_provenance_carries_locator_confidence_and_applicability():
    record = cited()
    assert record.locator == "Fixture table 1"
    assert record.confidence is EvidenceConfidence.DIRECTLY_SUPPORTED
    assert record.applicability == "Fixture crop"


def test_confidence_is_a_fixed_vocabulary_not_a_probability():
    assert {item.value for item in EvidenceConfidence} == {
        "directly_supported",
        "context_dependent",
        "provisional",
        "insufficient_evidence",
    }
    for invalid in ("certain", "90%", 0.9, "high"):
        with pytest.raises(ValidationError):
            cited(confidence=invalid)


def test_a1_provenance_records_still_work_without_the_new_fields(literature):
    assert literature.locator is None and literature.confidence is None


# --- Crop requirements --------------------------------------------------------------


def test_valid_requirement():
    item = requirement()
    assert (item.minimum, item.maximum) == (10.0, 20.0)
    assert item.is_single_value is False
    assert requirement(minimum=1.2, maximum=1.2, variable="crop_coefficient_mid_season",
                       unit=Unit.DIMENSIONLESS).is_single_value is True


def test_one_sided_requirements_are_allowed():
    assert requirement(maximum=None).maximum is None
    assert requirement(minimum=None).minimum is None


def test_requirement_without_any_number_is_rejected():
    with pytest.raises(ValidationError, match="minimum, a maximum or both"):
        requirement(minimum=None, maximum=None)


def test_contradictory_minimum_and_maximum_are_rejected():
    with pytest.raises(ValidationError, match="minimum must not be greater than maximum"):
        requirement(minimum=30.0, maximum=20.0)


@pytest.mark.parametrize(
    ("variable", "unit", "minimum", "maximum"),
    [
        ("crop_temperature_requirement", Unit.DEGREE_CELSIUS, -40.0, 20.0),
        ("crop_temperature_requirement", Unit.DEGREE_CELSIUS, 10.0, 95.0),
        ("crop_soil_ph_requirement", Unit.PH, 4.0, 15.0),
        ("crop_depletion_fraction", Unit.FRACTION, 0.2, 1.4),
        ("crop_cycle_length", Unit.DAY, 0.0, 100.0),
        ("crop_coefficient_mid_season", Unit.DIMENSIONLESS, -0.1, 1.0),
        ("crop_annual_rainfall_requirement", Unit.MILLIMETRE, -5.0, 100.0),
    ],
)
def test_impossible_numeric_ranges_are_rejected(variable, unit, minimum, maximum):
    with pytest.raises(ValidationError, match="physical"):
        requirement(variable=variable, unit=unit, minimum=minimum, maximum=maximum)


@pytest.mark.parametrize(
    ("variable", "wrong_unit", "expected"),
    [
        ("crop_temperature_requirement", Unit.PERCENT, "degC"),
        ("crop_seasonal_water_requirement", Unit.MILLIMETRE_PER_DAY, "mm"),
        ("crop_annual_rainfall_requirement", Unit.MILLIMETRE_PER_DAY, "mm"),
        ("crop_max_rooting_depth", Unit.CENTIMETRE, "m"),
        ("crop_cycle_length", Unit.COUNT, "day"),
        ("crop_soil_ph_requirement", Unit.DIMENSIONLESS, "pH"),
    ],
)
def test_incorrect_units_are_rejected(variable, wrong_unit, expected):
    with pytest.raises(ValidationError, match=f"must use unit '{expected}'"):
        requirement(variable=variable, unit=wrong_unit, minimum=1.0, maximum=2.0)


def test_requirement_must_use_a_crop_variable():
    with pytest.raises(ValidationError, match="not a crop variable"):
        requirement(variable="air_temperature_mean")
    with pytest.raises(ValidationError, match="unknown variable"):
        requirement(variable="crop_yield_potential")


def test_requirement_kinds_are_distinct_and_validated():
    assert {item.value for item in RequirementBasis} == {
        "optimal", "suitable", "tolerated", "stage_specific", "typical"
    }
    with pytest.raises(ValidationError):
        requirement(basis="ideal")
    with pytest.raises(ValidationError, match="must name the growth stage"):
        requirement(basis=RequirementBasis.STAGE_SPECIFIC)
    staged = requirement(basis=RequirementBasis.STAGE_SPECIFIC, growth_stage="seedling")
    assert staged.growth_stage == "seedling"


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        ({"citation": None}, "needs a cited source"),
        ({"locator": None}, "where in the source"),
        ({"confidence": None}, "needs a confidence classification"),
    ],
)
def test_unsupported_requirements_are_rejected(missing, message):
    with pytest.raises(ValidationError, match=message):
        requirement(provenance=cited(kind=DataKind.USER_REPORTED, **missing))


def test_requirement_needs_a_statement_and_a_limitation():
    for field in ("statement", "limitation", "requirement_id", "provenance"):
        fields = requirement().model_dump()
        del fields[field]
        with pytest.raises(ValidationError):
            CropRequirement(**fields)
    with pytest.raises(ValidationError):
        requirement(limitation="   ")


# --- Qualitative attributes, unknowns and explanations --------------------------------


def test_qualitative_attribute_needs_cited_evidence():
    item = QualitativeAttribute(attribute="waterlogging", statement="Fixture.", provenance=cited())
    assert item.attribute == "waterlogging"
    with pytest.raises(ValidationError, match="confidence"):
        QualitativeAttribute(attribute="waterlogging", statement="Fixture.", provenance=cited(confidence=None))
    with pytest.raises(ValidationError):
        QualitativeAttribute(attribute="Not A Slug", statement="Fixture.", provenance=cited())


def test_unknown_attribute_needs_a_reason():
    assert UnknownAttribute(attribute="soil_ph", reason="Not found in the sources read.").reason
    with pytest.raises(ValidationError):
        UnknownAttribute(attribute="soil_ph", reason="  ")
    with pytest.raises(ValidationError):
        UnknownAttribute(attribute="soil_ph")


def test_explanation_has_five_parts_and_names_its_region():
    base = dict(
        what_is_known="Known.", why_it_matters="Matters.", evidence_summary="Evidence.",
        what_is_uncertain="Uncertain.",
    )
    general = Explanation(**base, region_specific=False)
    assert general.region_note is None
    with pytest.raises(ValidationError, match="must name the region"):
        Explanation(**base, region_specific=True)
    assert Explanation(**base, region_specific=True, region_note="Fixture region").region_note
    for part in base:
        with pytest.raises(ValidationError):
            Explanation(**{**base, part: " "}, region_specific=False)


# --- Crop profile extension -----------------------------------------------------------


def test_earlier_crop_profiles_remain_valid():
    crop = profile()
    assert crop.requirements == () and crop.attributes == () and crop.unknowns == ()
    assert crop.life_cycle is None
    assert crop.data_quality is KnowledgeStatus.INCOMPLETE  # nothing is assumed reviewed


def test_profile_holds_requirements_attributes_and_unknowns():
    crop = profile(
        life_cycle=CropLifeCycle.ANNUAL,
        life_cycle_basis="Stated by the fixture source.",
        requirements=(
            requirement(requirement_id="optimal", basis=RequirementBasis.OPTIMAL),
            requirement(requirement_id="tolerated", basis=RequirementBasis.TOLERATED, minimum=5.0, maximum=35.0),
        ),
        attributes=(QualitativeAttribute(attribute="drainage", statement="Fixture.", provenance=cited()),),
        unknowns=(UnknownAttribute(attribute="base_temperature", reason="Not found."),),
        data_quality=KnowledgeStatus.PROVISIONAL,
    )
    assert len(crop.requirements_for("crop_temperature_requirement")) == 2
    optimal = crop.requirements_for("crop_temperature_requirement", RequirementBasis.OPTIMAL)
    assert [item.requirement_id for item in optimal] == ["optimal"]
    assert crop.requirements_for("crop_soil_ph_requirement") == ()
    assert crop.is_unknown("base_temperature") and not crop.is_unknown("drainage")


def test_profile_rejects_duplicate_and_unexplained_entries():
    with pytest.raises(ValidationError, match="requirement identifiers must not repeat"):
        profile(requirements=(requirement(), requirement()))
    duplicate = UnknownAttribute(attribute="soil_ph", reason="Not found.")
    with pytest.raises(ValidationError, match="unknown attributes must not repeat"):
        profile(unknowns=(duplicate, duplicate))
    with pytest.raises(ValidationError, match="needs its basis"):
        profile(life_cycle=CropLifeCycle.ANNUAL)
    with pytest.raises(ValidationError):
        profile(life_cycle="biennial", life_cycle_basis="Fixture.")
    with pytest.raises(ValidationError):
        profile(data_quality="excellent")


@pytest.mark.parametrize("field", ["crop_id", "common_name", "botanical_family", "functional_group", "nitrogen_fixing", "sources"])
def test_profile_mandatory_identifiers(field):
    fields = profile().model_dump()
    del fields[field]
    with pytest.raises(ValidationError):
        models.CropProfile(**fields)


def test_profile_round_trips_through_json():
    crop = profile(requirements=(requirement(),), unknowns=(UnknownAttribute(attribute="x", reason="y"),))
    assert models.CropProfile.model_validate_json(crop.model_dump_json()) == crop


# --- Soil: four kinds of information, never merged -------------------------------------


def soil_value(variable, value, unit, kind, **extra):
    fields = dict(kind=kind, source_id="soil-fixture", source_name="Fixture")
    if kind in (DataKind.GROUND_MEASUREMENT, DataKind.GRIDDED_MAP_PRODUCT):
        from tests.conftest import FIXED_TIME

        fields.update(retrieved_at=FIXED_TIME, citation="Fixture citation")
    if kind is DataKind.LITERATURE_VALUE:
        fields.update(citation="Fixture citation")
    if kind is DataKind.ASSUMED:
        fields.update(assumption="Fixture demonstration assumption")
    if kind in (DataKind.DERIVED, DataKind.MODELED):
        fields.update(transformations=("fixture calculation",))
    fields.update(extra)
    return models.ScientificValue(
        variable=variable, value=value, unit=unit, provenance=models.ProvenanceRecord(**fields)
    )


def test_soil_information_keeps_the_four_categories_apart(location, user_reported):
    soil = models.SoilInformation(
        location=location,
        depth_top_cm=0,
        depth_bottom_cm=30,
        texture_class=models.SoilTextureClass.LOAM,
        texture_provenance=user_reported,
        drainage_class=SoilDrainageClass.WELL_DRAINED,
        drainage_provenance=user_reported,
        properties=(
            soil_value("soil_ph", 6.2, Unit.PH, DataKind.GROUND_MEASUREMENT),
            soil_value("soil_organic_carbon", 12.0, Unit.GRAM_PER_KILOGRAM, DataKind.GRIDDED_MAP_PRODUCT),
            soil_value("soil_clay_content", 20.0, Unit.PERCENT, DataKind.USER_REPORTED),
            soil_value("soil_bulk_density", 1.3, Unit.GRAM_PER_CUBIC_CENTIMETRE, DataKind.ASSUMED),
            soil_value("soil_field_capacity", 0.25, Unit.CUBIC_METRE_PER_CUBIC_METRE, DataKind.LITERATURE_VALUE),
        ),
    )
    assert soil.evidence_categories() == {
        "soil_ph": SoilEvidenceCategory.MEASURED_LOCALLY,
        "soil_organic_carbon": SoilEvidenceCategory.MAPPED_ESTIMATE,
        "soil_clay_content": SoilEvidenceCategory.USER_ENTERED,
        "soil_bulk_density": SoilEvidenceCategory.DEMONSTRATION_ASSUMPTION,
        "soil_field_capacity": SoilEvidenceCategory.REFERENCE_VALUE,
        "texture_class": SoilEvidenceCategory.USER_ENTERED,
        "drainage_class": SoilEvidenceCategory.USER_ENTERED,
    }
    assert "soil_ph" not in soil.unmeasured()
    assert set(soil.unmeasured()) == set(soil.evidence_categories()) - {"soil_ph"}


@pytest.mark.parametrize("kind", [DataKind.REANALYSIS, DataKind.SATELLITE_RETRIEVAL, DataKind.MODELED])
def test_soil_is_never_inferred_from_weather_or_model_output(kind, location, reanalysis, modeled):
    from tests.conftest import FIXED_TIME

    record = models.ProvenanceRecord(
        kind=kind,
        source_id="nasa-power",
        source_name="Fixture",
        citation="Fixture citation",
        retrieved_at=FIXED_TIME,
        transformations=("fixture calculation",),
    )
    inferred = models.ScientificValue(variable="soil_organic_carbon", value=10.0, unit=Unit.GRAM_PER_KILOGRAM, provenance=record)
    with pytest.raises(ValidationError, match="never inferred from weather or model output"):
        models.SoilInformation(location=location, depth_top_cm=0, depth_bottom_cm=30, properties=(inferred,))
    with pytest.raises(ValidationError, match="never inferred from weather or model output"):
        models.SoilInformation(
            location=location, depth_top_cm=0, depth_bottom_cm=30,
            drainage_class=SoilDrainageClass.POORLY_DRAINED, drainage_provenance=record,
        )


def test_drainage_class_needs_provenance_and_a_known_value(location, user_reported):
    with pytest.raises(ValidationError, match="drainage class needs provenance"):
        models.SoilInformation(location=location, depth_top_cm=0, depth_bottom_cm=30,
                               drainage_class=SoilDrainageClass.WELL_DRAINED)
    with pytest.raises(ValidationError):
        models.SoilInformation(location=location, depth_top_cm=0, depth_bottom_cm=30,
                               drainage_class="swampy", drainage_provenance=user_reported)


def test_unmeasured_soil_stays_unknown(location):
    empty = models.SoilInformation(location=location, depth_top_cm=0, depth_bottom_cm=30)
    assert empty.evidence_categories() == {} and empty.get("soil_ph") is None
    assert empty.texture_class is None and empty.drainage_class is None


@pytest.mark.parametrize(
    ("variable", "unit", "value"),
    [("soil_ph", Unit.PH, -1.0), ("soil_ph", Unit.PH, 14.5), ("soil_clay_content", Unit.PERCENT, 120.0),
     ("soil_field_capacity", Unit.CUBIC_METRE_PER_CUBIC_METRE, 1.5)],
)
def test_invalid_soil_values_are_rejected(variable, unit, value):
    with pytest.raises(ValidationError, match="physical"):
        soil_value(variable, value, unit, DataKind.USER_REPORTED)


# --- Registry and priorities ----------------------------------------------------------


def test_crop_variables_are_final_and_carry_units():
    crop_variables = {item.name: item for item in models.registered_variables(models.VariableDomain.CROP)}
    assert not any(item.provisional for item in crop_variables.values())
    assert crop_variables["crop_seasonal_water_requirement"].unit is Unit.MILLIMETRE
    assert "not rainfall" in crop_variables["crop_seasonal_water_requirement"].description
    assert crop_variables["crop_temperature_requirement"].unit is Unit.DEGREE_CELSIUS
    assert crop_variables["crop_soil_ph_requirement"].unit is Unit.PH
    assert crop_variables["crop_depletion_fraction"].unit is Unit.FRACTION
    assert "crop_base_temperature" not in crop_variables  # no source supplied one


def test_priority_dimensions_cover_official_and_project_categories():
    names = {item.value for item in models.PriorityDimension}
    official = {"water_use", "nitrogen_fixation", "erosion_reduction", "organic_matter", "forage_value", "market_suitability"}
    assert official <= names
    assert {"crop_diversity", "operational_simplicity", "climate_resilience", "pest_cycle_disruption"} <= names
