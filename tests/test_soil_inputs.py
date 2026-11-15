"""A4.2: soil inputs for the three soil-dependent mappings.

Valid inputs are accepted with their provenance; invalid ones are rejected;
missing ones stay missing with guidance; hypothetical ones stay labelled; and
soil compatibility is computed only where both the soil input and the crop
evidence support it.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from src.models import DataKind, GeoLocation, SoilDrainageClass, SoilEvidenceCategory, SoilTextureClass
from src.soil_inputs import (
    SoilDrainageInput,
    SoilProfileInput,
    SoilSourceClass,
    SoilTextureInput,
    SoilValueInput,
    SoilVerificationStatus,
    SoilWaterBasis,
    compare_ph,
    demonstration_soil_profile,
    resolve_soil,
    root_zone_water,
)

SITE = GeoLocation(latitude=-1.58, longitude=37.24, name="Test site")
SOIL_MAPPINGS = ("soil-ph-requirement-to-soil-ph", "rooting-depth-to-soil-water", "depletion-fraction-to-soil-water")


def value(number, source=SoilSourceClass.USER_REPORTED, **extra):
    return SoilValueInput(value=number, source_class=source, **extra)


def test_the_three_soil_mappings_are_the_a3_soil_mappings(kb):
    soil = {item.mapping_id for item in kb.variable_mappings if item.target.value == "soil_information"}
    assert soil == set(SOIL_MAPPINGS)


def test_no_soil_means_every_soil_item_is_missing_with_guidance(gate):
    soil = resolve_soil(None, location=SITE, gate=gate)
    assert soil.records == () and soil.water is None and soil.information is None
    for mapping in SOIL_MAPPINGS:
        items = soil.missing_for(mapping)
        assert items and all(item.how_to_obtain and item.explanation for item in items)


def test_valid_ph_is_kept_with_its_provenance(gate):
    soil = resolve_soil(
        SoilProfileInput(soil_ph=value(6.2, SoilSourceClass.LAB_MEASURED, source_identifier="Report 17", collected_on=date(2026, 3, 1))),
        location=SITE, gate=gate,
    )
    record = soil.get("soil_ph")
    assert record.value == 6.2 and record.source_class is SoilSourceClass.LAB_MEASURED
    assert record.source_identifier == "Report 17" and record.collected_on == date(2026, 3, 1)
    assert record.applies_to and record.limitations


def test_a_reported_lab_value_is_not_claimed_as_verified(gate):
    soil = resolve_soil(SoilProfileInput(soil_ph=value(6.2, SoilSourceClass.LAB_MEASURED)), location=SITE, gate=gate)
    record = soil.get("soil_ph")
    assert record.verification is SoilVerificationStatus.NOT_VERIFIED
    assert record.provenance.kind is DataKind.USER_REPORTED
    assert "not independently verified" in record.limitations[0]
    # In the A1 soil contract it is user-entered, never a local measurement.
    assert soil.information.evidence_categories()["soil_ph"] is SoilEvidenceCategory.USER_ENTERED


@pytest.mark.parametrize(
    "fields, message",
    [
        (dict(soil_ph=value(15)), "physical maximum"),
        (dict(soil_ph=value(-1)), "physical minimum"),
        (dict(field_capacity=value(0.2), wilting_point=value(0.3)), "greater than the wilting point"),
        (dict(field_capacity=value(0.3)), "together"),
        (dict(field_capacity=value(1.4), wilting_point=value(0.1)), "physical maximum"),
        (dict(available_water_capacity=value(900)), "physical maximum"),
        (
            dict(field_capacity=value(0.30), wilting_point=value(0.15), available_water_capacity=value(60)),
            "contradicts",
        ),
        (dict(depth_top_cm=30, depth_bottom_cm=10), "depth_bottom_cm"),
        (dict(soil_ph=value(6, SoilSourceClass.PROVISIONAL_ASSUMPTION)), "hypothetical"),
        (dict(soil_ph=value(6), hypothetical=True), "provisional assumption"),
    ],
)
def test_invalid_soil_inputs_are_rejected(fields, message):
    with pytest.raises(ValidationError, match=message):
        SoilProfileInput(**fields)


@pytest.mark.parametrize(
    "fields, message",
    [
        (dict(source_class=SoilSourceClass.UNKNOWN), "unknown source"),
        (dict(source_class=SoilSourceClass.PUBLIC_SOIL_DATASET), "name the dataset"),
        (dict(source_class=SoilSourceClass.USER_REPORTED, collected_on=date(2999, 1, 1)), "future"),
    ],
)
def test_invalid_soil_sources_are_rejected(fields, message):
    with pytest.raises(ValidationError, match=message):
        SoilValueInput(value=6, **fields)


def test_texture_and_category_values_are_validated():
    with pytest.raises(ValidationError):
        SoilTextureInput(texture_class="volcanic", source_class="user_reported")
    with pytest.raises(ValidationError):
        SoilDrainageInput(drainage_class="soggy", source_class="user_reported")


def test_implausible_but_possible_values_are_kept_with_a_warning(gate):
    soil = resolve_soil(SoilProfileInput(soil_ph=value(3.2)), location=SITE, gate=gate)
    assert soil.ph == 3.2 and soil.get("soil_ph").warnings


def test_available_water_capacity_is_used_directly(gate):
    soil = resolve_soil(SoilProfileInput(available_water_capacity=value(150)), location=SITE, gate=gate)
    assert soil.water.basis is SoilWaterBasis.AVAILABLE_WATER_CAPACITY
    assert (soil.water.available_water_min, soil.water.available_water_max) == (0.15, 0.15)


def test_field_capacity_and_wilting_point_give_derived_available_water(gate):
    soil = resolve_soil(SoilProfileInput(field_capacity=value(0.30), wilting_point=value(0.15)), location=SITE, gate=gate)
    assert soil.water.basis is SoilWaterBasis.FIELD_CAPACITY_AND_WILTING_POINT
    assert soil.water.available_water_min == pytest.approx(0.15)
    assert soil.water.verification is SoilVerificationStatus.DERIVED_FROM_INPUTS
    assert soil.water.provenance.kind is DataKind.DERIVED


def test_texture_alone_uses_the_fao_reference_range_labelled_as_typical(gate):
    texture = SoilTextureInput(texture_class=SoilTextureClass.LOAM, source_class=SoilSourceClass.USER_REPORTED)
    soil = resolve_soil(SoilProfileInput(texture=texture), location=SITE, gate=gate)
    assert soil.water.basis is SoilWaterBasis.TEXTURE_CLASS_REFERENCE
    assert (soil.water.available_water_min, soil.water.available_water_max) == (0.13, 0.18)
    assert soil.water.verification is SoilVerificationStatus.LITERATURE_REFERENCE
    assert "not a measurement" in soil.water.limitations[0]
    assert soil.water.gate.admitted


def test_garbled_silty_clay_reference_is_not_used(gate):
    texture = SoilTextureInput(texture_class=SoilTextureClass.SILTY_CLAY, source_class=SoilSourceClass.USER_REPORTED)
    soil = resolve_soil(SoilProfileInput(texture=texture), location=SITE, gate=gate)
    assert soil.water is None
    assert "cannot be used" in soil.missing_for("rooting-depth-to-soil-water")[0].explanation


def test_texture_class_without_a_reference_row_leaves_water_missing(gate):
    texture = SoilTextureInput(texture_class=SoilTextureClass.SANDY_CLAY, source_class=SoilSourceClass.USER_REPORTED)
    soil = resolve_soil(SoilProfileInput(texture=texture), location=SITE, gate=gate)
    assert soil.water is None
    assert "no reference values" in soil.missing_for("depletion-fraction-to-soil-water")[0].explanation


def test_demonstration_profile_is_hypothetical_throughout(gate):
    soil = resolve_soil(demonstration_soil_profile(), location=SITE, gate=gate)
    assert soil.hypothetical
    assert all(item.verification is SoilVerificationStatus.HYPOTHETICAL for item in soil.records)
    assert all(item.provenance.kind is DataKind.ASSUMED for item in soil.records)
    assert soil.water.verification is SoilVerificationStatus.HYPOTHETICAL
    assert "not real data" in soil.label
    assert set(soil.information.evidence_categories().values()) == {SoilEvidenceCategory.DEMONSTRATION_ASSUMPTION}


# --- The three mappings, per crop -------------------------------------------------


def test_ph_is_compared_with_every_admitted_range(kb, gate):
    soil = resolve_soil(SoilProfileInput(soil_ph=value(5.2)), location=SITE, gate=gate)
    results, gaps = compare_ph(kb.get_crop("sorghum"), soil, gate)
    assert [(item.requirement_id, item.position) for item in results] == [("sorghum-soil-ph-optimal", "below")]
    results, _ = compare_ph(kb.get_crop("maize"), soil, gate)
    assert results[0].position == "inside" and results[0].basis == "tolerated"


def test_ph_for_cowpea_is_unavailable_because_no_range_is_documented(kb, gate):
    soil = resolve_soil(SoilProfileInput(soil_ph=value(6.0)), location=SITE, gate=gate)
    results, gaps = compare_ph(kb.get_crop("cowpea"), soil, gate)
    assert results == () and any("No documented soil pH range" in item for item in gaps)


def test_missing_ph_gives_no_comparison(kb, gate):
    results, _ = compare_ph(kb.get_crop("maize"), resolve_soil(None, location=SITE, gate=gate), gate)
    assert results == ()


def test_root_zone_water_follows_fao56_equations_82_and_83(kb, gate):
    # Loam: available water 0.13-0.18 m3/m3 (FAO-56 Table 19).
    # Maize: rooting depth 1.0-1.7 m and p = 0.55 (FAO-56 Table 22).
    # TAW = 1000 x 0.13 x 1.0 = 130 mm to 1000 x 0.18 x 1.7 = 306 mm; RAW = 0.55 x TAW.
    texture = SoilTextureInput(texture_class=SoilTextureClass.LOAM, source_class=SoilSourceClass.USER_REPORTED)
    soil = resolve_soil(SoilProfileInput(texture=texture), location=SITE, gate=gate)
    water, gaps = root_zone_water(kb.get_crop("maize"), soil, gate)
    assert (water.taw_min_mm, water.taw_max_mm) == (130.0, 306.0)
    assert (water.raw_min_mm, water.raw_max_mm) == (71.5, 168.3)
    assert water.depletion_fraction == 0.55 and gaps == ()


def test_pigeon_pea_has_total_but_not_readily_available_water(kb, gate):
    soil = resolve_soil(SoilProfileInput(available_water_capacity=value(150)), location=SITE, gate=gate)
    water, gaps = root_zone_water(kb.get_crop("pigeon-pea"), soil, gate)
    assert (water.taw_min_mm, water.taw_max_mm) == (300.0, 300.0)  # 1000 x 0.15 x 2.0 m
    assert water.raw_min_mm is None and water.depletion_fraction is None
    assert any("depletion fraction" in item for item in gaps)


def test_root_zone_water_is_unavailable_without_soil_water(kb, gate):
    water, gaps = root_zone_water(kb.get_crop("maize"), resolve_soil(None, location=SITE, gate=gate), gate)
    assert water is None and gaps


def test_drainage_is_resolved(gate):
    drainage = SoilDrainageInput(drainage_class=SoilDrainageClass.POORLY_DRAINED, source_class=SoilSourceClass.USER_REPORTED)
    soil = resolve_soil(SoilProfileInput(drainage=drainage), location=SITE, gate=gate)
    assert soil.drainage is SoilDrainageClass.POORLY_DRAINED
    assert not soil.missing_for("waterlogging-sensitive-crop-on-wet-soil")


def test_soil_module_never_reads_weather(gate):
    import inspect

    import src.soil_inputs as module

    source = inspect.getsource(module)
    for forbidden in ("precipitation", "air_temperature", "nasa_client", "data_service"):
        assert forbidden not in source
