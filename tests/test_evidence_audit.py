"""A4.1: the scientific evidence audit and the evidence gate.

These tests prove that unsupported scientific values cannot silently enter a
calculation: unverified, provisional, unsupported, contradicted, abstract-only
and unregistered claims are refused as numeric inputs, and conditional claims
are admitted only with their conditions.
"""

from __future__ import annotations

import pytest

from src.crop_knowledge import ReviewStatus
from src.evidence_audit import (
    AuditAction,
    AuditStatus,
    ClaimOverride,
    EvidenceAudit,
    EvidenceAuditError,
    EvidenceGate,
    EvidenceGateError,
    EvidenceUse,
    GateDecision,
    SourceAccess,
    build_evidence_audit,
)
from src.models import CropRequirement, EvidenceConfidence, ProvenanceRecord, RequirementBasis, Unit
from tests.conftest import find

ABSTRACT_SOURCES = ("franke-2018", "rao-mathuva-2000")

# Every crop variable that an A4 indicator calculates with.
A4_NUMERIC_VARIABLES = (
    "crop_temperature_requirement",
    "crop_annual_rainfall_requirement",
    "crop_soil_ph_requirement",
    "crop_seasonal_water_requirement",
    "crop_cycle_length",
    "crop_max_rooting_depth",
    "crop_depletion_fraction",
)


# --- The audit record ------------------------------------------------------------


def test_every_registered_source_was_audited_and_answered(kb, gate):
    audited = {item.source_id for item in gate.audit.sources}
    assert audited == {item.source_id for item in kb.sources}
    assert len(audited) == 13
    for item in gate.audit.sources:
        assert item.reachable and item.metadata_confirmed
        assert item.checked_url.startswith("https://")
        assert item.outcome


def test_audit_is_for_the_loaded_knowledge_base_version(kb, gate):
    assert gate.audit.knowledge_base_version == kb.manifest.knowledge_base_version
    assert str(gate.audit.audited_on) == "2026-11-15"


def test_both_abstract_only_sources_were_examined(kb, gate):
    for source_id in ABSTRACT_SOURCES:
        assert kb.get_source(source_id).review_status is ReviewStatus.ABSTRACT_READ
        record = gate.audit.source(source_id)
        assert "Abstract" in " ".join(record.rechecked_sections)
        assert "Crossref" in record.metadata_check
    assert gate.audit.source("franke-2018").access is SourceAccess.FULL_TEXT_OPEN_NOT_READ
    assert gate.audit.source("rao-mathuva-2000").access is SourceAccess.ABSTRACT_OPEN_FULL_TEXT_RESTRICTED


def test_abstract_only_sources_support_no_numeric_threshold(kb):
    # Neither abstract is the source of any crop requirement or soil reference.
    for crop in kb.crops:
        for requirement in crop.requirements:
            assert requirement.provenance.source_id not in ABSTRACT_SOURCES
    for reference in kb.soil_texture_references:
        assert reference.provenance.source_id not in ABSTRACT_SOURCES


def test_matrix_covers_every_claim_with_a_status_and_action(kb, gate):
    rows = gate.matrix()
    assert len(rows) == len(list(kb.claims())) == 205
    assert len({row.claim_id for row in rows}) == len(rows)
    for row in rows:
        assert row.claim and row.reason and row.geographic_applicability and row.crop_applicability
        assert row.action in AuditAction


def test_matrix_summary_is_as_audited(gate):
    summary = gate.summary()
    assert summary["status"] == {
        "verified_direct": 97,
        "verified_conditional": 78,
        "abstract_only": 22,
        "unverified": 8,
        "contradicted": 0,
    }
    assert summary["action"]["exclude_from_calculation"] == 8
    assert summary["rechecked"]["rechecked_in_a4"] + summary["rechecked"]["a3_reading_only"] == 205


def test_abstract_claims_are_background_only(gate):
    rows = [row for row in gate.matrix() if row.source_id in ABSTRACT_SOURCES]
    assert len(rows) == 23
    for row in rows:
        assert row.status in (AuditStatus.ABSTRACT_ONLY, AuditStatus.UNVERIFIED)
        assert EvidenceUse.NUMERIC_INPUT not in row.allowed_uses
        assert row.rechecked_in_a4


def test_provisional_and_unsupported_claims_are_excluded(gate):
    excluded = {row.where for row in gate.matrix() if row.action is AuditAction.EXCLUDE_FROM_CALCULATION}
    assert {
        "soil_reference:silty_clay",
        "relationship:same-family-repetition",
        "constraint:same-family-in-succession",
        "relationship:legume-effects-on-cereal-pests",
        "crop:sorghum:attribute:rainfall_note",
        "growth_stage:cowpea-mediterranean",
    } <= excluded


@pytest.mark.parametrize("variable", A4_NUMERIC_VARIABLES)
def test_every_value_a4_calculates_with_was_rechecked(kb, gate, variable):
    for crop in kb.crops:
        for requirement in crop.requirements_for(variable):
            row = gate.assess(f"crop:{crop.crop_id}:requirement:{requirement.requirement_id}", requirement.provenance)
            assert row.rechecked_in_a4, requirement.requirement_id


def test_soil_references_used_by_a4_were_rechecked(kb, gate):
    for reference in kb.soil_texture_references:
        row = gate.assess(f"soil_reference:{reference.texture_class.value}", reference.provenance)
        assert row.rechecked_in_a4


def test_frost_threshold_comes_from_a_method_source(gate):
    etccdi = gate.audit.method_source("etccdi-indices")
    assert any(item.startswith("FD:") and "below 0 °C" in item for item in etccdi.sections_read)
    finding = next(item for item in gate.audit.findings if item.finding_id == "frost-threshold-sourced")
    assert finding.action is AuditAction.REPLACE_WITH_VERIFIED_SOURCE


def test_no_claim_was_found_contradicted(gate):
    assert not [row for row in gate.matrix() if row.status is AuditStatus.CONTRADICTED]


# --- The gate ---------------------------------------------------------------------


def _requirement(kb, crop_id, requirement_id):
    crop = kb.get_crop(crop_id)
    return crop, next(item for item in crop.requirements if item.requirement_id == requirement_id)


def test_directly_supported_rechecked_value_is_admitted(kb, gate):
    crop, requirement = _requirement(kb, "maize", "maize-rooting-depth")
    decision = gate.requirement(crop, requirement)
    assert decision.admitted and decision.status is AuditStatus.VERIFIED_DIRECT


def test_conditional_value_is_admitted_only_with_its_conditions(kb, gate):
    crop, requirement = _requirement(kb, "maize", "maize-water-need")
    decision = gate.requirement(crop, requirement)
    assert decision.admitted and decision.status is AuditStatus.VERIFIED_CONDITIONAL
    assert requirement.limitation in decision.conditions


def test_override_condition_travels_with_the_value(kb, gate):
    crop, requirement = _requirement(kb, "pigeon-pea", "pigeon-pea-rainfall-lower")
    decision = gate.requirement(crop, requirement)
    assert decision.admitted
    assert any("deep and well-structured" in item for item in decision.conditions)


def test_qualified_value_is_refused_as_a_number_but_kept_as_background(kb, gate):
    crop, requirement = _requirement(kb, "common-bean", "common-bean-temperature-upper")
    assert not gate.requirement(crop, requirement).admitted
    assert gate.requirement(crop, requirement, EvidenceUse.BACKGROUND).admitted


def test_stage_specific_value_needs_known_stage_dates(kb, gate):
    crop, requirement = _requirement(kb, "sorghum", "sorghum-temperature-seedling")
    refused = gate.requirement(crop, requirement)
    assert not refused.admitted and "stage" in refused.reason
    assert gate.requirement(crop, requirement, stage_dates_known=True).admitted


def test_value_not_rechecked_in_a4_cannot_drive_a_calculation(kb, gate):
    crop, requirement = _requirement(kb, "maize", "maize-kc-mid")
    decision = gate.requirement(crop, requirement)
    assert not decision.admitted and "re-checked" in decision.reason
    assert gate.requirement(crop, requirement, EvidenceUse.BACKGROUND).admitted


def test_abstract_only_claim_is_refused_as_a_number(kb, gate):
    system = next(item for item in kb.cropping_systems if item.system_id == "machakos-maize-cowpea-rotation")
    where = f"cropping_system:{system.system_id}"
    numeric = gate.check(where, system.evidence[0], EvidenceUse.NUMERIC_INPUT)
    assert not numeric.admitted and "abstract" in numeric.reason
    background = gate.check(where, system.evidence[0], EvidenceUse.BACKGROUND)
    assert background.admitted and background.status is AuditStatus.ABSTRACT_ONLY
    assert any("abstract" in item for item in background.conditions)
    with pytest.raises(EvidenceGateError):
        gate.require(where, system.evidence[0], EvidenceUse.NUMERIC_INPUT)


def test_unsupported_claim_is_refused_for_every_use(kb, gate):
    constraint = next(item for item in kb.constraints if item.constraint_id == "same-family-in-succession")
    for use in EvidenceUse:
        assert not gate.check(f"constraint:{constraint.constraint_id}", constraint.evidence[0], use).admitted


def test_provisional_soil_reference_is_refused(kb, gate):
    from src.models import SoilTextureClass

    reference = kb.soil_reference(SoilTextureClass.SILTY_CLAY)
    decision = gate.check("soil_reference:silty_clay", reference.provenance, EvidenceUse.NUMERIC_INPUT)
    assert not decision.admitted and decision.status is AuditStatus.UNVERIFIED


def _injected_requirement(source_id: str, confidence: EvidenceConfidence) -> CropRequirement:
    return CropRequirement(
        requirement_id="maize-water-need-injected",
        variable="crop_seasonal_water_requirement",
        minimum=100,
        maximum=200,
        unit=Unit.MILLIMETRE,
        basis=RequirementBasis.TYPICAL,
        statement="An invented value for a test.",
        limitation="Invented for a test.",
        provenance=ProvenanceRecord(
            kind="literature_value",
            source_id=source_id,
            source_name="Test",
            citation="Test citation (fixture, not a real publication)",
            locator="Nowhere",
            confidence=confidence,
        ),
    )


def test_value_from_an_unregistered_source_cannot_enter(kb, gate):
    crop = kb.get_crop("maize")
    injected = _injected_requirement("not-a-registered-source", EvidenceConfidence.DIRECTLY_SUPPORTED)
    patched = crop.model_copy(update={"requirements": (*crop.requirements, injected)})
    decision = gate.requirement(patched, injected)
    assert not decision.admitted and decision.status is AuditStatus.UNVERIFIED
    admitted, refused = gate.admitted_requirements(patched, "crop_seasonal_water_requirement")
    assert injected in [item for item, _ in refused]
    assert injected not in [item for item, _ in admitted]


def test_value_slipped_into_a_crop_without_audit_cannot_enter(kb, gate):
    # A registered, read source, but the claim was never audited in A4.
    crop = kb.get_crop("maize")
    injected = _injected_requirement("fao-tm3", EvidenceConfidence.DIRECTLY_SUPPORTED)
    patched = crop.model_copy(update={"requirements": (*crop.requirements, injected)})
    decision = gate.requirement(patched, injected)
    assert not decision.admitted and "re-checked" in decision.reason


def test_requirement_must_belong_to_the_crop_it_is_used_for(kb, gate):
    maize, requirement = _requirement(kb, "maize", "maize-water-need")
    decision = gate.requirement(kb.get_crop("cowpea"), requirement)
    assert not decision.admitted and "not part of" in decision.reason


def test_contradicted_claim_is_never_admitted(kb, raw_audit):
    raw_audit["claim_overrides"].append(
        {
            "where": "crop:maize:requirement:maize-rooting-depth",
            "status": "contradicted",
            "action": "exclude_from_calculation",
            "allowed_uses": [],
            "reason": "Test: pretend the source says something else.",
        }
    )
    gate = EvidenceGate(kb, build_evidence_audit(raw_audit, kb))
    crop, requirement = _requirement(kb, "maize", "maize-rooting-depth")
    for use in EvidenceUse:
        decision = gate.requirement(crop, requirement, use)
        assert not decision.admitted and decision.status is AuditStatus.CONTRADICTED


def test_override_cannot_promote_an_abstract_claim_to_a_number():
    with pytest.raises(ValueError, match="abstract-only"):
        ClaimOverride(
            where="x", status="abstract_only", action="retain", allowed_uses=["numeric_input"], reason="r"
        )


def test_override_cannot_allow_an_unverified_claim():
    with pytest.raises(ValueError, match="unverified or contradicted"):
        ClaimOverride(where="x", status="unverified", action="retain", allowed_uses=["background"], reason="r")


def test_gate_decision_refuses_conditional_admission_without_conditions():
    with pytest.raises(ValueError, match="conditions"):
        GateDecision(
            claim_id="x",
            source_id="fao-56",
            use="numeric_input",
            admitted=True,
            status="verified_conditional",
            action="qualify",
            reason="r",
        )


# --- Integrity of the audit file ----------------------------------------------------


def test_audit_must_cover_every_registered_source(kb, raw_audit):
    raw_audit["sources"] = [item for item in raw_audit["sources"] if item["source_id"] != "fao-56"]
    with pytest.raises(EvidenceAuditError, match="every registered source"):
        build_evidence_audit(raw_audit, kb)


def test_audit_must_match_the_knowledge_base_version(kb, raw_audit):
    raw_audit["knowledge_base_version"] = "0.2.0"
    with pytest.raises(EvidenceAuditError, match="re-audit"):
        build_evidence_audit(raw_audit, kb)


def test_override_must_name_a_real_claim(kb, raw_audit):
    raw_audit["claim_overrides"][0]["where"] = "crop:maize:requirement:invented"
    with pytest.raises(EvidenceAuditError, match="unknown claim"):
        build_evidence_audit(raw_audit, kb)


def test_audit_file_is_validated(kb, raw_audit):
    find(raw_audit["sources"], "source_id", "fao-56")["access"] = "rumoured"
    with pytest.raises(EvidenceAuditError):
        build_evidence_audit(raw_audit, kb)


def test_audit_loads_offline(kb):
    from src.evidence_audit import load_evidence_gate

    assert isinstance(load_evidence_gate(kb).audit, EvidenceAudit)
