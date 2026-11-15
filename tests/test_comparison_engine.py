"""A4.5 to A4.8: the comparison engine, farmer priorities and uncertainty.

The report fixtures run the whole engine on the real bundled NASA pilot data,
offline, with the real knowledge base and evidence audit.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.comparison_engine import (
    INDICATORS,
    PRIORITY_INDICATORS,
    ComparisonReport,
    ConstraintOutcome,
    EvidenceUsed,
    IndicatorResult,
    IndicatorStatus,
    PrioritySelection,
    assess_strategy,
    compare_strategies,
    evaluate_constraints,
    run_pilot_comparison,
)
from src.crop_knowledge import KnowledgeBaseError
from src.evidence_audit import EvidenceGate
from src.models import (
    ConfidenceLevel,
    CropRequirement,
    EvidenceConfidence,
    PriorityDimension,
    ProvenanceRecord,
    RequirementBasis,
    RotationRole,
    UncertaintyCategory,
    Unit,
)
from src.scenario_engine import build_scenarios
from src.season_config import (
    CANDIDATE_STRATEGIES,
    CONTINUOUS_MAIZE,
    MAIZE_COWPEA,
    MAIZE_PIGEON_PEA,
    RotationStrategy,
    SeasonAssignment,
    StrategyEvidence,
    UnknownCropError,
    pilot_configuration,
)
from src.soil_inputs import SoilProfileInput, SoilSourceClass, SoilValueInput, demonstration_soil_profile
from src.uncertainty import UNSUPPORTED_OUTCOMES, InformationLayer, assess

STAMP = datetime(2026, 11, 15, 1, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def config():
    return pilot_configuration()


@pytest.fixture(scope="module")
def scenarios(pilot_dataset, config):
    return build_scenarios(pilot_dataset, config.windows)


@pytest.fixture(scope="module")
def report(scenarios, kb, gate, config) -> ComparisonReport:
    return compare_strategies(scenarios=scenarios, kb=kb, gate=gate, config=config, generated_at=STAMP)


@pytest.fixture(scope="module")
def soil_report(scenarios, kb, gate, config) -> ComparisonReport:
    return compare_strategies(
        scenarios=scenarios, kb=kb, gate=gate, config=config, generated_at=STAMP,
        soil=demonstration_soil_profile(),
        priorities=PrioritySelection(
            dimensions=(PriorityDimension.WATER_USE, PriorityDimension.MARKET_SUITABILITY, PriorityDimension.CROP_DIVERSITY)
        ),
    )


def indicators(report, strategy_id, indicator_id, **match):
    return report.strategy(strategy_id).indicator(indicator_id, **match)


# --- Strategies -----------------------------------------------------------------


def test_three_candidate_strategies_are_the_documented_machakos_systems(kb):
    rotations = {item.system_id for item in kb.documented_rotations()}
    for strategy in CANDIDATE_STRATEGIES:
        assert strategy.evidence is StrategyEvidence.DOCUMENTED_SYSTEM
        assert strategy.season_assignment is SeasonAssignment.UNKNOWN
        assert strategy.documented_system_id in rotations | {"machakos-continuous-maize"}
    assert [item.strategy_id for item in CANDIDATE_STRATEGIES] == ["continuous-maize", "maize-cowpea", "maize-pigeon-pea"]


def test_only_the_baseline_is_marked_as_current_practice_and_it_says_why():
    assert CONTINUOUS_MAIZE.role is RotationRole.CURRENT_PRACTICE
    assert MAIZE_COWPEA.role is MAIZE_PIGEON_PEA.role is RotationRole.ALTERNATIVE
    assert any("baseline" in item for item in CONTINUOUS_MAIZE.assumptions)


def test_sequence_order_and_families_are_preserved(report):
    profile = report.strategy("maize-pigeon-pea").profile
    assert [(item.position, item.crop_id) for item in profile.crops] == [(1, "maize"), (2, "pigeon-pea")]
    assert profile.families == ("Fabaceae", "Poaceae")
    assert report.strategy("continuous-maize").profile.families == ("Poaceae",)


def test_unknown_crop_is_rejected(scenarios, kb, gate, config):
    invented = RotationStrategy(
        strategy_id="maize-teff", name="Maize and teff", crop_sequence=("maize", "teff"), role=RotationRole.ALTERNATIVE,
        evidence=StrategyEvidence.HYPOTHETICAL, description="Test input.",
    )
    with pytest.raises(UnknownCropError, match="teff"):
        compare_strategies((invented,), scenarios=scenarios, kb=kb, gate=gate, config=config)


def test_strategy_must_use_the_crops_of_the_system_it_cites(scenarios, kb, gate, config):
    wrong = MAIZE_COWPEA.model_copy(update={"crop_sequence": ("maize", "sorghum")})
    with pytest.raises(KnowledgeBaseError, match="does not use the crops"):
        compare_strategies((wrong,), scenarios=scenarios, kb=kb, gate=gate, config=config)


@pytest.mark.parametrize(
    "fields, message",
    [
        (dict(evidence=StrategyEvidence.DOCUMENTED_SYSTEM, documented_system_id=None), "name the cropping system"),
        (dict(evidence=StrategyEvidence.HYPOTHETICAL, documented_system_id="x"), "cannot claim"),
        (dict(slot_seasons=("long-rains",)), "hypothetical, not unknown"),
        (dict(season_assignment=SeasonAssignment.HYPOTHETICAL, slot_seasons=("long-rains",)), "declared"),
        (dict(planting_dates="documented"), "planting dates"),
    ],
)
def test_strategy_contract_rules(fields, message):
    base = dict(
        strategy_id="test", name="Test", crop_sequence=("maize",), role=RotationRole.ALTERNATIVE,
        evidence=StrategyEvidence.HYPOTHETICAL, description="Test input.",
    )
    base.update(fields)
    with pytest.raises(ValidationError, match=message):
        RotationStrategy(**base)


def test_hypothetical_season_assignment_is_labelled_and_used(scenarios, kb, gate, config):
    chosen = MAIZE_COWPEA.with_seasons(("long-rains", "short-rains"), reason="test choice")
    assessment = assess_strategy(chosen, scenarios=scenarios, soil=resolve(None, config, gate), kb=kb, gate=gate, config=config)
    assert assessment.uses_hypothetical_inputs
    assert any("does not reproduce the design" in item for item in assessment.strategy.assumptions)
    maize = {item.window_id for item in assessment.indicator("rainfall_vs_crop_water_use", crop_id="maize")}
    cowpea = {item.window_id for item in assessment.indicator("temperature_vs_documented_range", crop_id="cowpea")}
    assert maize == {"long-rains"} and cowpea == {"short-rains"}


def resolve(profile, config, gate):
    from src.soil_inputs import resolve_soil

    return resolve_soil(profile, location=config.location, gate=gate)


def test_unknown_season_assignment_evaluates_every_window(report):
    windows = {item.window_id for item in indicators(report, "maize-cowpea", "rainfall_vs_crop_water_use", crop_id="maize")}
    assert windows == {"long-rains", "short-rains"}
    assert not report.strategy("maize-cowpea").uses_hypothetical_inputs


# --- Indicators -------------------------------------------------------------------


def test_pigeon_pea_water_indicators_remain_unavailable(report):
    for window in ("long-rains", "short-rains"):
        (result,) = indicators(report, "maize-pigeon-pea", "rainfall_vs_crop_water_use", crop_id="pigeon-pea", window_id=window)
        assert result.status is IndicatorStatus.UNAVAILABLE
        assert result.values == () and result.season_findings == ()
        assert result.uncertainty.confidence is ConfidenceLevel.NOT_ASSESSED
        assert UncertaintyCategory.UNSUPPORTED_INDICATOR in result.uncertainty.categories


def test_cowpea_water_use_is_not_borrowed_from_another_crop(report):
    for result in indicators(report, "maize-cowpea", "rainfall_vs_crop_water_use", crop_id="cowpea"):
        assert result.status is IndicatorStatus.UNAVAILABLE and "cowpea" in result.headline.lower()


def test_pigeon_pea_readily_available_water_is_unavailable_even_with_soil(soil_report):
    (taw,) = indicators(soil_report, "maize-pigeon-pea", "root_zone_available_water", crop_id="pigeon-pea")
    (raw,) = indicators(soil_report, "maize-pigeon-pea", "readily_available_water", crop_id="pigeon-pea")
    assert taw.status is IndicatorStatus.CONDITIONAL and raw.status is IndicatorStatus.UNAVAILABLE


def test_rainfall_indicator_uses_the_nasa_season_totals(report, scenarios):
    (result,) = indicators(report, "continuous-maize", "rainfall_vs_crop_water_use", crop_id="maize", window_id="long-rains")
    window = scenarios.window("long-rains")
    for finding in result.season_findings:
        assert finding.value == window.season(finding.season_id).rainfall_total_mm
        assert finding.category is window.season(finding.season_id).category
    assert sum(item.seasons for item in result.category_summaries) == 25
    positions = [item.position for item in result.season_findings]
    assert positions.count("below") == sum(1 for item in result.season_findings if item.value < 500)


def test_rainfall_indicator_never_claims_irrigation_or_water_balance(report):
    (result,) = indicators(report, "continuous-maize", "rainfall_vs_crop_water_use", crop_id="maize", window_id="short-rains")
    assert result.status is IndicatorStatus.CONDITIONAL
    assert any("not directly comparable" in item for item in result.conditions)
    assert "irrigation" in result.explanation.what_it_does_not_establish
    assert any("longer than the 92-day window" in item for item in result.findings)


def test_stage_specific_sorghum_temperatures_are_not_compared(scenarios, kb, gate, config):
    sorghum = RotationStrategy(
        strategy_id="sorghum-only", name="Sorghum", crop_sequence=("sorghum",), role=RotationRole.ALTERNATIVE,
        evidence=StrategyEvidence.HYPOTHETICAL, description="Test input.",
    )
    assessment = assess_strategy(sorghum, scenarios=scenarios, soil=resolve(None, config, gate), kb=kb, gate=gate, config=config)
    for result in assessment.indicator("temperature_vs_documented_range"):
        assert result.status is IndicatorStatus.UNAVAILABLE
        assert any("stage" in item for item in result.missing)


def test_qualified_bean_temperature_is_not_used_as_an_upper_limit(scenarios, kb, gate, config):
    bean = RotationStrategy(
        strategy_id="bean-only", name="Bean", crop_sequence=("common-bean",), role=RotationRole.ALTERNATIVE,
        evidence=StrategyEvidence.HYPOTHETICAL, description="Test input.",
    )
    assessment = assess_strategy(bean, scenarios=scenarios, soil=resolve(None, config, gate), kb=kb, gate=gate, config=config)
    used = {item.requirement_id for item in assessment.indicator("temperature_vs_documented_range")}
    assert "common-bean-temperature-upper" not in used
    assert {"common-bean-temperature-suitable", "common-bean-temperature-lower"} <= used


def test_frost_days_count_the_nasa_minimum_temperatures(report, scenarios):
    (result,) = indicators(report, "continuous-maize", "frost_days", window_id="long-rains")
    assert all(item.value == scenarios.season(item.season_id).frost_days for item in result.season_findings)
    assert result.status is IndicatorStatus.SUPPORTED


def test_soil_indicators_are_unavailable_without_soil_and_say_how_to_get_it(report):
    for indicator_id in ("soil_ph_vs_documented_range", "root_zone_available_water", "readily_available_water"):
        for result in report.strategy("continuous-maize").indicator(indicator_id):
            assert result.status is IndicatorStatus.UNAVAILABLE
            assert any("soil" in item.lower() for item in result.missing)


def test_soil_indicators_with_a_hypothetical_profile_stay_labelled(soil_report):
    assert soil_report.uses_hypothetical_inputs and soil_report.soil.hypothetical
    assert "hypothetical" in soil_report.limitations[0]
    for indicator_id in ("soil_ph_vs_documented_range", "root_zone_available_water"):
        (result,) = indicators(soil_report, "continuous-maize", indicator_id, crop_id="maize")
        assert InformationLayer.HYPOTHETICAL_ASSUMPTION in result.information_layers
        assert "hypothetical" in result.headline.lower()


def test_soil_ph_comparison_with_a_reported_value(scenarios, kb, gate, config):
    soil = SoilProfileInput(soil_ph=SoilValueInput(value=5.2, source_class=SoilSourceClass.LAB_MEASURED))
    result = compare_strategies((MAIZE_PIGEON_PEA,), scenarios=scenarios, kb=kb, gate=gate, config=config, soil=soil)
    (maize,) = result.strategy("maize-pigeon-pea").indicator("soil_ph_vs_documented_range", crop_id="maize")
    assert maize.status is IndicatorStatus.CONDITIONAL and "inside the tolerated range" in maize.headline
    assert InformationLayer.USER_SOIL_INPUT in maize.information_layers
    assert UncertaintyCategory.SOIL_INPUT_UNVERIFIED in maize.uncertainty.categories


def test_sequence_indicators(report):
    (diversity,) = indicators(report, "continuous-maize", "crop_family_diversity")
    assert [value.value for value in diversity.values] == [1.0, 1.0]
    (repetition,) = indicators(report, "continuous-maize", "crop_repetition")
    assert repetition.values[0].value == 1.0
    (repetition,) = indicators(report, "maize-cowpea", "crop_repetition")
    assert repetition.values[0].value == 0.0 and repetition.values[1].value == 0.0
    (legume,) = indicators(report, "maize-cowpea", "legume_in_sequence")
    assert legume.values[0].value == 1.0 and legume.uncertainty.confidence is ConfidenceLevel.HIGH


def test_conditional_indicators_display_their_conditions(report, soil_report):
    for item in (report, soil_report):
        for strategy in item.strategies:
            for result in strategy.indicators:
                if result.status is IndicatorStatus.CONDITIONAL:
                    assert result.conditions


def test_every_numeric_input_passed_the_gate_and_was_rechecked(report, gate):
    rows = {row.claim_id: row for row in gate.matrix()}
    for strategy in report.strategies:
        for result in strategy.indicators:
            for evidence in result.evidence:
                if evidence.use.value == "numeric_input":
                    assert rows[evidence.claim_id].rechecked_in_a4
                    assert evidence.status.value in ("verified_direct", "verified_conditional")


def test_injected_unverified_value_cannot_reach_a_result(scenarios, kb, gate, config):
    cowpea = kb.get_crop("cowpea")
    invented = CropRequirement(
        requirement_id="cowpea-water-need-invented", variable="crop_seasonal_water_requirement", minimum=300, maximum=400,
        unit=Unit.MILLIMETRE, basis=RequirementBasis.TYPICAL, statement="Invented for a test.", limitation="Invented.",
        provenance=ProvenanceRecord(
            kind="literature_value", source_id="fao-tm3", source_name="Test", citation="Test citation (fixture)",
            locator="Nowhere", confidence=EvidenceConfidence.DIRECTLY_SUPPORTED,
        ),
    )
    patched_crops = tuple(
        crop.model_copy(update={"requirements": (*crop.requirements, invented)}) if crop.crop_id == "cowpea" else crop
        for crop in kb.crops
    )
    patched = kb.model_copy(update={"crops": patched_crops})
    patched_gate = EvidenceGate(patched, gate.audit)
    result = compare_strategies((MAIZE_COWPEA,), scenarios=scenarios, kb=patched, gate=patched_gate, config=config)
    for item in result.strategy("maize-cowpea").indicator("rainfall_vs_crop_water_use", crop_id="cowpea"):
        assert item.status is IndicatorStatus.UNAVAILABLE
        assert any("re-checked" in reason for reason in item.missing)
    assert cowpea.requirements_for("crop_seasonal_water_requirement") == ()


# --- Constraints --------------------------------------------------------------------


def test_unsupported_same_family_rule_is_never_applied(report):
    for strategy in report.strategies:
        found = [item for item in strategy.constraints if item.constraint_id == "same-family-in-succession"]
        assert found and all(item.outcome is ConstraintOutcome.NOT_APPLIED for item in found)


def test_frost_constraint_is_evaluated_from_the_record(report):
    found = [item for item in report.strategy("continuous-maize").constraints if item.constraint_id == "frost-kills-maize"]
    assert {item.window_id for item in found} == {"long-rains", "short-rains"}
    assert all(item.outcome is ConstraintOutcome.NOT_TRIGGERED for item in found)


def test_frost_constraint_triggers_when_frost_is_present(scenarios, kb, gate, config):
    window = scenarios.window("long-rains")
    frosty = window.model_copy(
        update={"seasons": tuple(item.model_copy(update={"frost_days": 2}) if item.season_year == 2010 else item for item in window.seasons)}
    )
    maize = kb.get_crop("maize")
    findings = evaluate_constraints(CONTINUOUS_MAIZE, [maize], [frosty], resolve(None, config, gate), kb=kb, gate=gate)
    (frost,) = [item for item in findings if item.constraint_id == "frost-kills-maize"]
    assert frost.outcome is ConstraintOutcome.TRIGGERED and "1 of 25" in frost.finding


def test_constraints_needing_missing_information_are_not_evaluated(report):
    outcomes = {
        item.constraint_id: item.outcome
        for item in report.strategy("continuous-maize").constraints
        if item.constraint_id in ("drought-at-flowering-maize", "soil-ph-outside-documented-range", "waterlogging-sensitive-crop-on-wet-soil")
    }
    assert set(outcomes.values()) == {ConstraintOutcome.NOT_EVALUATED}


def test_sequence_constraints(report):
    def outcome(strategy_id, constraint_id):
        return next(item.outcome for item in report.strategy(strategy_id).constraints if item.constraint_id == constraint_id)

    assert outcome("continuous-maize", "continuous-cereal-without-legume") is ConstraintOutcome.TRIGGERED
    assert outcome("maize-cowpea", "continuous-cereal-without-legume") is ConstraintOutcome.NOT_TRIGGERED
    assert outcome("continuous-maize", "same-crop-in-succession") is ConstraintOutcome.TRIGGERED
    assert outcome("maize-pigeon-pea", "perennial-in-seasonal-rotation") is ConstraintOutcome.TRIGGERED
    assert outcome("maize-cowpea", "legume-needs-pest-management") is ConstraintOutcome.TRIGGERED


# --- No score, no fabricated outcomes ---------------------------------------------------


def test_no_overall_score_or_ranking(report):
    assert report.overall_score is None
    for name in ComparisonReport.model_fields:
        assert "rank" not in name and ("score" not in name or name == "overall_score")
    # The list of outcomes the tool refuses to estimate names "resilience score"
    # on purpose; everything else must not.
    text = report.model_dump_json(exclude={"unsupported_outcomes"}).lower()
    for word in ("best rotation", "recommended rotation", "we recommend", "resilience score"):
        assert word not in text


def test_no_yield_profit_or_other_unsupported_outcome_is_calculated(report):
    for strategy in report.strategies:
        for result in strategy.indicators:
            for value in result.values:
                label = value.label.lower()
                for word in ("yield", "profit", "nitrogen fixed", "carbon", "irrigation", "disease"):
                    assert word not in label
    outcomes = {item.outcome for item in report.unsupported_outcomes}
    assert {"Crop yield", "Profit or economic return", "Irrigation requirement"} <= outcomes
    assert report.unsupported_outcomes == UNSUPPORTED_OUTCOMES


def test_reported_study_outcomes_are_background_only(report):
    notes = [item for item in report.strategy("maize-cowpea").background if item.topic == "documented_study_outcome"]
    assert notes and notes[0].evidence.use.value == "background"
    assert notes[0].evidence.status.value == "abstract_only"


def test_tradeoffs_are_side_by_side_without_a_winner(report):
    aspects = [item.aspect for item in report.tradeoffs]
    assert "Water-use evidence" in aspects and "Plant-family diversity" in aspects
    water = next(item for item in report.tradeoffs if item.aspect == "Water-use evidence")
    assert "pigeon pea" in water.statement and "incomplete, not favourable" in water.statement


# --- Farmer priorities -------------------------------------------------------------------


def test_priorities_follow_the_farmers_order_and_highlight_their_indicators(soil_report):
    view = soil_report.priorities
    assert [item.dimension for item in view.sections] == [
        PriorityDimension.WATER_USE, PriorityDimension.MARKET_SUITABILITY, PriorityDimension.CROP_DIVERSITY
    ]
    assert view.indicator_order[0] == "rainfall_vs_crop_water_use"
    assert set(view.indicator_order) == {item.indicator_id for item in INDICATORS}
    water = view.sections[0]
    assert water.indicator_ids == PRIORITY_INDICATORS[PriorityDimension.WATER_USE]
    pigeon = next(item for item in water.strategy_notes if item.strategy_id == "maize-pigeon-pea")
    assert pigeon.missing and pigeon.highlights


def test_unsupported_priority_reports_missing_evidence(soil_report):
    economic = soil_report.priorities.sections[1]
    assert economic.indicator_ids == ()
    assert "Nothing is estimated" in economic.unsupported_note and "prices" in economic.unsupported_note


@pytest.mark.parametrize(
    "dimension",
    [PriorityDimension.EROSION_REDUCTION, PriorityDimension.FORAGE_VALUE, PriorityDimension.OPERATIONAL_SIMPLICITY],
)
def test_priorities_without_evidence_are_flagged(scenarios, kb, gate, config, dimension):
    result = compare_strategies(
        (CONTINUOUS_MAIZE,), scenarios=scenarios, kb=kb, gate=gate, config=config,
        priorities=PrioritySelection(dimensions=(dimension,)),
    )
    assert result.priorities.sections[0].unsupported_note


def test_priorities_use_no_weights():
    assert "weight" not in PrioritySelection.model_fields
    with pytest.raises(ValidationError, match="must not repeat"):
        PrioritySelection(dimensions=(PriorityDimension.WATER_USE, PriorityDimension.WATER_USE))


def test_priorities_change_presentation_not_results(report, soil_report, scenarios, kb, gate, config):
    plain = compare_strategies(scenarios=scenarios, kb=kb, gate=gate, config=config, generated_at=STAMP)
    ordered = compare_strategies(
        scenarios=scenarios, kb=kb, gate=gate, config=config, generated_at=STAMP,
        priorities=PrioritySelection(dimensions=(PriorityDimension.CROP_DIVERSITY,)),
    )
    assert [item.model_dump() for item in plain.strategies] == [item.model_dump() for item in ordered.strategies]


# --- Uncertainty and explanations --------------------------------------------------------


def test_confidence_rules():
    assert assess(base=ConfidenceLevel.HIGH, categories=(), limitations=("x",)).confidence is ConfidenceLevel.HIGH
    nasa = assess(base=ConfidenceLevel.HIGH, categories=(UncertaintyCategory.LOCATION_APPROXIMATION,), limitations=("x",))
    assert nasa.confidence is ConfidenceLevel.MODERATE
    context = assess(base=ConfidenceLevel.MODERATE, categories=(UncertaintyCategory.CONTEXT_DEPENDENT_EVIDENCE,), limitations=("x",))
    assert context.confidence is ConfidenceLevel.LOW and "conditions" in context.confidence_basis
    missing = assess(base=ConfidenceLevel.HIGH, categories=(), limitations=("x",), available=False)
    assert missing.confidence is ConfidenceLevel.NOT_ASSESSED
    assert UncertaintyCategory.UNSUPPORTED_INDICATOR in missing.categories


def test_every_indicator_explains_itself(report, soil_report):
    for item in (report, soil_report):
        for strategy in item.strategies:
            for result in strategy.indicators:
                explanation = result.explanation
                for part in (
                    explanation.what_was_calculated, explanation.data_and_evidence_used, explanation.assumptions,
                    explanation.what_it_means, explanation.what_it_does_not_establish, explanation.how_to_improve_confidence,
                ):
                    assert part.strip()
                assert result.uncertainty.confidence_basis and result.uncertainty.limitations


def test_information_layers_keep_sources_apart(report):
    for strategy in report.strategies:
        for result in strategy.indicators:
            layers = set(result.information_layers)
            if result.status is IndicatorStatus.UNAVAILABLE:
                assert layers == {InformationLayer.UNAVAILABLE}
            elif result.indicator_id in ("rainfall_vs_crop_water_use", "frost_days", "temperature_vs_documented_range"):
                assert InformationLayer.NASA_OBSERVATION in layers
            if result.indicator_id == "rainfall_vs_crop_water_use" and result.status is not IndicatorStatus.UNAVAILABLE:
                assert InformationLayer.LITERATURE_VALUE in layers


def test_nasa_based_indicators_carry_the_location_and_model_caveats(report):
    (result,) = indicators(report, "continuous-maize", "frost_days", window_id="short-rains")
    assert {UncertaintyCategory.LOCATION_APPROXIMATION, UncertaintyCategory.MODEL_LIMITATION} <= set(result.uncertainty.categories)


@pytest.mark.parametrize(
    "fields, message",
    [
        (dict(status=IndicatorStatus.UNAVAILABLE, values=({"label": "x", "value": 1.0},)), "cannot carry values"),
        (dict(status=IndicatorStatus.CONDITIONAL, conditions=()), "display its conditions"),
    ],
)
def test_indicator_contract_rules(report, fields, message):
    (template,) = indicators(report, "continuous-maize", "rainfall_vs_crop_water_use", crop_id="maize", window_id="long-rains")
    data = template.model_dump()
    data.update(fields)
    if data["status"] == IndicatorStatus.UNAVAILABLE:
        data["missing"] = ("x",)
    with pytest.raises(ValidationError, match=message):
        IndicatorResult.model_validate(data)


def test_conditional_evidence_cannot_be_presented_as_supported(report):
    (template,) = indicators(report, "continuous-maize", "rainfall_vs_crop_water_use", crop_id="maize", window_id="long-rains")
    data = template.model_dump()
    data["status"] = IndicatorStatus.SUPPORTED
    with pytest.raises(ValidationError, match="marked conditional"):
        IndicatorResult.model_validate(data)


def test_abstract_only_evidence_cannot_be_a_numeric_input():
    with pytest.raises(ValidationError, match="only verified evidence"):
        EvidenceUsed(claim_id="x", source_id="franke-2018", citation="c", locator=None, status="abstract_only", use="numeric_input")


# --- Integration, provenance, determinism, offline ----------------------------------------


def test_report_preserves_provenance(report, pilot_dataset, kb, gate):
    assert report.dataset_id == pilot_dataset.dataset_id
    assert report.payload_sha256 == pilot_dataset.provenance.payload_sha256
    assert report.dataset_citations == pilot_dataset.provenance.citations
    assert report.knowledge_base_version == kb.manifest.knowledge_base_version
    assert report.audit_version == gate.audit.audit_version
    assert report.observation_period == ("2001-01-01", "2025-12-31")
    registered = {item.source_id for item in kb.sources}
    for strategy in report.strategies:
        for result in strategy.indicators:
            assert all(item.source_id in registered for item in result.evidence)


def test_report_records_the_provisional_pilot(report):
    assert report.pilot_status.value == "provisional"
    assert "not approved" in report.approval_note and report.approval_note in report.limitations


def test_comparison_is_deterministic(report, scenarios, kb, gate, config):
    again = compare_strategies(scenarios=scenarios, kb=kb, gate=gate, config=config, generated_at=STAMP)
    assert again.model_dump() == report.model_dump()


def test_evidence_completeness_counts_add_up(report):
    for strategy in report.strategies:
        counts = strategy.completeness
        assert counts.total == len(strategy.indicators)
        assert counts.unavailable == len(counts.unavailable_reasons)
    assert report.strategy("maize-pigeon-pea").completeness.unavailable > report.strategy("continuous-maize").completeness.unavailable


def test_export_to_the_a1_comparison_contract(report):
    result = report.to_comparison_result()
    assert result.follows_challenge_guidance and result.is_complete
    assert result.current_practice_rotation_id == "continuous-maize"
    assert len(result.scenario_ids) == 6 and len(result.results) == 18
    for item in result.results:
        assert all(value.provenance.kind.value == "derived" for value in item.indicators)


def test_location_mismatch_is_refused(scenarios, kb, gate):
    from src.pilot_sites import KATUMANI

    elsewhere = KATUMANI.model_copy(update={"location": KATUMANI.location.model_copy(update={"latitude": 0.5})})
    with pytest.raises(ValueError, match="different location"):
        compare_strategies(scenarios=scenarios, kb=kb, gate=gate, config=pilot_configuration(elsewhere))


def test_pilot_comparison_runs_offline(tmp_path, make_settings):
    settings = make_settings(offline_demo_mode=True, nasa_cache_directory=tmp_path / "cache")
    result = run_pilot_comparison(settings=settings)
    assert len(result.strategies) == 3 and result.overall_score is None
