"""Rotation relationships, constraints and farmer-priority definitions.

Phase A3 stores and validates these records. Nothing here executes a
constraint, ranks a rotation or weighs a priority; that is phase A4.
"""

from __future__ import annotations

import pytest

from src import crop_knowledge
from src.crop_knowledge import (
    ConstraintSeverity,
    CroppingArrangement,
    EvidenceAvailability,
    KnowledgeBaseError,
    PriorityDefinition,
    PriorityOrigin,
    RelationshipStrength,
    RelationshipType,
    RotationConstraint,
    RotationRelationship,
    build_knowledge_base,
)
from src.models import EvidenceConfidence, PriorityDimension, get_variable
from tests.conftest import find


def relationship_raw(raw, relationship_id):
    return find(raw["relationships"], "relationship_id", relationship_id)


def constraint_raw(raw, constraint_id):
    return find(raw["constraints"], "constraint_id", constraint_id)


# --- Relationships -------------------------------------------------------------------


def test_every_relationship_has_rationale_evidence_scope_and_limits(kb):
    assert len(kb.relationships) == 15
    for item in kb.relationships:
        assert item.statement and item.scope and item.limitations
        assert item.applies_to_crops or item.applies_to_families or item.applies_generally
        assert item.evidence
        for record in item.evidence:
            assert record.citation and record.locator and record.confidence
        explanation = item.explanation
        assert explanation.what_is_known and explanation.why_it_matters
        assert explanation.evidence_summary and explanation.what_is_uncertain


def test_relationship_types_cover_the_brief(kb):
    present = {item.relationship_type for item in kb.relationships}
    assert present == {
        RelationshipType.SAME_CROP_REPETITION,
        RelationshipType.SAME_FAMILY_REPETITION,
        RelationshipType.LEGUME_INCLUSION,
        RelationshipType.NITROGEN_BENEFIT,
        RelationshipType.PEST_DISEASE_CARRYOVER,
        RelationshipType.WEED_PRESSURE,
        RelationshipType.SOIL_ORGANIC_MATTER,
        RelationshipType.SOIL_COVER,
        RelationshipType.ROOTING_DIVERSITY,
        RelationshipType.ROTATION_DIVERSITY,
        RelationshipType.WATER_USE_CONTRAST,
    }


def test_tendencies_are_not_presented_as_universal_rules(kb):
    for item in kb.relationships:
        lowered = item.statement.lower()
        assert " always " not in f" {lowered} " and " never " not in f" {lowered} "
    strengths = {item.relationship_id: item.strength for item in kb.relationships}
    assert strengths["cereal-after-grain-legume"] is RelationshipStrength.DOCUMENTED_TENDENCY
    assert strengths["machakos-maize-after-cowpea"] is RelationshipStrength.SITE_SPECIFIC_FINDING
    assert strengths["rotation-breaks-crop-specific-pests"] is RelationshipStrength.GENERAL_PRINCIPLE
    assert strengths["same-family-repetition"] is RelationshipStrength.UNSUPPORTED
    assert strengths["legume-effects-on-cereal-pests"] is RelationshipStrength.UNSUPPORTED


def test_legume_benefit_is_qualified_not_assumed(kb):
    by_id = {item.relationship_id: item for item in kb.relationships}
    review = by_id["cereal-after-grain-legume"]
    assert "variability is large" in review.statement and len(review.known_exceptions) == 3
    assert "0.49 t/ha" in review.statement and "41 %" in review.statement

    grain = by_id["fixed-nitrogen-leaves-with-the-grain"]
    assert "does not necessarily leave it in the field" in grain.statement and "88 %" in grain.statement
    assert set(grain.applies_to_crops) == {"common-bean", "pigeon-pea"}

    beyond = by_id["legume-benefit-is-not-only-nitrogen"]
    assert "59 %" in beyond.statement

    organic = by_id["legumes-and-soil-organic-matter"]
    assert "studies generally report no such impacts" in organic.statement


def test_machakos_findings_are_site_specific_and_dated(kb):
    by_id = {item.relationship_id: item for item in kb.relationships}
    cowpea = by_id["machakos-maize-after-cowpea"]
    assert "17 %" in cowpea.statement and set(cowpea.applies_to_crops) == {"cowpea", "maize"}
    pigeon_pea = by_id["machakos-maize-with-pigeon-pea"]
    assert "24 %" in pigeon_pea.statement and "only marginally better" in pigeon_pea.statement
    assert any("Intercropping is not rotation" in item for item in pigeon_pea.limitations)
    for item in (cowpea, pigeon_pea, by_id["machakos-legume-pests"]):
        assert item.strength is RelationshipStrength.SITE_SPECIFIC_FINDING
        assert "1989" in item.scope and item.explanation.region_specific
        assert [record.source_id for record in item.evidence] == ["rao-mathuva-2000"]


def test_unsupported_relationships_say_what_is_missing(kb):
    family = next(item for item in kb.relationships if item.relationship_id == "same-family-repetition")
    assert all(record.confidence is EvidenceConfidence.INSUFFICIENT_EVIDENCE for record in family.evidence)
    assert "no source read" in family.statement
    assert family.explanation.what_is_known.startswith("Nothing")
    assert any("not a finding that the effect does not exist" in item for item in family.limitations)


def test_relationships_for_a_crop_include_family_and_general_records(kb):
    maize = {item.relationship_id for item in kb.relationships_for("maize")}
    assert {"machakos-maize-after-cowpea", "cereal-after-grain-legume", "rotation-breaks-crop-specific-pests",
            "sorghum-and-maize-under-drought", "same-family-repetition"} <= maize
    assert "machakos-legume-pests" not in maize and "fixed-nitrogen-leaves-with-the-grain" not in maize
    cowpea = {item.relationship_id for item in kb.relationships_for("cowpea")}
    assert "machakos-legume-pests" in cowpea and "sorghum-and-maize-under-drought" not in cowpea
    with pytest.raises(KnowledgeBaseError):
        kb.relationships_for("quinoa")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: r.update(strength="unsupported"), "unsupported relationship must mark its evidence as insufficient"),
        (lambda r: r["evidence"][0].update(confidence="insufficient_evidence"), "must be labelled unsupported"),
        (lambda r: r.update(applies_to_families=[], applies_to_crops=[]), "must say which crops or families"),
        (lambda r: r.update(applies_to_families=["Solanaceae"]), "unknown family 'Solanaceae'"),
        (lambda r: r.update(applies_to_crops=["quinoa"]), "unknown crop 'quinoa'"),
        (lambda r: r.update(evidence=[]), "every claim must cite a source"),
        (lambda r: r["evidence"][0].pop("confidence"), "confidence classification"),
        (lambda r: r.update(limitations=[]), "limitations"),
        (lambda r: r.pop("explanation"), "explanation"),
        (lambda r: r.pop("scope"), "scope"),
        (lambda r: r.update(relationship_type="companion_planting"), "relationship_type"),
        (lambda r: r.update(strength="proven"), "strength"),
    ],
)
def test_invalid_relationships_are_rejected(change, message, raw):
    change(relationship_raw(raw, "cereal-after-grain-legume"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_duplicate_relationship_identifiers_are_rejected(raw):
    raw["relationships"].append(dict(relationship_raw(raw, "soil-cover-between-crops")))
    with pytest.raises(KnowledgeBaseError, match="relationship identifiers must not repeat"):
        build_knowledge_base(raw)


def test_relationship_serialises_and_restores(kb):
    for item in kb.relationships:
        assert RotationRelationship.model_validate_json(item.model_dump_json()) == item


# --- Constraints ---------------------------------------------------------------------


def test_every_constraint_has_the_required_parts(kb):
    assert len(kb.constraints) == 14
    for item in kb.constraints:
        assert item.constraint_id and item.description and item.condition
        assert item.applicability and item.limitations and item.user_explanation
        assert item.applies_to_crops or item.applies_to_families or item.applies_generally
        assert item.evidence and all(record.confidence for record in item.evidence)
        assert item.evaluated_in_a3 is False
        for name in item.inputs:
            get_variable(name)


def test_severity_classification(kb):
    by_severity: dict[ConstraintSeverity, set[str]] = {level: set() for level in ConstraintSeverity}
    for item in kb.constraints:
        by_severity[item.severity].add(item.constraint_id)
    assert by_severity[ConstraintSeverity.HARD] == {"frost-kills-maize"}
    assert by_severity[ConstraintSeverity.UNSUPPORTED] == {"same-family-in-succession"}
    assert by_severity[ConstraintSeverity.ADVISORY] == {
        "continuous-cereal-without-legume", "frost-sensitive-crops", "growing-period-longer-than-season",
        "legume-needs-pest-management", "same-crop-in-succession", "waterlogging-sensitive-crop-on-wet-soil",
    }
    assert by_severity[ConstraintSeverity.CONTEXT_DEPENDENT] == {
        "cold-stops-common-bean-growth", "drought-at-flowering-maize", "perennial-in-seasonal-rotation",
        "seasonal-water-need-above-rainfall", "soil-ph-outside-documented-range",
        "temperature-outside-documented-range",
    }


def test_the_only_hard_constraint_is_justified_and_declares_its_assumption(kb):
    frost = next(item for item in kb.constraints if item.severity is ConstraintSeverity.HARD)
    assert frost.applies_to_crops == ("maize",)
    assert all(record.confidence is EvidenceConfidence.DIRECTLY_SUPPORTED for record in frost.evidence)
    assert "Frost kills the plants." in frost.evidence[0].locator
    # A3 declared the 0 °C frost threshold as an assumption; the A4 evidence
    # audit replaced it with the published ETCCDI definition. The guarantee is
    # unchanged: the constraint states how frost is defined and that the
    # agronomic source itself gives no temperature.
    assert any("without giving a temperature" in item and "ETCCDI" in item for item in frost.limitations)
    assert frost.inputs == ("air_temperature_min",)


def test_water_and_temperature_constraints_carry_the_required_cautions(kb):
    by_id = {item.constraint_id: item for item in kb.constraints}
    water = by_id["seasonal-water-need-above-rainfall"]
    assert any("evapotranspiration, not rainfall demand" in item for item in water.limitations)
    assert any("irrigation" in item for item in water.limitations)
    temperature = by_id["temperature-outside-documented-range"]
    assert any("short spells of heat or cold" in item for item in temperature.limitations)
    assert any("No heat-stress threshold" in item for item in temperature.limitations)
    ph = by_id["soil-ph-outside-documented-range"]
    assert "cowpea" not in ph.applies_to_crops  # no pH range is held for cowpea
    assert any("never inferred from NASA data" in item for item in ph.limitations)
    waterlogging = by_id["waterlogging-sensitive-crop-on-wet-soil"]
    assert "sorghum" not in waterlogging.applies_to_crops  # described as somewhat tolerant


def test_constraints_reference_only_crops_with_the_needed_evidence(kb):
    by_id = {item.constraint_id: item for item in kb.constraints}
    for crop_id in by_id["growing-period-longer-than-season"].applies_to_crops:
        assert kb.get_crop(crop_id).requirements_for("crop_cycle_length")
    for crop_id in by_id["seasonal-water-need-above-rainfall"].applies_to_crops:
        assert kb.get_crop(crop_id).requirements_for("crop_seasonal_water_requirement")
    for crop_id in by_id["soil-ph-outside-documented-range"].applies_to_crops:
        assert kb.get_crop(crop_id).requirements_for("crop_soil_ph_requirement")
    for crop_id in by_id["temperature-outside-documented-range"].applies_to_crops:
        assert kb.get_crop(crop_id).requirements_for("crop_temperature_requirement")


def test_constraints_for_a_crop(kb):
    maize = {item.constraint_id for item in kb.constraints_for("maize")}
    assert {"frost-kills-maize", "same-crop-in-succession", "continuous-cereal-without-legume",
            "drought-at-flowering-maize", "same-family-in-succession"} <= maize
    assert "legume-needs-pest-management" not in maize and "perennial-in-seasonal-rotation" not in maize
    pigeon_pea = {item.constraint_id for item in kb.constraints_for("pigeon-pea")}
    assert {"perennial-in-seasonal-rotation", "legume-needs-pest-management", "frost-sensitive-crops"} <= pigeon_pea
    assert "continuous-cereal-without-legume" not in pigeon_pea
    sorghum = {item.constraint_id for item in kb.constraints_for("sorghum")}
    assert "waterlogging-sensitive-crop-on-wet-soil" not in sorghum and "continuous-cereal-without-legume" in sorghum


def test_constraints_build_on_recorded_relationships(kb):
    relationships = {item.relationship_id for item in kb.relationships}
    for item in kb.constraints:
        assert set(item.based_on_relationships) <= relationships
    unsupported = next(item for item in kb.constraints if item.constraint_id == "same-family-in-succession")
    assert unsupported.based_on_relationships == ("same-family-repetition",)
    assert "does not apply it" in unsupported.user_explanation


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda c: c["evidence"][0].update(confidence="context_dependent"), "hard constraint needs evidence that directly supports it"),
        (lambda c: c["evidence"][0].update(confidence="insufficient_evidence"), "hard constraint needs evidence"),
        (lambda c: c.update(severity="unsupported"), "unsupported constraint must mark its evidence as insufficient"),
        (lambda c: c.update(applies_to_crops=["quinoa"]), "unknown crop 'quinoa'"),
        (lambda c: c.update(applies_to_crops=[]), "must say which crops or families"),
        (lambda c: c.update(inputs=["soil_moisture_index"]), "unknown variable 'soil_moisture_index'"),
        (lambda c: c.update(inputs=["air_temperature_min", "air_temperature_min"]), "inputs must not repeat"),
        (lambda c: c.update(based_on_relationships=["a-relationship-that-does-not-exist"]), "unknown relationship"),
        (lambda c: c.update(evidence=[]), "every claim must cite a source"),
        (lambda c: c.update(limitations=[]), "limitations"),
        (lambda c: c.pop("user_explanation"), "user_explanation"),
        (lambda c: c.pop("condition"), "condition"),
        (lambda c: c.update(severity="mandatory"), "severity"),
        (lambda c: c.update(evaluated_in_a3=True), "evaluated_in_a3"),
    ],
)
def test_invalid_constraints_are_rejected(change, message, raw):
    change(constraint_raw(raw, "frost-kills-maize"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_an_advisory_constraint_cannot_rest_only_on_insufficient_evidence(raw):
    constraint = constraint_raw(raw, "same-crop-in-succession")
    constraint["evidence"][0]["confidence"] = "insufficient_evidence"
    with pytest.raises(KnowledgeBaseError, match="must be labelled unsupported"):
        build_knowledge_base(raw)


def test_duplicate_constraint_identifiers_are_rejected(raw):
    raw["constraints"].append(dict(constraint_raw(raw, "frost-kills-maize")))
    with pytest.raises(KnowledgeBaseError, match="constraint identifiers must not repeat"):
        build_knowledge_base(raw)


def test_constraint_serialisation_is_stable_and_reversible(kb):
    for item in kb.constraints:
        text = item.model_dump_json()
        restored = RotationConstraint.model_validate_json(text)
        assert restored == item and restored.model_dump_json() == text
    payload = kb.constraints[0].model_dump(mode="json")
    assert payload["severity"] in {level.value for level in ConstraintSeverity}
    assert payload["evaluated_in_a3"] is False
    assert isinstance(payload["evidence"], list) and payload["evidence"][0]["source_id"]


def test_constraints_are_stored_not_executed(kb):
    callables = [name for name in dir(RotationConstraint) if not name.startswith("_") and name not in dir(crop_knowledge.Contract)]
    assert not [name for name in callables if callable(getattr(RotationConstraint, name))]
    forbidden = ("evaluate", "apply", "check_rotation", "violat", "rank")
    public = [name for name in vars(crop_knowledge) if not name.startswith("_")]
    assert not [name for name in public if any(word in name.lower() for word in forbidden)]


# --- Cropping systems a cited study actually compared ---------------------------------


def test_documented_cropping_systems_come_from_the_machakos_trial(kb):
    systems = {item.system_id: item for item in kb.cropping_systems}
    assert list(systems) == [
        "machakos-continuous-maize",
        "machakos-maize-cowpea-rotation",
        "machakos-maize-pigeon-pea-intercrop",
        "machakos-maize-pigeon-pea-rotation",
    ]
    for item in systems.values():
        assert [record.source_id for record in item.evidence] == ["rao-mathuva-2000"]
        assert item.not_reported and item.limitations  # what the source leaves out is recorded
        assert any("rainy season" in gap for gap in item.not_reported)
        assert any("not as a recommendation" in limit for limit in item.limitations)
    baseline = systems["machakos-continuous-maize"]
    assert baseline.arrangement is CroppingArrangement.CONTINUOUS and baseline.crops == ("maize",)
    assert "17 %" in systems["machakos-maize-cowpea-rotation"].reported_outcome
    assert "only marginally better" in systems["machakos-maize-pigeon-pea-rotation"].reported_outcome


def test_at_least_one_documented_rotation_includes_a_legume(kb):
    with_legume = kb.documented_rotations(with_legume=True)
    assert [item.system_id for item in with_legume] == [
        "machakos-maize-cowpea-rotation", "machakos-maize-pigeon-pea-rotation"
    ]
    assert kb.documented_rotations() == with_legume  # continuous maize is not a rotation
    intercrop = next(item for item in kb.cropping_systems if item.arrangement is CroppingArrangement.INTERCROP)
    assert intercrop not in kb.documented_rotations()
    assert any("not a rotation" in limit for limit in intercrop.limitations)


def test_a_baseline_and_two_alternatives_exist_for_the_three_way_comparison(kb):
    # The challenge suggests comparing at least three strategies including the existing one.
    continuous = [item for item in kb.cropping_systems if item.arrangement is CroppingArrangement.CONTINUOUS]
    assert len(continuous) == 1 and len(kb.documented_rotations()) == 2
    # Nothing here says which one a farmer should choose, or which is theirs today.
    assert any("for the farmer to say" in limit for limit in continuous[0].limitations)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s.update(crops=["maize", "quinoa"], applies_to_crops=["maize", "quinoa"]), "unknown crop 'quinoa'"),
        (lambda s: s.update(arrangement="continuous"), "continuous system has exactly one crop"),
        (lambda s: s.update(crops=["maize"], applies_to_crops=["maize"]), "needs at least two crops"),
        (lambda s: s.update(crops=["maize", "maize"], applies_to_crops=["maize"]), "must not repeat"),
        (lambda s: s.update(evidence=[]), "every claim must cite a source"),
        (lambda s: s.update(not_reported=[]), "not_reported"),
        (lambda s: s.update(limitations=[]), "limitations"),
        (lambda s: s.update(arrangement="relay"), "arrangement"),
        (lambda s: s.update(expected_yield_gain=0.17), "expected_yield_gain"),
    ],
)
def test_invalid_cropping_systems_are_rejected(change, message, raw):
    change(find(raw["cropping_systems"], "system_id", "machakos-maize-cowpea-rotation"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_duplicate_cropping_system_identifiers_are_rejected(raw):
    raw["cropping_systems"].append(dict(find(raw["cropping_systems"], "system_id", "machakos-continuous-maize")))
    with pytest.raises(KnowledgeBaseError, match="cropping system identifiers must not repeat"):
        build_knowledge_base(raw)


# --- Farmer priorities ---------------------------------------------------------------


def test_every_priority_dimension_is_defined_once(kb):
    assert [item.dimension for item in kb.priorities] == list(PriorityDimension)
    for item in kb.priorities:
        assert item.label and item.description and item.evidence_requirement and item.limitations
        assert kb.priority(item.dimension) is item


def test_priorities_carry_no_weights_or_economic_estimates(kb):
    fields = set(PriorityDefinition.model_fields)
    assert not fields & {"weight", "default_weight", "importance", "score", "price", "return"}
    market = kb.priority(PriorityDimension.MARKET_SUITABILITY)
    assert market.evidence_available is EvidenceAvailability.NOT_AVAILABLE
    assert any("none are estimated" in item for item in market.limitations)
    assert any("not used as a present-day economic estimate" in item for item in market.limitations)


def test_priority_origins_distinguish_official_text_from_our_additions(kb):
    official = {item.dimension for item in kb.priorities if item.origin is PriorityOrigin.OFFICIAL_CHALLENGE_TEXT}
    assert official == {
        PriorityDimension.WATER_USE, PriorityDimension.NITROGEN_FIXATION, PriorityDimension.EROSION_REDUCTION,
        PriorityDimension.ORGANIC_MATTER, PriorityDimension.FORAGE_VALUE, PriorityDimension.MARKET_SUITABILITY,
        PriorityDimension.PEST_CYCLE_DISRUPTION,
    }
    ours = {item.dimension for item in kb.priorities if item.origin is PriorityOrigin.PROJECT_ADDITION}
    assert ours == {PriorityDimension.CLIMATE_RESILIENCE, PriorityDimension.CROP_DIVERSITY, PriorityDimension.OPERATIONAL_SIMPLICITY}


def test_evidence_availability_is_stated_honestly(kb):
    availability = {item.dimension.value: item.evidence_available for item in kb.priorities}
    assert availability == {
        "water_use": EvidenceAvailability.PARTIAL,
        "nitrogen_fixation": EvidenceAvailability.PARTIAL,
        "erosion_reduction": EvidenceAvailability.NOT_AVAILABLE,
        "organic_matter": EvidenceAvailability.PARTIAL,
        "forage_value": EvidenceAvailability.NOT_AVAILABLE,
        "market_suitability": EvidenceAvailability.NOT_AVAILABLE,
        "pest_cycle_disruption": EvidenceAvailability.PARTIAL,
        "climate_resilience": EvidenceAvailability.PARTIAL,
        "crop_diversity": EvidenceAvailability.AVAILABLE,
        "operational_simplicity": EvidenceAvailability.NOT_AVAILABLE,
    }
    for dimension in (PriorityDimension.FORAGE_VALUE, PriorityDimension.MARKET_SUITABILITY, PriorityDimension.OPERATIONAL_SIMPLICITY):
        assert any("needing local information, not scored" in item for item in kb.priority(dimension).limitations)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda p: p.update(weight=0.5), "weight"),
        (lambda p: p.update(related_relationships=["a-relationship-that-does-not-exist"]), "unknown relationship"),
        (lambda p: p.update(related_variables=["crop_profit"]), "unknown variable 'crop_profit'"),
        (lambda p: p.pop("evidence_requirement"), "evidence_requirement"),
        (lambda p: p.update(limitations=[]), "limitations"),
        (lambda p: p.update(evidence_available="plenty"), "evidence_available"),
        (lambda p: p.update(dimension="taste"), "dimension"),
    ],
)
def test_invalid_priority_definitions_are_rejected(change, message, raw):
    change(find(raw["priorities"], "dimension", "water_use"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_a_missing_or_repeated_priority_is_rejected(raw):
    raw["priorities"] = [item for item in raw["priorities"] if item["dimension"] != "forage_value"]
    with pytest.raises(KnowledgeBaseError, match="no definition for priority: forage_value"):
        build_knowledge_base(raw)


def test_a_repeated_priority_is_rejected(raw):
    raw["priorities"].append(dict(find(raw["priorities"], "dimension", "water_use")))
    with pytest.raises(KnowledgeBaseError, match="priority definitions must not repeat"):
        build_knowledge_base(raw)
