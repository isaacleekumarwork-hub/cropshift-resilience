"""The agronomic knowledge base: loading, evidence, crops, soil and A2 compatibility.

The value checks below were transcribed from the cited source tables when the
knowledge base was compiled (14 November 2026). They guard the data files
against accidental edits; they do not re-verify the sources.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date

import pytest

from src import crop_knowledge
from src.config import PROJECT_ROOT
from src.crop_knowledge import (
    KNOWLEDGE_DIRECTORY,
    KnowledgeBase,
    KnowledgeBaseError,
    MappingTarget,
    ReviewStatus,
    build_knowledge_base,
    load_knowledge_base,
)
from src.models import (
    CropLifeCycle,
    EvidenceConfidence,
    KnowledgeStatus,
    RequirementBasis,
    SoilTextureClass,
    Unit,
    get_variable,
)
from src.nasa_client import POWER_PARAMETERS
from src.pilot_sites import PILOT_SITE
from tests.conftest import find

CROP_IDS = ["common-bean", "cowpea", "maize", "mung-bean", "pigeon-pea", "sorghum"]


def crop_raw(raw, crop_id):
    return find(raw["crops"], "crop_id", crop_id)


def requirement_raw(raw, crop_id, requirement_id):
    return find(crop_raw(raw, crop_id)["requirements"], "requirement_id", requirement_id)


# --- Loading, versioning and offline use ---------------------------------------------


def test_knowledge_base_loads(kb):
    assert isinstance(kb, KnowledgeBase)
    assert [crop.crop_id for crop in kb.crops] == CROP_IDS
    assert len(kb.sources) == 13 and len(kb.relationships) == 15 and len(kb.constraints) == 14


def test_manifest_records_version_and_provisional_status(kb):
    manifest = kb.manifest
    assert manifest.schema_version == 1
    assert manifest.knowledge_base_version == "0.3.0"
    assert manifest.status is KnowledgeStatus.PROVISIONAL
    assert manifest.compiled_on == date(2026, 11, 14)
    assert manifest.pilot_site_id == PILOT_SITE.site_id
    assert manifest.pilot_site_approved is False and PILOT_SITE.approved is False


def test_loading_needs_no_network_interface_or_ai_service():
    # The autouse network guard is active in this process as well.
    assert load_knowledge_base() == load_knowledge_base()
    script = (
        "import sys; from src.crop_knowledge import load_knowledge_base; load_knowledge_base();"
        "loaded=[name for name in ('streamlit','openai','httpx') if name in sys.modules];"
        "sys.exit(1 if loaded else 0)"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=PROJECT_ROOT, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr.decode()


@pytest.fixture
def copied_knowledge(tmp_path):
    target = tmp_path / "knowledge"
    shutil.copytree(KNOWLEDGE_DIRECTORY, target)
    return target


def _edit(path, change):
    content = json.loads(path.read_text(encoding="utf-8"))
    change(content)
    path.write_text(json.dumps(content), encoding="utf-8")


def test_a_copy_of_the_knowledge_files_loads_identically(copied_knowledge, kb):
    assert load_knowledge_base(copied_knowledge) == kb


def test_unsupported_schema_versions_are_refused(copied_knowledge):
    _edit(copied_knowledge / "manifest.json", lambda content: content.update(schema_version=2))
    with pytest.raises(KnowledgeBaseError, match="schema version 2 is not supported"):
        load_knowledge_base(copied_knowledge)


def test_a_data_file_with_another_schema_version_is_refused(copied_knowledge):
    _edit(copied_knowledge / "crops.json", lambda content: content.update(schema_version=7))
    with pytest.raises(KnowledgeBaseError, match="crops.json has an unsupported schema version"):
        load_knowledge_base(copied_knowledge)


def test_missing_or_damaged_files_fail_clearly(copied_knowledge, tmp_path):
    with pytest.raises(KnowledgeBaseError, match="manifest.json is missing"):
        load_knowledge_base(tmp_path / "nowhere")
    (copied_knowledge / "soil_reference.json").unlink()
    with pytest.raises(KnowledgeBaseError, match="soil_reference.json is missing"):
        load_knowledge_base(copied_knowledge)


def test_malformed_json_fails_clearly(copied_knowledge):
    (copied_knowledge / "evidence_registry.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="evidence_registry.json is not valid JSON"):
        load_knowledge_base(copied_knowledge)


def test_invalid_version_string_is_refused(raw):
    raw["manifest"]["knowledge_base_version"] = "latest"
    with pytest.raises(KnowledgeBaseError, match="knowledge_base_version"):
        build_knowledge_base(raw)


# --- Deterministic ordering ----------------------------------------------------------


def test_records_come_back_in_a_fixed_order(kb):
    assert [item.source_id for item in kb.sources] == sorted(item.source_id for item in kb.sources)
    assert [item.crop_id for item in kb.crops] == sorted(CROP_IDS)
    assert [item.name for item in kb.families] == ["Fabaceae", "Poaceae"]
    assert [item.relationship_id for item in kb.relationships] == sorted(item.relationship_id for item in kb.relationships)
    assert [item.constraint_id for item in kb.constraints] == sorted(item.constraint_id for item in kb.constraints)
    assert [item.mapping_id for item in kb.variable_mappings] == sorted(item.mapping_id for item in kb.variable_mappings)
    classes = [item.texture_class for item in kb.soil_texture_references]
    assert classes == [item for item in SoilTextureClass if item in classes]


def test_file_order_does_not_change_the_result(raw, kb):
    for key in ("sources", "families", "crops", "growth_stage_examples", "soil_texture_references",
                "relationships", "constraints", "cropping_systems", "priorities", "variable_mappings"):
        raw[key] = list(reversed(raw[key]))
    shuffled = build_knowledge_base(raw)
    assert shuffled == kb
    assert shuffled.model_dump_json() == kb.model_dump_json()


def test_knowledge_base_round_trips_through_json(kb):
    assert KnowledgeBase.model_validate_json(kb.model_dump_json()) == kb


# --- Evidence registry ---------------------------------------------------------------


def test_every_source_is_identifiable_and_was_checked(kb):
    for source in kb.sources:
        assert source.url.startswith("https://")
        assert source.accessed_on == date(2026, 11, 14)
        assert source.sections_read and source.limitations and source.verification_note
        assert source.citation and source.institution and source.geographic_scope and source.crop_scope
    statuses = [source.review_status for source in kb.sources]
    assert statuses.count(ReviewStatus.CONTENT_READ) == 11
    assert statuses.count(ReviewStatus.ABSTRACT_READ) == 2
    assert {source.source_id: source.doi for source in kb.sources if source.doi} == {
        "franke-2018": "10.1016/j.agee.2017.09.029",
        "rao-mathuva-2000": "10.1016/S0167-8809(99)00125-5",
    }


def test_articles_read_only_in_abstract_say_so(kb):
    for source_id in ("franke-2018", "rao-mathuva-2000"):
        source = kb.get_source(source_id)
        assert source.review_status is ReviewStatus.ABSTRACT_READ
        assert source.sections_read == ("Abstract",)
        assert any("Only the abstract was read" in item for item in source.limitations)
        assert "Crossref" in source.verification_note


def test_every_claim_cites_a_registered_source_with_locator_and_confidence(kb):
    registered = {source.source_id for source in kb.sources}
    claims = list(kb.claims())
    assert len(claims) == 205
    for claim in claims:
        record = claim.provenance
        assert record.source_id in registered, claim.where
        assert record.citation and record.locator and record.confidence, claim.where
        assert record.url.startswith("https://")


def test_confidence_is_reported_in_words_and_counted(kb):
    assert kb.confidence_summary() == {
        "directly_supported": 118,
        "context_dependent": 79,
        "provisional": 5,
        "insufficient_evidence": 3,
    }
    assert sum(kb.claims_by_source().values()) == 205


def test_directly_supported_claims_rest_on_sources_that_were_read(kb):
    read = {source.source_id for source in kb.sources if source.review_status in crop_knowledge.READ_STATUSES}
    for claim in kb.claims():
        if claim.provenance.confidence is EvidenceConfidence.DIRECTLY_SUPPORTED:
            assert claim.provenance.source_id in read


def test_the_only_source_no_claim_cites_supports_the_pilot_site_description(kb):
    assert kb.unused_sources() == ("fao-giews-kenya",)
    assert "fao-giews-kenya" in PILOT_SITE.context_sources


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s.update(url="http://example.org/page"), "url"),
        (lambda s: s.update(doi="doi:10.1016/x"), "doi"),
        (lambda s: s.update(accessed_on="2999-01-01"), "future"),
        (lambda s: s.update(sections_read=[]), "must list the sections"),
        (lambda s: s.update(limitations=[]), "limitations"),
        (lambda s: s.update(review_status="skimmed"), "review_status"),
        (lambda s: s.pop("citation"), "citation"),
        (lambda s: s.update(year=1492), "year"),
    ],
)
def test_invalid_sources_are_rejected(change, message, raw):
    change(find(raw["sources"], "source_id", "fao-56"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_duplicate_source_identifiers_are_rejected(raw):
    raw["sources"].append(dict(find(raw["sources"], "source_id", "fao-56")))
    with pytest.raises(KnowledgeBaseError, match="source identifiers must not repeat"):
        build_knowledge_base(raw)


# --- Unsupported claims are rejected -------------------------------------------------


def test_unknown_evidence_reference_is_rejected(raw):
    requirement_raw(raw, "maize", "maize-kc-mid")["evidence"]["source_id"] = "a-source-that-does-not-exist"
    with pytest.raises(KnowledgeBaseError, match="unknown evidence reference 'a-source-that-does-not-exist'"):
        build_knowledge_base(raw)


def test_a_value_without_evidence_is_rejected(raw):
    del requirement_raw(raw, "maize", "maize-kc-mid")["evidence"]
    with pytest.raises(KnowledgeBaseError, match="maize-kc-mid.*every claim must cite a source"):
        build_knowledge_base(raw)


@pytest.mark.parametrize(("field", "message"), [("confidence", "confidence classification"), ("locator", "where in the source")])
def test_a_claim_missing_confidence_or_locator_is_rejected(field, message, raw):
    del requirement_raw(raw, "sorghum", "sorghum-kc-mid")["evidence"][field]
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_a_claim_cannot_be_directly_supported_by_an_unread_source(raw):
    find(raw["sources"], "source_id", "fao-tm3").update(review_status="metadata_only", sections_read=[])
    crop_raw(raw, "maize")["attributes"].append(
        {"attribute": "fixture", "statement": "Fixture.", "evidence": {
            "source_id": "fao-tm3", "locator": "Fixture", "confidence": "directly_supported"}}
    )
    with pytest.raises(KnowledgeBaseError, match="marked directly supported, but the source 'fao-tm3' was not read"):
        build_knowledge_base(raw)


def test_nitrogen_fixing_needs_a_cited_statement(raw):
    cowpea = crop_raw(raw, "cowpea")
    cowpea["attributes"] = [item for item in cowpea["attributes"] if item["attribute"] != "nitrogen_fixation"]
    with pytest.raises(KnowledgeBaseError, match="'cowpea' is marked nitrogen-fixing without a cited statement"):
        build_knowledge_base(raw)


def test_identity_needs_evidence(raw):
    crop_raw(raw, "maize")["identity_evidence"] = []
    with pytest.raises(KnowledgeBaseError, match="crop 'maize' identity: no evidence reference"):
        build_knowledge_base(raw)


# --- Invalid crop data is rejected ---------------------------------------------------


def test_duplicate_crop_identifiers_are_rejected(raw):
    raw["crops"].append(dict(crop_raw(raw, "maize")))
    with pytest.raises(KnowledgeBaseError, match="crop identifiers must not repeat"):
        build_knowledge_base(raw)


@pytest.mark.parametrize("field", ["crop_id", "common_name", "botanical_family", "functional_group", "nitrogen_fixing"])
def test_missing_mandatory_identifiers_are_rejected(field, raw):
    del crop_raw(raw, "sorghum")[field]
    with pytest.raises(KnowledgeBaseError, match=field):
        build_knowledge_base(raw)


def test_invalid_botanical_family_is_rejected(raw):
    crop_raw(raw, "maize")["botanical_family"] = "Brassicaceae"
    with pytest.raises(KnowledgeBaseError, match="'maize' names the family 'Brassicaceae', which is not in the knowledge base"):
        build_knowledge_base(raw)


def test_a_family_needs_evidence(raw):
    find(raw["families"], "name", "Poaceae")["evidence"] = []
    with pytest.raises(KnowledgeBaseError, match="family 'Poaceae': no evidence reference"):
        build_knowledge_base(raw)


def test_incorrect_units_are_rejected(raw):
    requirement_raw(raw, "maize", "maize-water-need")["unit"] = "mm/day"
    with pytest.raises(KnowledgeBaseError, match="must use unit 'mm'"):
        build_knowledge_base(raw)


def test_contradictory_ranges_are_rejected(raw):
    requirement_raw(raw, "maize", "maize-rooting-depth").update(minimum=1.7, maximum=1.0)
    with pytest.raises(KnowledgeBaseError, match="minimum must not be greater than maximum"):
        build_knowledge_base(raw)


def test_impossible_values_are_rejected(raw):
    requirement_raw(raw, "maize", "maize-soil-ph-tolerated")["maximum"] = 18.7
    with pytest.raises(KnowledgeBaseError, match="physical maximum"):
        build_knowledge_base(raw)


def test_invented_fields_are_rejected(raw):
    crop_raw(raw, "maize")["expected_yield_t_per_ha"] = 4.2
    with pytest.raises(KnowledgeBaseError, match="expected_yield_t_per_ha"):
        build_knowledge_base(raw)


# --- Crop profiles -------------------------------------------------------------------


def test_crop_selection_spans_two_families_with_legumes(kb):
    assert {crop.botanical_family for crop in kb.crops} == {"Fabaceae", "Poaceae"}
    assert [crop.crop_id for crop in kb.crops_in_family("Poaceae")] == ["maize", "sorghum"]
    assert [crop.crop_id for crop in kb.crops_in_family("Fabaceae")] == ["common-bean", "cowpea", "mung-bean", "pigeon-pea"]
    assert {crop.crop_id for crop in kb.crops if crop.nitrogen_fixing} == {"common-bean", "cowpea", "mung-bean", "pigeon-pea"}


def test_scientific_names_and_life_cycles(kb):
    assert {crop.crop_id: crop.scientific_name for crop in kb.crops} == {
        "common-bean": "Phaseolus vulgaris L.",
        "cowpea": "Vigna unguiculata (L.) Walp.",
        "maize": "Zea mays L.",
        "mung-bean": "Vigna radiata (L.) R. Wilczek",
        "pigeon-pea": "Cajanus cajan (L.) Huth",
        "sorghum": "Sorghum bicolor (L.) Moench",
    }
    assert kb.get_crop("pigeon-pea").life_cycle is CropLifeCycle.SHORT_LIVED_PERENNIAL
    assert kb.get_crop("sorghum").life_cycle is CropLifeCycle.ANNUAL
    assert kb.get_crop("maize").life_cycle_basis.startswith("Inferred, not stated")  # honesty about inference
    assert kb.get_crop("cowpea").life_cycle_basis.startswith("Stated by the source")


def test_every_profile_is_complete_and_none_claims_to_be_fully_reviewed(kb):
    for crop in kb.crops:
        assert crop.sources and crop.requirements and crop.attributes and crop.unknowns
        assert crop.limitations and crop.explanation is not None
        assert crop.data_quality in (KnowledgeStatus.PROVISIONAL, KnowledgeStatus.INCOMPLETE)
        for item in crop.requirements:
            assert item.statement and item.limitation
    assert {crop.crop_id for crop in kb.crops if crop.data_quality is KnowledgeStatus.INCOMPLETE} == {
        "cowpea", "mung-bean", "pigeon-pea"
    }


def test_unknown_crop_lookup_fails_clearly(kb):
    with pytest.raises(KnowledgeBaseError, match="no crop 'quinoa'"):
        kb.get_crop("quinoa")


TRANSCRIBED = [
    # crop, requirement id, variable, basis, minimum, maximum, unit, source
    ("maize", "maize-kc-initial", "crop_coefficient_initial", "typical", 0.3, 0.3, "dimensionless", "fao-56"),
    ("maize", "maize-kc-mid", "crop_coefficient_mid_season", "typical", 1.2, 1.2, "dimensionless", "fao-56"),
    ("maize", "maize-kc-end", "crop_coefficient_end_season", "typical", 0.35, 0.6, "dimensionless", "fao-56"),
    ("maize", "maize-max-height", "crop_max_height", "typical", 2.0, 2.0, "m", "fao-56"),
    ("maize", "maize-rooting-depth", "crop_max_rooting_depth", "typical", 1.0, 1.7, "m", "fao-56"),
    ("maize", "maize-depletion-fraction", "crop_depletion_fraction", "typical", 0.55, 0.55, "fraction", "fao-56"),
    ("maize", "maize-yield-response", "crop_yield_response_factor", "typical", 1.25, 1.25, "dimensionless", "fao-56"),
    ("maize", "maize-growing-period", "crop_cycle_length", "typical", 125, 180, "day", "fao-tm3"),
    ("maize", "maize-water-need", "crop_seasonal_water_requirement", "typical", 500, 800, "mm", "fao-tm3"),
    ("maize", "maize-temperature-optimal", "crop_temperature_requirement", "optimal", 18, 21, "degC", "feedipedia-maize-forage"),
    ("maize", "maize-rainfall-optimal", "crop_annual_rainfall_requirement", "optimal", 750, None, "mm", "feedipedia-maize-forage"),
    ("maize", "maize-rainfall-tolerated", "crop_annual_rainfall_requirement", "tolerated", 230, 4100, "mm", "feedipedia-maize-forage"),
    ("maize", "maize-soil-ph-tolerated", "crop_soil_ph_requirement", "tolerated", 4.3, 8.7, "pH", "feedipedia-maize-forage"),
    ("sorghum", "sorghum-kc-mid", "crop_coefficient_mid_season", "typical", 1.0, 1.1, "dimensionless", "fao-56"),
    ("sorghum", "sorghum-kc-end", "crop_coefficient_end_season", "typical", 0.55, 0.55, "dimensionless", "fao-56"),
    ("sorghum", "sorghum-max-height", "crop_max_height", "typical", 1.0, 2.0, "m", "fao-56"),
    ("sorghum", "sorghum-rooting-depth", "crop_max_rooting_depth", "typical", 1.0, 2.0, "m", "fao-56"),
    ("sorghum", "sorghum-depletion-fraction", "crop_depletion_fraction", "typical", 0.55, 0.55, "fraction", "fao-56"),
    ("sorghum", "sorghum-yield-response", "crop_yield_response_factor", "typical", 0.9, 0.9, "dimensionless", "fao-56"),
    ("sorghum", "sorghum-growing-period", "crop_cycle_length", "typical", 120, 130, "day", "fao-tm3"),
    ("sorghum", "sorghum-water-need", "crop_seasonal_water_requirement", "typical", 450, 650, "mm", "fao-tm3"),
    ("sorghum", "sorghum-temperature-seedling", "crop_temperature_requirement", "stage_specific", 25, 30, "degC", "feedipedia-sorghum-forage"),
    ("sorghum", "sorghum-temperature-growth", "crop_temperature_requirement", "stage_specific", 30, 30, "degC", "feedipedia-sorghum-forage"),
    ("sorghum", "sorghum-soil-ph-optimal", "crop_soil_ph_requirement", "optimal", 5.5, 7.5, "pH", "feedipedia-sorghum-forage"),
    ("common-bean", "common-bean-kc-initial", "crop_coefficient_initial", "typical", 0.4, 0.4, "dimensionless", "fao-56"),
    ("common-bean", "common-bean-kc-mid", "crop_coefficient_mid_season", "typical", 1.15, 1.15, "dimensionless", "fao-56"),
    ("common-bean", "common-bean-kc-end", "crop_coefficient_end_season", "typical", 0.35, 0.35, "dimensionless", "fao-56"),
    ("common-bean", "common-bean-rooting-depth", "crop_max_rooting_depth", "typical", 0.6, 0.9, "m", "fao-56"),
    ("common-bean", "common-bean-depletion-fraction", "crop_depletion_fraction", "typical", 0.45, 0.45, "fraction", "fao-56"),
    ("common-bean", "common-bean-yield-response", "crop_yield_response_factor", "typical", 1.15, 1.15, "dimensionless", "fao-56"),
    ("common-bean", "common-bean-growing-period", "crop_cycle_length", "typical", 95, 110, "day", "fao-tm3"),
    ("common-bean", "common-bean-water-need", "crop_seasonal_water_requirement", "typical", 300, 500, "mm", "fao-tm3"),
    ("common-bean", "common-bean-temperature-suitable", "crop_temperature_requirement", "suitable", 15, 23, "degC", "feedipedia-common-bean"),
    ("common-bean", "common-bean-temperature-upper", "crop_temperature_requirement", "tolerated", None, 35, "degC", "feedipedia-common-bean"),
    ("common-bean", "common-bean-temperature-lower", "crop_temperature_requirement", "tolerated", 10, None, "degC", "feedipedia-common-bean"),
    ("common-bean", "common-bean-rainfall-optimal", "crop_annual_rainfall_requirement", "optimal", 500, 1500, "mm", "feedipedia-common-bean"),
    ("common-bean", "common-bean-rainfall-tolerated", "crop_annual_rainfall_requirement", "tolerated", 300, 4300, "mm", "feedipedia-common-bean"),
    ("common-bean", "common-bean-soil-ph-suitable", "crop_soil_ph_requirement", "suitable", 4, 9, "pH", "feedipedia-common-bean"),
    ("cowpea", "cowpea-kc-mid", "crop_coefficient_mid_season", "typical", 1.05, 1.05, "dimensionless", "fao-56"),
    ("cowpea", "cowpea-kc-end", "crop_coefficient_end_season", "typical", 0.35, 0.6, "dimensionless", "fao-56"),
    ("cowpea", "cowpea-rooting-depth", "crop_max_rooting_depth", "typical", 0.6, 1.0, "m", "fao-56"),
    ("cowpea", "cowpea-depletion-fraction", "crop_depletion_fraction", "typical", 0.45, 0.45, "fraction", "fao-56"),
    ("cowpea", "cowpea-temperature-suitable", "crop_temperature_requirement", "suitable", 25, 35, "degC", "feedipedia-cowpea-forage"),
    ("cowpea", "cowpea-rainfall-suitable", "crop_annual_rainfall_requirement", "suitable", 750, 1100, "mm", "feedipedia-cowpea-forage"),
    ("pigeon-pea", "pigeon-pea-rooting-depth", "crop_max_rooting_depth", "typical", 2.0, 2.0, "m", "feedipedia-pigeon-pea-forage"),
    ("pigeon-pea", "pigeon-pea-temperature-suitable", "crop_temperature_requirement", "suitable", 20, 40, "degC", "feedipedia-pigeon-pea-forage"),
    ("pigeon-pea", "pigeon-pea-rainfall-preferred", "crop_annual_rainfall_requirement", "optimal", 625, None, "mm", "feedipedia-pigeon-pea-forage"),
    ("pigeon-pea", "pigeon-pea-rainfall-lower", "crop_annual_rainfall_requirement", "tolerated", 250, None, "mm", "feedipedia-pigeon-pea-forage"),
    ("pigeon-pea", "pigeon-pea-soil-ph-optimal", "crop_soil_ph_requirement", "optimal", 5, 7, "pH", "feedipedia-pigeon-pea-forage"),
    ("mung-bean", "mung-bean-kc-mid", "crop_coefficient_mid_season", "typical", 1.05, 1.05, "dimensionless", "fao-56"),
    ("mung-bean", "mung-bean-rooting-depth", "crop_max_rooting_depth", "typical", 0.6, 1.0, "m", "fao-56"),
    ("mung-bean", "mung-bean-temperature-optimal", "crop_temperature_requirement", "optimal", 28, 30, "degC", "feedipedia-mung-bean"),
    ("mung-bean", "mung-bean-temperature-lower", "crop_temperature_requirement", "tolerated", 15, None, "degC", "feedipedia-mung-bean"),
    ("mung-bean", "mung-bean-rainfall-suitable", "crop_annual_rainfall_requirement", "suitable", 600, 1000, "mm", "feedipedia-mung-bean"),
    ("mung-bean", "mung-bean-soil-ph-suitable", "crop_soil_ph_requirement", "suitable", 5, 8, "pH", "feedipedia-mung-bean"),
]


@pytest.mark.parametrize(
    ("crop_id", "requirement_id", "variable", "basis", "minimum", "maximum", "unit", "source_id"),
    TRANSCRIBED,
    ids=[row[1] for row in TRANSCRIBED],
)
def test_values_match_what_was_transcribed_from_the_sources(
    kb, crop_id, requirement_id, variable, basis, minimum, maximum, unit, source_id
):
    crop = kb.get_crop(crop_id)
    item = next(entry for entry in crop.requirements if entry.requirement_id == requirement_id)
    assert item.variable == variable
    assert item.basis.value == basis
    assert (item.minimum, item.maximum) == (minimum, maximum)
    assert item.unit.value == unit and item.unit is get_variable(variable).unit
    assert item.provenance.source_id == source_id


def test_no_value_exists_that_was_not_transcribed(kb):
    held = {item.requirement_id for crop in kb.crops for item in crop.requirements}
    checked = {row[1] for row in TRANSCRIBED}
    unchecked = held - checked
    # Every remaining value is a group-level or shared-row figure, checked here.
    assert unchecked == {
        "sorghum-kc-initial", "cowpea-kc-initial", "mung-bean-kc-initial",
        "common-bean-max-height", "cowpea-max-height", "mung-bean-max-height",
        "mung-bean-kc-end", "mung-bean-depletion-fraction", "pigeon-pea-height",
    }
    by_id = {item.requirement_id: item for crop in kb.crops for item in crop.requirements}
    assert by_id["sorghum-kc-initial"].minimum == 0.3
    assert by_id["cowpea-kc-initial"].minimum == by_id["mung-bean-kc-initial"].minimum == 0.4
    assert by_id["common-bean-max-height"].minimum == by_id["cowpea-max-height"].minimum == 0.4
    assert (by_id["mung-bean-kc-end"].minimum, by_id["mung-bean-kc-end"].maximum) == (0.35, 0.6)
    assert by_id["mung-bean-depletion-fraction"].minimum == 0.45
    assert (by_id["pigeon-pea-height"].minimum, by_id["pigeon-pea-height"].maximum) == (1.0, 2.0)


def test_survival_suitable_and_optimal_thresholds_are_kept_apart(kb):
    bean = kb.get_crop("common-bean")
    temperatures = bean.requirements_for("crop_temperature_requirement")
    assert {item.basis for item in temperatures} == {RequirementBasis.SUITABLE, RequirementBasis.TOLERATED}
    assert len(temperatures) == 3  # three separate statements, never merged into one range
    assert bean.requirements_for("crop_temperature_requirement", RequirementBasis.OPTIMAL) == ()

    sorghum = kb.get_crop("sorghum").requirements_for("crop_temperature_requirement")
    assert all(item.basis is RequirementBasis.STAGE_SPECIFIC and item.growth_stage for item in sorghum)

    maize = kb.get_crop("maize")
    assert len(maize.requirements_for("crop_annual_rainfall_requirement", RequirementBasis.OPTIMAL)) == 1
    assert len(maize.requirements_for("crop_annual_rainfall_requirement", RequirementBasis.TOLERATED)) == 1


def test_crop_water_need_is_never_presented_as_rainfall_demand(kb):
    found = 0
    for crop in kb.crops:
        for item in crop.requirements_for("crop_seasonal_water_requirement"):
            found += 1
            assert "evapotranspiration" in item.limitation and "not the rainfall it needs" in item.limitation
            assert item.original_unit == "mm/total growing period"
    assert found == 3
    for crop in kb.crops:
        for item in crop.requirements_for("crop_annual_rainfall_requirement"):
            assert "annual" in item.limitation.lower()


def test_secondary_sources_are_not_treated_as_firm_numbers(kb):
    for crop in kb.crops:
        for item in crop.requirements:
            if item.provenance.source_id.startswith("feedipedia") and item.variable in (
                "crop_annual_rainfall_requirement", "crop_soil_ph_requirement"
            ):
                assert item.provenance.confidence is EvidenceConfidence.CONTEXT_DEPENDENT


# --- Unknown values stay unknown -----------------------------------------------------


def test_gaps_are_recorded_instead_of_filled(kb):
    cowpea = kb.get_crop("cowpea")
    assert cowpea.is_unknown("soil_ph") and cowpea.requirements_for("crop_soil_ph_requirement") == ()
    assert cowpea.is_unknown("seasonal_water_need") and cowpea.requirements_for("crop_seasonal_water_requirement") == ()
    assert cowpea.is_unknown("growing_period") and cowpea.requirements_for("crop_cycle_length") == ()

    pigeon_pea = kb.get_crop("pigeon-pea")
    assert pigeon_pea.is_unknown("crop_coefficients")
    for variable in ("crop_coefficient_initial", "crop_coefficient_mid_season", "crop_coefficient_end_season",
                     "crop_depletion_fraction", "crop_cycle_length", "crop_seasonal_water_requirement"):
        assert pigeon_pea.requirements_for(variable) == ()

    sorghum = kb.get_crop("sorghum")
    assert sorghum.is_unknown("annual_rainfall_range")
    assert sorghum.requirements_for("crop_annual_rainfall_requirement") == ()  # ambiguous source, not encoded
    assert "ambiguous" in next(item.statement for item in sorghum.attributes if item.attribute == "rainfall_note")

    for crop in kb.crops:
        assert crop.is_unknown("base_temperature") or crop.crop_id in {"cowpea", "pigeon-pea", "mung-bean"}
        for unknown in crop.unknowns:
            assert unknown.reason


def test_unknowns_report_lists_every_crop(kb):
    report = kb.unknowns()
    assert list(report) == CROP_IDS and all(report.values())
    assert "nitrogen_left_for_next_crop" in report["common-bean"]


# --- Regional evidence and the unapproved pilot site ---------------------------------


def test_regional_evidence_is_separate_and_limited_to_what_was_read(kb):
    with_evidence = {crop.crop_id for crop in kb.crops if crop.regional_evidence}
    assert with_evidence == {"cowpea", "maize", "pigeon-pea"}
    for crop_id in with_evidence:
        trial = next(item for item in kb.get_crop(crop_id).regional_evidence if item.attribute == "machakos_trial")
        assert trial.provenance.source_id == "rao-mathuva-2000"
        assert "1989" in trial.provenance.applicability
    for crop_id in ("common-bean", "mung-bean", "sorghum"):
        crop = kb.get_crop(crop_id)
        assert crop.is_unknown("regional_use")
        assert any("No evidence specific to the pilot region" in item for item in crop.limitations)


def test_no_record_claims_suitability_for_the_unapproved_pilot_site(kb):
    text = kb.model_dump_json().lower()
    for claim in ("suitable for the pilot", "recommended for", "best crop", "well suited to machakos", "suits the pilot"):
        assert claim not in text
    assert any("no record claims that a crop suits that site" in note for note in kb.manifest.notes)


def test_pilot_site_background_is_now_cited(kb):
    assert PILOT_SITE.context_is_cited is True
    for source_id in PILOT_SITE.context_sources:
        assert kb.get_source(source_id)
    assert PILOT_SITE.context_assumptions  # the inference linking the site to FAO's zone is declared
    assert "national dryland research station" not in PILOT_SITE.agricultural_context  # uncited claim removed


def test_explanations_have_five_parts_and_flag_regional_evidence(kb):
    for crop in kb.crops:
        explanation = crop.explanation
        for part in ("what_is_known", "why_it_matters", "evidence_summary", "what_is_uncertain"):
            assert len(getattr(explanation, part)) > 30
    assert {crop.crop_id for crop in kb.crops if crop.explanation.region_specific} == {"cowpea", "pigeon-pea"}


# --- Growth-stage examples -----------------------------------------------------------


def test_growth_stage_examples_keep_the_source_figures_and_flag_inconsistencies(kb):
    examples = {item.example_id: item for item in kb.growth_stage_examples}
    assert len(examples) == 7
    maize = examples["maize-east-africa-altitude"]
    assert (maize.initial_days, maize.development_days, maize.mid_season_days, maize.late_season_days, maize.total_days) == (30, 50, 60, 40, 180)
    assert maize.is_internally_consistent and maize.discrepancy_note is None

    inconsistent = {name for name, item in examples.items() if not item.is_internally_consistent}
    assert inconsistent == {"sorghum-arid-region", "sorghum-usa-pakistan-mediterranean", "cowpea-mediterranean"}
    for name in inconsistent:
        item = examples[name]
        assert item.discrepancy_note and item.provenance.confidence is EvidenceConfidence.PROVISIONAL
    assert (examples["sorghum-arid-region"].stage_sum, examples["sorghum-arid-region"].total_days) == (130, 140)
    assert [item.example_id for item in kb.growth_stages_for("common-bean")] == [
        "common-bean-continental", "common-bean-pakistan-california"
    ]


def test_an_inconsistent_row_must_be_flagged(raw):
    example = find(raw["growth_stage_examples"], "example_id", "sorghum-arid-region")
    del example["discrepancy_note"]
    with pytest.raises(KnowledgeBaseError, match="add up to 130, not the stated total 140"):
        build_knowledge_base(raw)


def test_an_inconsistent_row_cannot_be_presented_as_firm(raw):
    find(raw["growth_stage_examples"], "example_id", "sorghum-arid-region")["evidence"]["confidence"] = "directly_supported"
    with pytest.raises(KnowledgeBaseError, match="can only be provisional"):
        build_knowledge_base(raw)


def test_a_consistent_row_cannot_carry_a_discrepancy_note(raw):
    find(raw["growth_stage_examples"], "example_id", "maize-arid-climate")["discrepancy_note"] = "Fixture."
    with pytest.raises(KnowledgeBaseError, match="only for rows whose stages do not add up"):
        build_knowledge_base(raw)


def test_growth_stage_example_must_name_a_known_crop(raw):
    find(raw["growth_stage_examples"], "example_id", "maize-arid-climate")["crop_id"] = "teff"
    with pytest.raises(KnowledgeBaseError, match="names an unknown crop"):
        build_knowledge_base(raw)


# --- Soil reference values -----------------------------------------------------------


def test_soil_reference_values_by_texture_class(kb):
    assert len(kb.soil_texture_references) == 9
    loam = kb.soil_reference(SoilTextureClass.LOAM)
    assert (loam.field_capacity_min, loam.field_capacity_max) == (0.20, 0.30)
    assert (loam.wilting_point_min, loam.wilting_point_max) == (0.07, 0.17)
    assert (loam.available_water_min, loam.available_water_max) == (0.13, 0.18)
    assert loam.unit is Unit.CUBIC_METRE_PER_CUBIC_METRE and loam.provenance.source_id == "fao-56"
    sand, clay = kb.soil_reference(SoilTextureClass.SAND), kb.soil_reference(SoilTextureClass.CLAY)
    assert sand.field_capacity_max < clay.field_capacity_min  # sands hold less water than clays
    for reference in kb.soil_texture_references:
        assert "Not a measurement of any field" in reference.provenance.applicability


def test_texture_classes_absent_from_the_source_stay_absent(kb):
    for missing in (SoilTextureClass.SANDY_CLAY_LOAM, SoilTextureClass.CLAY_LOAM, SoilTextureClass.SANDY_CLAY):
        assert kb.soil_reference(missing) is None


def test_the_scanning_error_in_the_source_is_declared(kb):
    silty_clay = kb.soil_reference(SoilTextureClass.SILTY_CLAY)
    assert silty_clay.field_capacity_min == 0.30
    assert silty_clay.provenance.confidence is EvidenceConfidence.PROVISIONAL
    assert "'0-30 - 0.42'" in silty_clay.note and silty_clay.provenance.transformations
    firm = [item for item in kb.soil_texture_references if item.provenance.confidence is EvidenceConfidence.DIRECTLY_SUPPORTED]
    assert len(firm) == 8


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: r.update(field_capacity_min=0.5), "field capacity: minimum must not be greater"),
        (lambda r: r.update(wilting_point_min=0.9, wilting_point_max=0.95), "must be able to exceed the wilting point"),
        (lambda r: r.update(available_water_max=1.5), "available_water_max"),
        (lambda r: r.update(texture_class="gravel"), "texture_class"),
    ],
)
def test_invalid_soil_reference_values_are_rejected(change, message, raw):
    change(find(raw["soil_texture_references"], "texture_class", "loam"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


def test_duplicate_soil_reference_is_rejected(raw):
    raw["soil_texture_references"].append(dict(find(raw["soil_texture_references"], "texture_class", "loam")))
    with pytest.raises(KnowledgeBaseError, match="soil texture references must not repeat"):
        build_knowledge_base(raw)


# --- Compatibility with the A2 data layer ---------------------------------------------

DATA_LAYER_VARIABLES = {item.variable for item in POWER_PARAMETERS.values()} | {"precipitation_total"}


def test_mappings_marked_available_use_only_variables_the_data_layer_supplies(kb):
    for mapping in kb.variable_mappings:
        if mapping.available_from_data_layer:
            assert mapping.target is MappingTarget.NASA_OBSERVATION
            assert set(mapping.target_variables) <= DATA_LAYER_VARIABLES, mapping.mapping_id
        assert mapping.implemented is False  # contracts only; A4 does the comparison


def test_soil_and_derived_inputs_are_never_marked_as_available_from_nasa(kb):
    for mapping in kb.variable_mappings:
        if mapping.target is not MappingTarget.NASA_OBSERVATION:
            assert mapping.available_from_data_layer is False
    soil_ph = kb.mappings_for("crop_soil_ph_requirement")[0]
    assert soil_ph.target is MappingTarget.SOIL_INFORMATION
    assert any("never inferred from NASA" in item for item in soil_ph.limitations)
    for mapping in kb.variable_mappings:
        if "reference_evapotranspiration" in mapping.target_variables and mapping.crop_variable.startswith("crop_coefficient"):
            assert any("wind speed" in item for item in mapping.limitations)


@pytest.mark.parametrize(
    ("crop_variable", "target_variable"),
    [
        ("crop_temperature_requirement", "air_temperature_mean"),
        ("crop_temperature_requirement", "air_temperature_max"),
        ("crop_temperature_requirement", "air_temperature_min"),
        ("crop_annual_rainfall_requirement", "precipitation_total"),
        ("crop_seasonal_water_requirement", "precipitation_total"),
        ("crop_soil_ph_requirement", "soil_ph"),
    ],
)
def test_mapped_variables_share_a_unit(kb, crop_variable, target_variable):
    assert any(target_variable in mapping.target_variables for mapping in kb.mappings_for(crop_variable))
    assert get_variable(crop_variable).unit is get_variable(target_variable).unit


def test_requirements_line_up_with_the_real_nasa_observations(kb, make_settings, tmp_path):
    from src.data_processing import monthly_summary
    from src.data_service import load_pilot_dataset

    dataset = load_pilot_dataset(settings=make_settings(offline_demo_mode=True, nasa_cache_directory=tmp_path / "cache"))
    maize_temperature = kb.get_crop("maize").requirements_for("crop_temperature_requirement")[0]
    assert dataset.get("air_temperature_mean").unit is maize_temperature.unit

    monthly = monthly_summary(dataset)
    rain = monthly[monthly["variable"] == "precipitation"].iloc[0]
    maize_water = kb.get_crop("maize").requirements_for("crop_seasonal_water_requirement")[0]
    assert rain["unit"] == maize_water.unit.value == "mm"
    assert rain["output_variable"] == "precipitation_total"
    # A daily rate (mm/day) is a different unit and must never be compared with a seasonal need.
    assert dataset.get("precipitation").unit is not maize_water.unit


def test_mapping_limits_are_stated(kb):
    temperature = kb.mappings_for("crop_temperature_requirement")[0]
    assert any("short spells" in item for item in temperature.limitations)
    assert any("disease incidence or yield" in item for item in temperature.limitations)
    water = kb.mappings_for("crop_seasonal_water_requirement")[0]
    assert any("not rainfall demand" in item for item in water.limitations)
    assert any("irrigation" in item for item in water.limitations)
    for mapping in kb.variable_mappings:
        assert mapping.limitations and mapping.comparison_intent and mapping.temporal_basis


def test_every_comparable_crop_variable_has_a_mapping(kb):
    used = {item.variable for crop in kb.crops for item in crop.requirements}
    mapped = {mapping.crop_variable for mapping in kb.variable_mappings}
    assert used - mapped == {"crop_max_height"}  # descriptive only


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda m: m.update(crop_variable="air_temperature_mean"), "not a crop variable"),
        (lambda m: m.update(target_variables=["soil_ph"]), "not a environment variable"),
        (lambda m: m.update(target_variables=[]), "target_variables"),
        (lambda m: m.update(implemented=True), "implemented"),
        (lambda m: m.update(limitations=[]), "limitations"),
        (lambda m: m.update(target="soil_information", target_variables=["soil_ph"], available_from_data_layer=True),
         "never comes from the NASA data layer"),
    ],
)
def test_invalid_mappings_are_rejected(change, message, raw):
    change(find(raw["variable_mappings"], "mapping_id", "temperature-requirement-to-air-temperature"))
    with pytest.raises(KnowledgeBaseError, match=message):
        build_knowledge_base(raw)


# --- Scope: knowledge only ------------------------------------------------------------


def test_knowledge_module_ranks_and_recommends_nothing():
    forbidden = ("rank", "recommend", "score", "optimi", "suitab", "predict", "yield", "evaluate", "compare")
    public = [name for name in vars(crop_knowledge) if not name.startswith("_")]
    assert not [name for name in public if any(word in name.lower() for word in forbidden)]
    methods = [name for name in dir(KnowledgeBase) if not name.startswith("_")]
    assert not [name for name in methods if any(word in name.lower() for word in forbidden)]


def test_knowledge_files_hold_no_economic_or_yield_estimates():
    for path in KNOWLEDGE_DIRECTORY.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        for key in ('"price"', '"profit"', '"gross_margin"', '"expected_yield"', '"weight"'):
            assert key not in text, f"{path.name} contains {key}"
