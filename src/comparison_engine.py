"""Crop-rotation comparison engine and farmer priorities (phases A4.5 and A4.6).

Responsibility
    Set candidate crop sequences side by side against the historical seasons of
    the NASA record, the user's soil information and the cited crop evidence,
    and present the result through the farmer's priorities. Every indicator
    states what it used, what it assumed, what it means and what it does not
    establish. The output is complete without any AI service.

What it will not do
    * It produces **no overall score and no ranking**. Indicators measure
      unlike things, and no defensible method exists here to weigh them, so the
      strategies are shown side by side with their tradeoffs.
    * It does not predict yield, profit, nitrogen fixed, soil carbon change,
      irrigation demand or pest and disease incidence. ``UNSUPPORTED_OUTCOMES``
      says why for each.
    * No literature value is used unless the evidence gate admits it. A value
      the gate refuses makes its indicator unavailable; nothing is substituted.

Indicators
    ===================================  ==========  ==========================================
    Indicator                            Scope       What it compares
    ===================================  ==========  ==========================================
    rainfall_vs_crop_water_use           seasonal    season rainfall vs indicative crop water use
    temperature_vs_documented_range      seasonal    daily mean temperature vs a documented range
    frost_days                           seasonal    days with minimum below 0 °C (ETCCDI FD)
    growing_period_vs_window             window      documented growing period vs window length
    annual_rainfall_vs_documented_range  annual      calendar-year rainfall vs a documented range
    soil_ph_vs_documented_range          soil        user soil pH vs documented pH ranges
    root_zone_available_water            soil        FAO-56 Eq. 82 from rooting depth and soil water
    readily_available_water              soil        FAO-56 Eq. 83 from the depletion fraction
    crop_family_diversity                sequence    distinct crops and botanical families
    legume_in_sequence                   sequence    whether a nitrogen-fixing crop is included
    crop_repetition                      sequence    the same crop or family in successive slots
    ===================================  ==========  ==========================================

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from src.crop_knowledge import KnowledgeBase, RotationConstraint
from src.evidence_audit import AuditStatus, EvidenceGate, EvidenceUse, GateDecision
from src.models import (
    DEFAULT_DISCLAIMER,
    ComparisonResult,
    ConfidenceLevel,
    Contract,
    CropProfile,
    DataKind,
    GeoLocation,
    PriorityDimension,
    ProvenanceRecord,
    RotationAssessment,
    ScenarioCategory,
    ScenarioResult,
    ScientificValue,
    Slug,
    SoilDrainageClass,
    Text,
    UncertaintyCategory,
    UncertaintyStatement,
    Unit,
    VariableDefinition,
    VariableDomain,
    _now,
    _require_unique,
    get_variable,
    register_variable,
)
from src.scenario_engine import ScenarioSet, SeasonClimate, WindowScenarios
from src.season_config import (
    CANDIDATE_STRATEGIES,
    PilotConfiguration,
    PilotStatus,
    RotationStrategy,
    SeasonAssignment,
    StrategyEvidence,
    validate_strategy,
)
from src.soil_inputs import ResolvedSoil, SoilProfileInput, compare_ph, resolve_soil, root_zone_water
from src.uncertainty import (
    UNSUPPORTED_OUTCOMES,
    IndicatorExplanation,
    InformationLayer,
    TradeoffNote,
    UnsupportedOutcome,
    assess,
)

ENGINE_VERSION = "0.4.0"
ENGINE_SOURCE_ID = "cropshift-comparison-engine"

_NASA = (UncertaintyCategory.LOCATION_APPROXIMATION, UncertaintyCategory.MODEL_LIMITATION)


class ComparisonError(ValueError):
    """The comparison cannot be made with the inputs given."""


# --------------------------------------------------------------------------- #
# Indicator catalogue
# --------------------------------------------------------------------------- #


class IndicatorScope(StrEnum):
    SEASONAL = "seasonal"  # one value per past season of a window
    WINDOW = "window"  # one value per season window
    ANNUAL = "annual"  # one value per calendar year
    SOIL = "soil"  # static, from soil information
    SEQUENCE = "sequence"  # from the crop sequence alone


class IndicatorStatus(StrEnum):
    SUPPORTED = "supported"  # verified evidence and data; shown without conditions
    CONDITIONAL = "conditional"  # shown, with conditions that must be read beside it
    UNAVAILABLE = "unavailable"  # cannot be calculated; the reason is given


class IndicatorDefinition(Contract):
    indicator_id: Slug
    name: Text
    scope: IndicatorScope
    unit: Unit | None
    description: Text
    method: Text
    mapping_id: Slug | None = None
    priorities: tuple[PriorityDimension, ...] = ()


INDICATORS: tuple[IndicatorDefinition, ...] = (
    IndicatorDefinition(
        indicator_id="rainfall_vs_crop_water_use", name="Season rainfall against indicative crop water use",
        scope=IndicatorScope.SEASONAL, unit=Unit.MILLIMETRE,
        description="How each past season's rainfall compared with the crop's indicative seasonal water use.",
        method="For every classified season: below, within or above the documented water-use range (FAO TM3).",
        mapping_id="seasonal-water-need-to-seasonal-rainfall",
        priorities=(PriorityDimension.WATER_USE, PriorityDimension.CLIMATE_RESILIENCE),
    ),
    IndicatorDefinition(
        indicator_id="temperature_vs_documented_range", name="Daily temperature against a documented range",
        scope=IndicatorScope.SEASONAL, unit=Unit.PERCENT,
        description="Share of days in each past season whose daily mean temperature was inside a documented range.",
        method="For every classified season: days with NASA daily mean temperature inside the range, as a percentage.",
        mapping_id="temperature-requirement-to-air-temperature",
        priorities=(PriorityDimension.CLIMATE_RESILIENCE,),
    ),
    IndicatorDefinition(
        indicator_id="frost_days", name="Frost days in the season",
        scope=IndicatorScope.SEASONAL, unit=Unit.COUNT,
        description="Days whose NASA daily minimum air temperature was below 0 °C (ETCCDI index FD).",
        method="Count per classified season.",
        priorities=(PriorityDimension.CLIMATE_RESILIENCE,),
    ),
    IndicatorDefinition(
        indicator_id="growing_period_vs_window", name="Growing period against the season window",
        scope=IndicatorScope.WINDOW, unit=Unit.DAY,
        description="Whether the crop's documented growing period fits within the rainy-season window.",
        method="Documented total growing period (FAO TM3) minus the window length.",
        mapping_id="growing-period-to-season-length",
        priorities=(PriorityDimension.WATER_USE, PriorityDimension.CLIMATE_RESILIENCE),
    ),
    IndicatorDefinition(
        indicator_id="annual_rainfall_vs_documented_range", name="Annual rainfall against a documented range",
        scope=IndicatorScope.ANNUAL, unit=Unit.COUNT,
        description="In how many complete calendar years the NASA annual rainfall fell inside a documented range.",
        method="Count of years below, inside and above each documented annual-rainfall range.",
        mapping_id="annual-rainfall-requirement-to-precipitation",
        priorities=(PriorityDimension.CLIMATE_RESILIENCE, PriorityDimension.WATER_USE),
    ),
    IndicatorDefinition(
        indicator_id="soil_ph_vs_documented_range", name="Soil pH against documented ranges",
        scope=IndicatorScope.SOIL, unit=Unit.PH,
        description="Whether the field's soil pH lies inside each documented pH range of the crop.",
        method="Inside, below or above each admitted range.",
        mapping_id="soil-ph-requirement-to-soil-ph",
    ),
    IndicatorDefinition(
        indicator_id="root_zone_available_water", name="Water held in the root zone",
        scope=IndicatorScope.SOIL, unit=Unit.MILLIMETRE,
        description="Total available soil water within the crop's rooting depth (FAO-56 Equation 82).",
        method="TAW = 1000 (θFC − θWP) Zr, as a range from the ranges of its inputs.",
        mapping_id="rooting-depth-to-soil-water",
        priorities=(PriorityDimension.WATER_USE, PriorityDimension.CLIMATE_RESILIENCE),
    ),
    IndicatorDefinition(
        indicator_id="readily_available_water", name="Water the crop can use before stress",
        scope=IndicatorScope.SOIL, unit=Unit.MILLIMETRE,
        description="Readily available water in the root zone (FAO-56 Equation 83).",
        method="RAW = p TAW, with the depletion fraction p from FAO-56 Table 22.",
        mapping_id="depletion-fraction-to-soil-water",
        priorities=(PriorityDimension.WATER_USE, PriorityDimension.CLIMATE_RESILIENCE),
    ),
    IndicatorDefinition(
        indicator_id="crop_family_diversity", name="Crops and plant families in the sequence",
        scope=IndicatorScope.SEQUENCE, unit=Unit.COUNT,
        description="How many different crops and botanical families the sequence contains.",
        method="Count of distinct crops and of distinct families.",
        priorities=(PriorityDimension.CROP_DIVERSITY, PriorityDimension.PEST_CYCLE_DISRUPTION),
    ),
    IndicatorDefinition(
        indicator_id="legume_in_sequence", name="Legume in the sequence",
        scope=IndicatorScope.SEQUENCE, unit=Unit.COUNT,
        description="Whether the sequence includes a nitrogen-fixing legume.",
        method="Count of nitrogen-fixing crops, from cited crop statements.",
        priorities=(PriorityDimension.NITROGEN_FIXATION, PriorityDimension.ORGANIC_MATTER, PriorityDimension.CROP_DIVERSITY),
    ),
    IndicatorDefinition(
        indicator_id="crop_repetition", name="Same crop or family in succession",
        scope=IndicatorScope.SEQUENCE, unit=Unit.COUNT,
        description="How many successive slots repeat the same crop, or the same family, as the cycle repeats.",
        method="Count over the repeating cycle, including the step from the last slot back to the first.",
        priorities=(PriorityDimension.PEST_CYCLE_DISRUPTION, PriorityDimension.CROP_DIVERSITY),
    ),
)

_DEFINITIONS = {item.indicator_id: item for item in INDICATORS}

PRIORITY_INDICATORS: dict[PriorityDimension, tuple[str, ...]] = {
    dimension: tuple(item.indicator_id for item in INDICATORS if dimension in item.priorities)
    for dimension in PriorityDimension
}
"""Which indicators inform each priority. Derived from the catalogue above; no weights."""


# Indicator variables for the A1 result contracts (``ScenarioResult``).
for _definition in (
    VariableDefinition(
        name="indicator_season_rainfall_total", domain=VariableDomain.INDICATOR, unit=Unit.MILLIMETRE,
        description="NASA rainfall total over a season window (descriptive)", valid_min=0, valid_max=30000,
    ),
    VariableDefinition(
        name="indicator_frost_days", domain=VariableDomain.INDICATOR, unit=Unit.COUNT,
        description="Days with daily minimum air temperature below 0 °C in a season window", valid_min=0, valid_max=400,
    ),
    VariableDefinition(
        name="indicator_family_count", domain=VariableDomain.INDICATOR, unit=Unit.COUNT,
        description="Distinct botanical families in a crop sequence", valid_min=0, valid_max=50,
    ),
):
    try:
        get_variable(_definition.name)
    except ValueError:
        register_variable(_definition)


# --------------------------------------------------------------------------- #
# Result contracts
# --------------------------------------------------------------------------- #


class EvidenceUsed(Contract):
    """One cited claim an indicator rests on, with the gate's decision."""

    claim_id: Text
    source_id: Slug
    citation: Text
    locator: Text | None
    status: AuditStatus
    use: EvidenceUse
    conditions: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check_evidence(self) -> "EvidenceUsed":
        if self.use is EvidenceUse.NUMERIC_INPUT and self.status not in (
            AuditStatus.VERIFIED_DIRECT, AuditStatus.VERIFIED_CONDITIONAL
        ):
            raise ValueError("only verified evidence may be a numeric input")
        if self.status in (AuditStatus.UNVERIFIED, AuditStatus.CONTRADICTED):
            raise ValueError("unverified or contradicted evidence cannot be used")
        return self


class IndicatorValue(Contract):
    label: Text
    value: float | None
    unit: Unit | None = None
    note: Text | None = None


class SeasonFinding(Contract):
    """The indicator for one past season (or one calendar year)."""

    season_id: Text
    year: int
    category: ScenarioCategory | None
    value: float | None
    position: Text | None = Field(default=None, description="'below', 'within' or 'above' a range, if any.")


class CategorySummary(Contract):
    """The indicator across all seasons of one category: dry, typical or wet."""

    category: ScenarioCategory
    seasons: int = Field(ge=0)
    positions: dict[str, int] = {}
    median_value: float | None = None
    lowest_value: float | None = None
    highest_value: float | None = None


class IndicatorResult(Contract):
    indicator_id: Slug
    name: Text
    scope: IndicatorScope
    status: IndicatorStatus
    strategy_id: Slug
    crop_id: Slug | None = None
    window_id: Slug | None = None
    requirement_id: Slug | None = None
    headline: Text
    values: tuple[IndicatorValue, ...] = ()
    category_summaries: tuple[CategorySummary, ...] = ()
    season_findings: tuple[SeasonFinding, ...] = ()
    findings: tuple[Text, ...] = ()
    evidence: tuple[EvidenceUsed, ...] = ()
    conditions: tuple[Text, ...] = ()
    information_layers: tuple[InformationLayer, ...] = Field(min_length=1)
    missing: tuple[Text, ...] = ()
    uncertainty: UncertaintyStatement
    explanation: IndicatorExplanation

    @model_validator(mode="after")
    def _check_result(self) -> "IndicatorResult":
        if self.indicator_id not in _DEFINITIONS:
            raise ValueError(f"unknown indicator '{self.indicator_id}'")
        if self.status is IndicatorStatus.UNAVAILABLE:
            if self.values or self.season_findings or self.category_summaries:
                raise ValueError("an unavailable indicator cannot carry values")
            if not self.missing:
                raise ValueError("an unavailable indicator must say what is missing")
            if self.uncertainty.confidence is not ConfidenceLevel.NOT_ASSESSED:
                raise ValueError("an unavailable indicator is not assessed")
        else:
            if self.uncertainty.confidence is ConfidenceLevel.NOT_ASSESSED:
                raise ValueError("an available indicator needs an assessed confidence")
        conditional = any(
            item.use is EvidenceUse.NUMERIC_INPUT and item.status is AuditStatus.VERIFIED_CONDITIONAL
            for item in self.evidence
        )
        if conditional and self.status is IndicatorStatus.SUPPORTED:
            raise ValueError("an indicator built on conditional evidence must be marked conditional")
        if self.status is IndicatorStatus.CONDITIONAL and not self.conditions:
            raise ValueError("a conditional indicator must display its conditions")
        return self


class ConstraintOutcome(StrEnum):
    TRIGGERED = "triggered"  # the condition occurred, or applies to this sequence
    NOT_TRIGGERED = "not_triggered"  # evaluated, and the condition did not occur
    NOT_EVALUATED = "not_evaluated"  # the information needed is missing
    NOT_APPLIED = "not_applied"  # the rule is unsupported by evidence, so it is not used


class ConstraintFinding(Contract):
    constraint_id: Slug
    severity: Text
    crop_id: Slug | None = None
    window_id: Slug | None = None
    outcome: ConstraintOutcome
    finding: Text
    user_explanation: Text
    evidence: tuple[EvidenceUsed, ...] = ()
    limitations: tuple[Text, ...] = ()


class BackgroundNote(Contract):
    """Cited context that explains a result but never calculates one."""

    topic: Text
    statement: Text
    evidence: EvidenceUsed


class CropInSequence(Contract):
    position: int = Field(ge=1)
    crop_id: Slug
    common_name: Text
    botanical_family: Text
    nitrogen_fixing: bool
    life_cycle: Text | None
    growing_period_days: tuple[float, float] | None = None
    seasons_evaluated: tuple[Slug, ...]


class StrategyProfile(Contract):
    """Everything about a strategy that does not depend on the weather."""

    strategy_id: Slug
    name: Text
    evidence: StrategyEvidence
    documented_system_id: Slug | None
    documented_in: Text | None
    crops: tuple[CropInSequence, ...]
    distinct_crops: int
    families: tuple[Text, ...]
    slots_per_cycle: int
    seasons_per_cycle: int | None
    season_assignment: SeasonAssignment
    required_soil_information: tuple[Text, ...]
    applicable_constraints: tuple[Slug, ...]
    assumptions: tuple[Text, ...]
    limitations: tuple[Text, ...]


class EvidenceCompleteness(Contract):
    supported: int = Field(ge=0)
    conditional: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    unavailable_reasons: tuple[Text, ...] = ()

    @property
    def total(self) -> int:
        return self.supported + self.conditional + self.unavailable


class StrategyAssessment(Contract):
    strategy: RotationStrategy
    profile: StrategyProfile
    indicators: tuple[IndicatorResult, ...]
    constraints: tuple[ConstraintFinding, ...]
    background: tuple[BackgroundNote, ...]
    completeness: EvidenceCompleteness
    information_gaps: tuple[Text, ...]
    local_review_risks: tuple[Text, ...]
    uses_hypothetical_inputs: bool

    def indicator(self, indicator_id: str, **match: str | None) -> tuple[IndicatorResult, ...]:
        return tuple(
            item
            for item in self.indicators
            if item.indicator_id == indicator_id and all(getattr(item, key) == value for key, value in match.items())
        )


class PrioritySelection(Contract):
    """The priorities a farmer chose, in the farmer's own order. No weights."""

    dimensions: tuple[PriorityDimension, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_selection(self) -> "PrioritySelection":
        _require_unique([item.value for item in self.dimensions], "priorities")
        return self


class PriorityStrategyNote(Contract):
    strategy_id: Slug
    highlights: tuple[Text, ...] = ()
    missing: tuple[Text, ...] = ()


class PrioritySection(Contract):
    dimension: PriorityDimension
    order: int = Field(ge=1, description="1 is the farmer's first-named priority.")
    label: Text
    why_it_matters: Text
    evidence_available: Text
    indicator_ids: tuple[Slug, ...]
    strategy_notes: tuple[PriorityStrategyNote, ...]
    unsupported_note: Text | None = None
    limitations: tuple[Text, ...] = ()


class PriorityView(Contract):
    selection: PrioritySelection
    sections: tuple[PrioritySection, ...]
    indicator_order: tuple[Slug, ...] = Field(description="Indicators in display order, the first priority's first.")
    weights_used: Literal[False] = False


class ScenarioOverview(Contract):
    window_id: Slug
    name: Text
    window_basis: Text
    seasons_classified: int
    dry_upper_mm: float | None
    wet_lower_mm: float | None
    representative: dict[ScenarioCategory, Slug]
    rainfall_mean_mm: float | None
    rainfall_cv_percent: float | None
    excluded: tuple[Text, ...]


class ComparisonReport(Contract):
    """The full A4 result. A5 displays it; nothing else is needed to explain it."""

    report_id: Slug
    engine_version: Text
    generated_at: datetime
    site_id: Slug
    site_name: Text
    pilot_status: PilotStatus
    approval_note: Text
    location: GeoLocation
    knowledge_base_version: Text
    audit_version: Text
    dataset_id: Text
    payload_sha256: Text
    dataset_citations: tuple[Text, ...]
    observation_period: tuple[str, str]
    scenarios: tuple[ScenarioOverview, ...]
    soil: ResolvedSoil
    strategies: tuple[StrategyAssessment, ...] = Field(min_length=1)
    priorities: PriorityView | None = None
    tradeoffs: tuple[TradeoffNote, ...] = ()
    unsupported_outcomes: tuple[UnsupportedOutcome, ...]
    overall_score: None = Field(default=None, description="Always None: no overall score is computed.")
    limitations: tuple[Text, ...]
    disclaimer: Text = DEFAULT_DISCLAIMER

    @model_validator(mode="after")
    def _check_report(self) -> "ComparisonReport":
        _require_unique([item.strategy.strategy_id for item in self.strategies], "strategies")
        return self

    def strategy(self, strategy_id: str) -> StrategyAssessment:
        for item in self.strategies:
            if item.strategy.strategy_id == strategy_id:
                return item
        raise KeyError(f"no strategy '{strategy_id}' in the report")

    @property
    def uses_hypothetical_inputs(self) -> bool:
        return self.soil.hypothetical or any(item.uses_hypothetical_inputs for item in self.strategies)

    def to_comparison_result(self) -> ComparisonResult:
        """The same comparison in the A1 ``ComparisonResult`` contract."""
        return _to_comparison_result(self)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _used(decision: GateDecision, kb: KnowledgeBase, provenance: ProvenanceRecord) -> EvidenceUsed:
    source = next((item for item in kb.sources if item.source_id == decision.source_id), None)
    return EvidenceUsed(
        claim_id=decision.claim_id,
        source_id=decision.source_id,
        citation=source.citation if source else provenance.source_name,
        locator=provenance.locator,
        status=decision.status,
        use=decision.use,
        conditions=decision.conditions,
    )


def _short_source(kb: KnowledgeBase, source_id: str) -> str:
    """A readable short reference: the source's title and year (never a citation cut at an initial)."""
    source = next((item for item in kb.sources if item.source_id == source_id), None)
    if source is None:
        return source_id
    return f"{source.title} ({source.year})" if source.year else source.title


def _range_text(low: float | None, high: float | None, unit: str) -> str:
    if low is not None and high is not None:
        return f"{low:g} to {high:g} {unit}" if low != high else f"{low:g} {unit}"
    if low is not None:
        return f"at least {low:g} {unit}"
    return f"at most {high:g} {unit}"


def _position(value: float, low: float | None, high: float | None) -> str:
    if low is not None and value < low:
        return "below"
    if high is not None and value > high:
        return "above"
    return "within"


def _summaries(findings: Sequence[SeasonFinding]) -> tuple[CategorySummary, ...]:
    result = []
    for category in ScenarioCategory:
        members = [item for item in findings if item.category is category]
        values = [item.value for item in members if item.value is not None]
        positions: dict[str, int] = {}
        for item in members:
            if item.position:
                positions[item.position] = positions.get(item.position, 0) + 1
        result.append(
            CategorySummary(
                category=category,
                seasons=len(members),
                positions=positions,
                median_value=round(statistics.median(values), 2) if values else None,
                lowest_value=round(min(values), 2) if values else None,
                highest_value=round(max(values), 2) if values else None,
            )
        )
    return tuple(result)


def _window_categories(window: WindowScenarios) -> list[UncertaintyCategory]:
    found = [*_NASA, UncertaintyCategory.SEASON_ASSUMPTION]
    if window.excluded:
        found.append(UncertaintyCategory.INCOMPLETE_OBSERVATION_PERIOD)
    return found


def _unavailable(
    indicator_id: str,
    *,
    strategy_id: str,
    headline: str,
    missing: Sequence[str],
    explanation: IndicatorExplanation,
    crop_id: str | None = None,
    window_id: str | None = None,
    requirement_id: str | None = None,
    categories: Sequence[UncertaintyCategory] = (UncertaintyCategory.DATA_MISSING,),
) -> IndicatorResult:
    definition = _DEFINITIONS[indicator_id]
    return IndicatorResult(
        indicator_id=indicator_id, name=definition.name, scope=definition.scope, status=IndicatorStatus.UNAVAILABLE,
        strategy_id=strategy_id, crop_id=crop_id, window_id=window_id, requirement_id=requirement_id,
        headline=headline, information_layers=(InformationLayer.UNAVAILABLE,), missing=tuple(missing),
        uncertainty=assess(base=ConfidenceLevel.LOW, categories=categories, limitations=missing, available=False),
        explanation=explanation,
    )


def _status(evidence: Sequence[EvidenceUsed]) -> IndicatorStatus:
    if any(item.use is EvidenceUse.NUMERIC_INPUT and item.status is AuditStatus.VERIFIED_CONDITIONAL for item in evidence):
        return IndicatorStatus.CONDITIONAL
    return IndicatorStatus.SUPPORTED


def _evidence_categories(evidence: Sequence[EvidenceUsed]) -> list[UncertaintyCategory]:
    found = []
    if any(item.status is AuditStatus.VERIFIED_CONDITIONAL for item in evidence):
        found.append(UncertaintyCategory.CONTEXT_DEPENDENT_EVIDENCE)
    if any(item.status is AuditStatus.ABSTRACT_ONLY for item in evidence):
        found.append(UncertaintyCategory.ABSTRACT_ONLY_EVIDENCE)
    return found


def _name(crop: CropProfile) -> str:
    return crop.common_name


# --------------------------------------------------------------------------- #
# Seasonal, window and annual indicators
# --------------------------------------------------------------------------- #


def rainfall_vs_water_use(
    crop: CropProfile, window: WindowScenarios, *, strategy_id: str, kb: KnowledgeBase, gate: EvidenceGate
) -> IndicatorResult:
    name, window_name = _name(crop), window.window.name.lower()
    admitted, refused = gate.admitted_requirements(crop, "crop_seasonal_water_requirement")
    explanation_missing = IndicatorExplanation(
        what_was_calculated="Nothing: no usable seasonal water-use value is held for this crop.",
        data_and_evidence_used="The evidence registry was searched; the sources read give no seasonal water need for this crop.",
        assumptions="None.",
        what_it_means="The water demand of this crop cannot be set beside past rainfall in this tool.",
        what_it_does_not_establish="It does not mean the crop needs little or much water. It means the evidence is missing.",
        how_to_improve_confidence="A cited seasonal water-use figure for the crop, or local water-use measurements.",
    )
    if not admitted:
        reasons = [f"No seasonal water-use value for {name.lower()} is held in the sources read."]
        reasons += [f"{item.requirement_id}: {decision.reason}" for item, decision in refused]
        return _unavailable(
            "rainfall_vs_crop_water_use", strategy_id=strategy_id, crop_id=crop.crop_id, window_id=window.window.season_id,
            headline=f"{name}, {window_name}: not available. No verified seasonal water-use value exists for {name.lower()}.",
            missing=reasons, explanation=explanation_missing,
            categories=(UncertaintyCategory.DATA_MISSING, UncertaintyCategory.UNSUPPORTED_INDICATOR),
        )
    requirement, decision = admitted[0]
    low, high = requirement.minimum, requirement.maximum
    findings = [
        SeasonFinding(
            season_id=item.season_id, year=item.season_year, category=item.category,
            value=item.rainfall_total_mm,
            position=_position(item.rainfall_total_mm, low, high),  # type: ignore[arg-type]
        )
        for item in sorted(window.classified(), key=lambda season: season.season_year)
    ]
    below = sum(1 for item in findings if item.position == "below")
    within = sum(1 for item in findings if item.position == "within")
    above = sum(1 for item in findings if item.position == "above")
    extra: list[str] = []
    cycle, _ = gate.admitted_requirements(crop, "crop_cycle_length")
    window_days = window.window.length_days(2001)
    if cycle and cycle[0][0].minimum is not None and cycle[0][0].minimum > window_days:
        extra.append(
            f"The documented growing period of {name.lower()} ({_range_text(cycle[0][0].minimum, cycle[0][0].maximum, 'days')}) "
            f"is longer than the {window_days}-day window, so rain outside the window, and water stored in the soil, "
            "are not counted."
        )
    evidence = (_used(decision, kb, requirement.provenance),)
    range_text = _range_text(low, high, "mm")
    return IndicatorResult(
        indicator_id="rainfall_vs_crop_water_use", name=_DEFINITIONS["rainfall_vs_crop_water_use"].name,
        scope=IndicatorScope.SEASONAL, status=_status(evidence), strategy_id=strategy_id, crop_id=crop.crop_id,
        window_id=window.window.season_id, requirement_id=requirement.requirement_id,
        headline=(
            f"{name}, {window_name}: season rainfall was below the indicative water use of {range_text} in "
            f"{below} of {len(findings)} past seasons, within it in {within} and above it in {above} "
            f"(rain within the {window_days}-day window only; not a water balance)."
        ),
        values=(
            IndicatorValue(label="Indicative seasonal water use, low end", value=low, unit=Unit.MILLIMETRE),
            IndicatorValue(label="Indicative seasonal water use, high end", value=high, unit=Unit.MILLIMETRE),
            IndicatorValue(label="Median season rainfall", value=window.rainfall_median_mm, unit=Unit.MILLIMETRE),
        ),
        category_summaries=_summaries(findings),
        season_findings=tuple(findings),
        findings=tuple(extra),
        evidence=evidence,
        conditions=(
            "The crop figure is water use (evapotranspiration) under the source's conditions, not the rainfall a crop "
            "needs; the two are not directly comparable without a water balance.",
            *decision.conditions,
        ),
        information_layers=(InformationLayer.NASA_OBSERVATION, InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION),
        uncertainty=assess(
            base=ConfidenceLevel.MODERATE,
            categories=(*_window_categories(window), *_evidence_categories(evidence)),
            limitations=(requirement.limitation, *window.window.limitations, *extra),
        ),
        explanation=IndicatorExplanation(
            what_was_calculated=(
                f"For each of the {len(findings)} past {window_name} seasons, the NASA rainfall total over the window "
                f"was set beside the indicative seasonal water use of {name.lower()} ({range_text}) and marked below, "
                "within or above it."
            ),
            data_and_evidence_used=(
                f"NASA POWER daily rainfall (MERRA-2 reanalysis), 2001-2025, summed over each window; the water-use "
                f"range from {_short_source(kb, evidence[0].source_id)}, {requirement.provenance.locator}."
            ),
            assumptions=(
                "The rainy-season window stands in for the growing season; sowing dates are not known. Rainfall is "
                "compared with water use as a first indication only."
            ),
            what_it_means=(
                f"Seasons below the range had less rain within the window than {name.lower()} typically uses over a "
                "season. That points to reliance on stored soil water, rain outside the window, or water stress."
            ),
            what_it_does_not_establish=(
                "It is not a water balance, an irrigation requirement or a yield estimate. Runoff, evaporation, soil "
                "storage and the crop's actual growing dates are not modelled."
            ),
            how_to_improve_confidence=(
                "Local sowing dates and growing periods, a daily soil water balance with reference evapotranspiration "
                "(which needs wind speed), and a local rain gauge."
            ),
        ),
    )


def temperature_vs_range(
    crop: CropProfile, window: WindowScenarios, *, strategy_id: str, kb: KnowledgeBase, gate: EvidenceGate
) -> tuple[IndicatorResult, ...]:
    name, window_name = _name(crop), window.window.name.lower()
    admitted, refused = gate.admitted_requirements(crop, "crop_temperature_requirement")
    if not admitted:
        reasons = [f"{item.requirement_id}: {decision.reason}" for item, decision in refused] or [
            f"No temperature range is held for {name.lower()}."
        ]
        return (
            _unavailable(
                "temperature_vs_documented_range", strategy_id=strategy_id, crop_id=crop.crop_id,
                window_id=window.window.season_id,
                headline=f"{name}, {window_name}: not available. No documented temperature range can be compared with a whole season.",
                missing=reasons,
                explanation=IndicatorExplanation(
                    what_was_calculated="Nothing: the documented temperatures for this crop apply to growth stages whose dates are unknown, or are missing.",
                    data_and_evidence_used="The crop's cited temperature statements, checked by the evidence gate.",
                    assumptions="None.",
                    what_it_means="Whole-season temperatures cannot be judged against this crop's documented needs here.",
                    what_it_does_not_establish="It does not mean the temperatures suit or do not suit the crop.",
                    how_to_improve_confidence="Local sowing dates, so stage-specific values can be compared with the right days.",
                ),
            ),
        )
    results = []
    for requirement, decision in admitted:
        low, high = requirement.minimum, requirement.maximum
        findings = []
        for season in sorted(window.classified(), key=lambda item: item.season_year):
            values = [item for item in season.daily_mean_temperature_c if item is not None]
            inside = sum(1 for item in values if (low is None or item >= low) and (high is None or item <= high))
            share = round(100.0 * inside / len(values), 1) if values else None
            findings.append(
                SeasonFinding(
                    season_id=season.season_id, year=season.season_year, category=season.category, value=share,
                    position=_position(season.mean_temperature_c, low, high) if season.mean_temperature_c is not None else None,
                )
            )
        shares = [item.value for item in findings if item.value is not None]
        median_share = round(statistics.median(shares), 1) if shares else None
        share_text = f"{median_share:g} %" if median_share is not None else "an unknown share"
        means_outside = sum(1 for item in findings if item.position in ("below", "above"))
        evidence = (_used(decision, kb, requirement.provenance),)
        range_text = _range_text(low, high, "°C")
        results.append(
            IndicatorResult(
                indicator_id="temperature_vs_documented_range", name=_DEFINITIONS["temperature_vs_documented_range"].name,
                scope=IndicatorScope.SEASONAL, status=_status(evidence), strategy_id=strategy_id, crop_id=crop.crop_id,
                window_id=window.window.season_id, requirement_id=requirement.requirement_id,
                headline=(
                    f"{name}, {window_name}: on a median {share_text} of days the daily mean temperature was inside "
                    f"the {requirement.basis.value} range of {range_text}; the season mean lay outside it in "
                    f"{means_outside} of {len(findings)} seasons (the source does not say which temperature it "
                    "means, so this is not evidence of unsuitability)."
                ),
                values=(
                    IndicatorValue(label=f"Documented {requirement.basis.value} range, low end", value=low, unit=Unit.DEGREE_CELSIUS),
                    IndicatorValue(label=f"Documented {requirement.basis.value} range, high end", value=high, unit=Unit.DEGREE_CELSIUS),
                    IndicatorValue(label="Median share of days inside the range", value=median_share, unit=Unit.PERCENT),
                ),
                category_summaries=_summaries(findings),
                season_findings=tuple(findings),
                evidence=evidence,
                conditions=(
                    "The source does not say which temperature it means (daily mean, daytime or seasonal); NASA's daily "
                    "mean air temperature is used as the nearest available quantity.",
                    *decision.conditions,
                ),
                information_layers=(InformationLayer.NASA_OBSERVATION, InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION),
                uncertainty=assess(
                    base=ConfidenceLevel.MODERATE,
                    categories=(*_window_categories(window), *_evidence_categories(evidence)),
                    limitations=(requirement.limitation, "A daily mean hides hot afternoons and cold nights."),
                ),
                explanation=IndicatorExplanation(
                    what_was_calculated=(
                        f"For each past {window_name} season, the share of days whose NASA daily mean temperature was "
                        f"inside the {requirement.basis.value} range of {range_text} documented for {name.lower()}."
                    ),
                    data_and_evidence_used=(
                        f"NASA POWER daily mean air temperature at 2 m (MERRA-2), 2001-2025; the range from "
                        f"{_short_source(kb, evidence[0].source_id)}, {requirement.provenance.locator}."
                    ),
                    assumptions="The daily mean temperature is taken as comparable with the documented range; the window stands in for the growing season.",
                    what_it_means=(
                        "A low share means past temperatures in this window were mostly outside the conditions the source "
                        f"describes as {requirement.basis.value} for the crop."
                    ),
                    what_it_does_not_establish=(
                        "It does not establish crop damage, disease or yield. Temperatures at a farm can differ from a grid-cell "
                        "average, and short spells of heat or cold are not shown by a daily mean."
                    ),
                    how_to_improve_confidence=(
                        "Sources that state the temperature measure and growth stage, local sowing dates, and a local weather station."
                    ),
                ),
            )
        )
    return tuple(results)


def frost_days(window: WindowScenarios, *, strategy_id: str, etccdi_citation: str) -> IndicatorResult:
    window_name = window.window.name.lower()
    findings = tuple(
        SeasonFinding(season_id=item.season_id, year=item.season_year, category=item.category, value=float(item.frost_days or 0))
        for item in sorted(window.classified(), key=lambda season: season.season_year)
        if item.frost_days is not None
    )
    with_frost = sum(1 for item in findings if item.value and item.value > 0)
    lowest = min(
        (item.lowest_daily_min_c for item in window.classified() if item.lowest_daily_min_c is not None), default=None
    )
    lowest_text = f"{lowest:g} °C" if lowest is not None else "not available"
    return IndicatorResult(
        indicator_id="frost_days", name=_DEFINITIONS["frost_days"].name, scope=IndicatorScope.SEASONAL,
        status=IndicatorStatus.SUPPORTED, strategy_id=strategy_id, window_id=window.window.season_id,
        headline=(
            f"{window.window.name}: frost days (daily minimum below 0 °C) occurred in {with_frost} of {len(findings)} past "
            f"seasons; the lowest daily minimum recorded was {lowest_text}."
        ),
        values=(
            IndicatorValue(label="Seasons with at least one frost day", value=float(with_frost), unit=Unit.COUNT),
            IndicatorValue(label="Lowest daily minimum in any season", value=lowest, unit=Unit.DEGREE_CELSIUS),
        ),
        category_summaries=_summaries(findings),
        season_findings=findings,
        findings=(f"Frost day definition: ETCCDI index FD ({etccdi_citation.split('.')[0]}).",),
        information_layers=(InformationLayer.NASA_OBSERVATION, InformationLayer.DESCRIPTIVE_CALCULATION),
        uncertainty=assess(
            base=ConfidenceLevel.MODERATE,
            categories=_window_categories(window),
            limitations=(
                "Air temperature at 2 m averaged over a grid cell; frost can form on the ground or in hollows when the "
                "air above stays above 0 °C.",
            ),
        ),
        explanation=IndicatorExplanation(
            what_was_calculated=f"The number of days in each past {window_name} season whose NASA daily minimum air temperature was below 0 °C.",
            data_and_evidence_used="NASA POWER daily minimum air temperature at 2 m (MERRA-2), 2001-2025; the ETCCDI frost-day definition.",
            assumptions="None beyond the window standing in for the growing season.",
            what_it_means="Whether frost, which kills maize and damages other crops according to the sources, appears in the record for this window.",
            what_it_does_not_establish="It does not rule out ground frost on a particular field, and it does not measure crop damage.",
            how_to_improve_confidence="The farmer's own experience of frost, and a local minimum thermometer near the ground.",
        ),
    )


def growing_period_vs_window(
    crop: CropProfile, window: WindowScenarios, *, strategy_id: str, kb: KnowledgeBase, gate: EvidenceGate
) -> IndicatorResult:
    name, window_name = _name(crop), window.window.name.lower()
    admitted, refused = gate.admitted_requirements(crop, "crop_cycle_length")
    window_days = window.window.length_days(2001)
    if not admitted:
        reasons = [f"No growing period in days is held for {name.lower()}."]
        reasons += [f"{item.requirement_id}: {decision.reason}" for item, decision in refused]
        return _unavailable(
            "growing_period_vs_window", strategy_id=strategy_id, crop_id=crop.crop_id, window_id=window.window.season_id,
            headline=f"{name}, {window_name}: not available. The sources read give no growing period in days for {name.lower()}.",
            missing=reasons,
            explanation=IndicatorExplanation(
                what_was_calculated="Nothing: no documented growing period is held for the crop.",
                data_and_evidence_used="The crop's cited statements.",
                assumptions="None.",
                what_it_means="Whether the crop fits within a rainy season cannot be shown.",
                what_it_does_not_establish="It does not mean the crop is short or long.",
                how_to_improve_confidence="A cited growing period for local varieties.",
            ),
        )
    requirement, decision = admitted[0]
    low, high = requirement.minimum, requirement.maximum
    excess_low = (low or 0) - window_days
    excess_high = (high or low or 0) - window_days
    evidence = (_used(decision, kb, requirement.provenance),)
    if excess_low > 0:
        verdict = f"is longer than the {window_days}-day window by {excess_low:g} to {excess_high:g} days"
    elif excess_high > 0:
        verdict = f"may be longer than the {window_days}-day window, by up to {excess_high:g} days"
    else:
        verdict = f"fits within the {window_days}-day window"
    return IndicatorResult(
        indicator_id="growing_period_vs_window", name=_DEFINITIONS["growing_period_vs_window"].name,
        scope=IndicatorScope.WINDOW, status=_status(evidence), strategy_id=strategy_id, crop_id=crop.crop_id,
        window_id=window.window.season_id, requirement_id=requirement.requirement_id,
        headline=f"{name}, {window_name}: the documented growing period ({_range_text(low, high, 'days')}) {verdict}.",
        values=(
            IndicatorValue(label="Documented growing period, shortest", value=low, unit=Unit.DAY),
            IndicatorValue(label="Documented growing period, longest", value=high, unit=Unit.DAY),
            IndicatorValue(label="Window length", value=float(window_days), unit=Unit.DAY),
        ),
        evidence=evidence,
        conditions=decision.conditions or (requirement.limitation,),
        information_layers=(InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION),
        uncertainty=assess(
            base=ConfidenceLevel.MODERATE,
            categories=(UncertaintyCategory.SEASON_ASSUMPTION, *_evidence_categories(evidence)),
            limitations=(requirement.limitation, "A crop can finish on stored soil water after the rains end."),
        ),
        explanation=IndicatorExplanation(
            what_was_calculated=f"The documented total growing period of {name.lower()} minus the length of the {window_name} window.",
            data_and_evidence_used=f"{_short_source(kb, evidence[0].source_id)}, {requirement.provenance.locator}; the FAO GIEWS season window.",
            assumptions="The window is used as the length of the rainy season.",
            what_it_means="A crop longer than the window relies on rain after the window or on stored soil water to finish.",
            what_it_does_not_establish="Real rainy seasons vary in length, and local varieties may be shorter or longer.",
            how_to_improve_confidence="Local variety durations and a cited rule for the start and end of each rainy season.",
        ),
    )


def annual_rainfall_vs_range(
    crop: CropProfile, scenarios: ScenarioSet, *, strategy_id: str, kb: KnowledgeBase, gate: EvidenceGate
) -> tuple[IndicatorResult, ...]:
    name = _name(crop)
    admitted, refused = gate.admitted_requirements(crop, "crop_annual_rainfall_requirement")
    if not admitted:
        reasons = [f"No usable annual rainfall range is held for {name.lower()}."]
        reasons += [f"{item.requirement_id}: {decision.reason}" for item, decision in refused]
        return (
            _unavailable(
                "annual_rainfall_vs_documented_range", strategy_id=strategy_id, crop_id=crop.crop_id,
                headline=f"{name}: not available. No usable annual rainfall range is held.",
                missing=reasons,
                explanation=IndicatorExplanation(
                    what_was_calculated="Nothing: no annual rainfall range can be used for the crop.",
                    data_and_evidence_used="The crop's cited statements, checked by the evidence gate.",
                    assumptions="None.",
                    what_it_means="Annual rainfall cannot be set beside a documented range for this crop.",
                    what_it_does_not_establish="It says nothing about whether the rainfall suits the crop.",
                    how_to_improve_confidence="A clearly stated annual rainfall range from a primary source.",
                ),
            ),
        )
    years = [item for item in scenarios.annual_rainfall if item.complete]
    results = []
    for requirement, decision in admitted:
        low, high = requirement.minimum, requirement.maximum
        findings = tuple(
            SeasonFinding(
                season_id=f"year-{item.year}", year=item.year, category=None, value=item.total_mm,
                position=_position(item.total_mm, low, high),  # type: ignore[arg-type]
            )
            for item in years
        )
        counts = {key: sum(1 for item in findings if item.position == key) for key in ("below", "within", "above")}
        evidence = (_used(decision, kb, requirement.provenance),)
        range_text = _range_text(low, high, "mm a year")
        totals = [item.value for item in findings if item.value is not None]
        results.append(
            IndicatorResult(
                indicator_id="annual_rainfall_vs_documented_range", name=_DEFINITIONS["annual_rainfall_vs_documented_range"].name,
                scope=IndicatorScope.ANNUAL, status=_status(evidence), strategy_id=strategy_id, crop_id=crop.crop_id,
                requirement_id=requirement.requirement_id,
                headline=(
                    f"{name}: annual rainfall was inside the {requirement.basis.value} range of {range_text} in "
                    f"{counts['within']} of {len(findings)} years, below it in {counts['below']} and above it in {counts['above']}."
                ),
                values=(
                    IndicatorValue(label="Years inside the range", value=float(counts["within"]), unit=Unit.COUNT),
                    IndicatorValue(label="Years below the range", value=float(counts["below"]), unit=Unit.COUNT),
                    IndicatorValue(label="Years above the range", value=float(counts["above"]), unit=Unit.COUNT),
                    IndicatorValue(label="Median annual rainfall", value=round(statistics.median(totals), 2) if totals else None, unit=Unit.MILLIMETRE),
                ),
                season_findings=findings,
                evidence=evidence,
                conditions=(
                    "An annual total hides how rain is split between the two rainy seasons.",
                    *decision.conditions,
                ),
                information_layers=(InformationLayer.NASA_OBSERVATION, InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION),
                uncertainty=assess(
                    base=ConfidenceLevel.MODERATE,
                    categories=(*_NASA, *_evidence_categories(evidence)),
                    limitations=(requirement.limitation,),
                ),
                explanation=IndicatorExplanation(
                    what_was_calculated=f"For each complete calendar year, whether NASA annual rainfall was inside {range_text}.",
                    data_and_evidence_used=f"NASA POWER daily rainfall summed by year; {_short_source(kb, evidence[0].source_id)}, {requirement.provenance.locator}.",
                    assumptions="None beyond treating the grid-cell rainfall as representative of the area.",
                    what_it_means=f"How often the site's annual rainfall resembled the rainfall of areas the source associates with {name.lower()}.",
                    what_it_does_not_establish="It says nothing about the timing of rain within the year, or about any one season.",
                    how_to_improve_confidence="A local rain gauge record and sources that give seasonal rather than annual figures.",
                ),
            )
        )
    return tuple(results)


# --------------------------------------------------------------------------- #
# Soil indicators
# --------------------------------------------------------------------------- #


def _soil_categories(soil: ResolvedSoil) -> list[UncertaintyCategory]:
    return [UncertaintyCategory.SOIL_INPUT_UNVERIFIED]


def _soil_layers(soil: ResolvedSoil) -> tuple[InformationLayer, ...]:
    layers = [InformationLayer.USER_SOIL_INPUT, InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION]
    if soil.hypothetical:
        layers.insert(0, InformationLayer.HYPOTHETICAL_ASSUMPTION)
    return tuple(layers)


def soil_ph_indicator(crop: CropProfile, soil: ResolvedSoil, *, strategy_id: str, kb: KnowledgeBase, gate: EvidenceGate) -> IndicatorResult:
    name = _name(crop)
    comparisons, gaps = compare_ph(crop, soil, gate)
    missing_input = soil.missing_for("soil-ph-requirement-to-soil-ph")
    if not comparisons:
        missing = [*(f"{item.explanation} {item.how_to_obtain}" for item in missing_input), *gaps]
        return _unavailable(
            "soil_ph_vs_documented_range", strategy_id=strategy_id, crop_id=crop.crop_id,
            headline=(
                f"{name}: not available. "
                + ("No soil pH was supplied." if missing_input else f"No documented pH range is held for {name.lower()}.")
            ),
            missing=missing or ["No comparison is possible."],
            explanation=IndicatorExplanation(
                what_was_calculated="Nothing: the soil pH, or a documented pH range for the crop, is missing.",
                data_and_evidence_used="The user's soil information and the crop's cited pH ranges.",
                assumptions="None. No default soil pH is used.",
                what_it_means="Soil acidity cannot be compared with the crop's documented needs.",
                what_it_does_not_establish="It does not mean the soil suits or does not suit the crop.",
                how_to_improve_confidence="A soil test that reports pH, and a documented pH range for the crop.",
            ),
        )
    record = soil.get("soil_ph")
    requirements = {item.requirement_id: item for item in crop.requirements}
    evidence = tuple(_used(item.decision, kb, requirements[item.requirement_id].provenance) for item in comparisons)
    summary = "; ".join(f"{item.position} the {item.basis} range of {_range_text(item.minimum, item.maximum, '')}".strip() for item in comparisons)
    hypothetical = " (hypothetical demonstration soil)" if soil.hypothetical else ""
    return IndicatorResult(
        indicator_id="soil_ph_vs_documented_range", name=_DEFINITIONS["soil_ph_vs_documented_range"].name,
        scope=IndicatorScope.SOIL, status=IndicatorStatus.CONDITIONAL, strategy_id=strategy_id, crop_id=crop.crop_id,
        headline=f"{name}: soil pH {record.value:g}{hypothetical} is {summary}.",
        values=(IndicatorValue(label="Soil pH", value=record.value, unit=Unit.PH, note=record.source_class.value),),
        findings=tuple(gaps) + tuple(record.warnings),
        evidence=evidence,
        conditions=(
            *record.limitations,
            *(condition for item in comparisons for condition in item.decision.conditions),
        ),
        information_layers=_soil_layers(soil),
        uncertainty=assess(
            base=ConfidenceLevel.MODERATE,
            categories=(*_soil_categories(soil), *_evidence_categories(evidence)),
            limitations=(*record.limitations, "Published pH ranges mix optimal, suitable and tolerated values."),
            assumptions=("Hypothetical soil." ,) if soil.hypothetical else (),
        ),
        explanation=IndicatorExplanation(
            what_was_calculated=f"Whether the soil pH supplied lies inside each documented pH range of {name.lower()}.",
            data_and_evidence_used=f"Soil pH from the user ({record.source_class.value.replace('_', ' ')}); the crop's pH ranges from Feedipedia.",
            assumptions="The pH supplied describes the topsoil of the field." + (" It is a hypothetical value." if soil.hypothetical else ""),
            what_it_means="A pH outside a range suggests the soil may need attention for that crop; the kind of range matters.",
            what_it_does_not_establish="It does not establish nutrient availability, toxicity or yield.",
            how_to_improve_confidence="A laboratory soil test, and local advice on liming or crop choice.",
        ),
    )


def soil_water_indicators(crop: CropProfile, soil: ResolvedSoil, *, strategy_id: str, kb: KnowledgeBase, gate: EvidenceGate) -> tuple[IndicatorResult, IndicatorResult]:
    name = _name(crop)
    water, gaps = root_zone_water(crop, soil, gate)
    missing_input = soil.missing_for("rooting-depth-to-soil-water")
    common_missing = [f"{item.explanation} {item.how_to_obtain}" for item in missing_input] + list(gaps)
    no_water = IndicatorExplanation(
        what_was_calculated="Nothing: soil water information or a documented rooting depth is missing.",
        data_and_evidence_used="The user's soil information, FAO-56 Table 19 and Table 22.",
        assumptions="None. No default soil is used.",
        what_it_means="The water a crop's roots could reach cannot be estimated.",
        what_it_does_not_establish="It does not mean the soil holds little or much water.",
        how_to_improve_confidence="Field capacity and wilting point from a soil laboratory, or at least the soil texture class.",
    )
    if water is None:
        return (
            _unavailable("root_zone_available_water", strategy_id=strategy_id, crop_id=crop.crop_id,
                         headline=f"{name}: not available. Soil water information is missing.", missing=common_missing or ["Missing."],
                         explanation=no_water),
            _unavailable("readily_available_water", strategy_id=strategy_id, crop_id=crop.crop_id,
                         headline=f"{name}: not available. Soil water information is missing.", missing=common_missing or ["Missing."],
                         explanation=no_water),
        )
    assert soil.water is not None
    requirements = {item.requirement_id: item for item in crop.requirements}
    rooting_req = next(item for item in crop.requirements if item.variable == "crop_max_rooting_depth")
    evidence = [_used(water.rooting_decision, kb, rooting_req.provenance)]
    if soil.water.gate is not None:
        evidence.append(_used(soil.water.gate, kb, soil.water.provenance))
    hypothetical = " Hypothetical demonstration soil." if soil.hypothetical else ""
    soil_conditions = tuple(soil.water.limitations) + tuple(water.rooting_decision.conditions)
    layers = _soil_layers(soil)
    taw = IndicatorResult(
        indicator_id="root_zone_available_water", name=_DEFINITIONS["root_zone_available_water"].name,
        scope=IndicatorScope.SOIL, status=IndicatorStatus.CONDITIONAL, strategy_id=strategy_id, crop_id=crop.crop_id,
        requirement_id=rooting_req.requirement_id,
        headline=(
            f"{name}: the root zone ({_range_text(water.rooting_depth_min_m, water.rooting_depth_max_m, 'm')}) could hold "
            f"about {_range_text(water.taw_min_mm, water.taw_max_mm, 'mm')} of plant-available water.{hypothetical}"
        ),
        values=(
            IndicatorValue(label="Total available water, low", value=water.taw_min_mm, unit=Unit.MILLIMETRE),
            IndicatorValue(label="Total available water, high", value=water.taw_max_mm, unit=Unit.MILLIMETRE),
        ),
        findings=tuple(gaps),
        evidence=tuple(evidence),
        conditions=soil_conditions,
        information_layers=layers,
        uncertainty=assess(
            base=ConfidenceLevel.MODERATE,
            categories=(*_soil_categories(soil), *_evidence_categories(evidence)),
            limitations=soil.water.limitations,
        ),
        explanation=IndicatorExplanation(
            what_was_calculated=f"FAO-56 Equation 82: 1000 x available water (θFC − θWP) x rooting depth of {name.lower()}.",
            data_and_evidence_used=(
                f"Available water {soil.water.available_water_min:g}-{soil.water.available_water_max:g} m3/m3 "
                f"({soil.water.basis.value.replace('_', ' ')}); rooting depth from {rooting_req.provenance.locator}."
            ),
            assumptions="The soil holds water the same way through the whole root zone, and nothing stops the roots." + hypothetical,
            what_it_means="The size of the soil's water store that this crop's roots can draw on between rains.",
            what_it_does_not_establish="It does not say how full the store is in any season; no water balance is run.",
            how_to_improve_confidence="Measured field capacity and wilting point, and the depth of soil at the field.",
        ),
    )
    if water.raw_min_mm is None or water.depletion_decision is None:
        raw = _unavailable(
            "readily_available_water", strategy_id=strategy_id, crop_id=crop.crop_id,
            headline=f"{name}: not available. No documented depletion fraction is held for {name.lower()}.",
            missing=list(gaps) or ["No depletion fraction."],
            explanation=IndicatorExplanation(
                what_was_calculated="Nothing: the share of soil water the crop can use before stress is not documented.",
                data_and_evidence_used="FAO-56 Table 22 has no row for this crop.",
                assumptions="None. The value of another crop is not borrowed.",
                what_it_means="How much of the stored water the crop can use comfortably cannot be estimated.",
                what_it_does_not_establish="It does not mean the crop is or is not drought tolerant.",
                how_to_improve_confidence="A cited depletion fraction for the crop.",
            ),
        )
    else:
        p_req = next(item for item in crop.requirements if item.variable == "crop_depletion_fraction")
        raw_evidence = (*evidence, _used(water.depletion_decision, kb, p_req.provenance))
        raw = IndicatorResult(
            indicator_id="readily_available_water", name=_DEFINITIONS["readily_available_water"].name,
            scope=IndicatorScope.SOIL, status=IndicatorStatus.CONDITIONAL, strategy_id=strategy_id, crop_id=crop.crop_id,
            requirement_id=p_req.requirement_id,
            headline=(
                f"{name}: about {_range_text(water.raw_min_mm, water.raw_max_mm, 'mm')} of that water can be used before "
                f"stress begins (depletion fraction {water.depletion_fraction:g}).{hypothetical}"
            ),
            values=(
                IndicatorValue(label="Readily available water, low", value=water.raw_min_mm, unit=Unit.MILLIMETRE),
                IndicatorValue(label="Readily available water, high", value=water.raw_max_mm, unit=Unit.MILLIMETRE),
                IndicatorValue(label="Depletion fraction p", value=water.depletion_fraction, unit=Unit.FRACTION),
            ),
            evidence=raw_evidence,
            conditions=(*soil_conditions, p_req.limitation, "FAO-56 gives p for an evapotranspiration rate of about 5 mm/day; it is not adjusted here."),
            information_layers=layers,
            uncertainty=assess(
                base=ConfidenceLevel.MODERATE,
                categories=(*_soil_categories(soil), *_evidence_categories(raw_evidence)),
                limitations=(*soil.water.limitations, p_req.limitation),
            ),
            explanation=IndicatorExplanation(
                what_was_calculated="FAO-56 Equation 83: depletion fraction p x total available water.",
                data_and_evidence_used=f"The total available water above and p from {p_req.provenance.locator}.",
                assumptions="p is taken unadjusted for the local evaporation rate." + hypothetical,
                what_it_means="The part of the soil's water store the crop can use before its water use starts to fall.",
                what_it_does_not_establish="It does not predict stress or yield in any season.",
                how_to_improve_confidence="Measured soil water properties and a daily water balance with reference evapotranspiration.",
            ),
        )
    return taw, raw


# --------------------------------------------------------------------------- #
# Sequence indicators
# --------------------------------------------------------------------------- #


def _identity_evidence(crop: CropProfile, kb: KnowledgeBase, gate: EvidenceGate) -> EvidenceUsed:
    record = crop.sources[0]
    decision = gate.check(f"crop:{crop.crop_id}:identity", record, EvidenceUse.NUMERIC_INPUT)
    return _used(decision, kb, record)


def family_diversity(strategy: RotationStrategy, crops: Sequence[CropProfile], *, kb: KnowledgeBase, gate: EvidenceGate) -> IndicatorResult:
    families = sorted({item.botanical_family for item in crops})
    distinct = len({item.crop_id for item in crops})
    evidence = tuple(_identity_evidence(item, kb, gate) for item in {crop.crop_id: crop for crop in crops}.values())
    return IndicatorResult(
        indicator_id="crop_family_diversity", name=_DEFINITIONS["crop_family_diversity"].name,
        scope=IndicatorScope.SEQUENCE, status=IndicatorStatus.SUPPORTED, strategy_id=strategy.strategy_id,
        headline=f"{strategy.name}: {distinct} crop{'s' if distinct != 1 else ''} from {len(families)} plant famil{'ies' if len(families) != 1 else 'y'} ({', '.join(families)}).",
        values=(
            IndicatorValue(label="Distinct crops", value=float(distinct), unit=Unit.COUNT),
            IndicatorValue(label="Distinct botanical families", value=float(len(families)), unit=Unit.COUNT),
        ),
        evidence=evidence,
        information_layers=(InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION),
        uncertainty=assess(
            base=ConfidenceLevel.HIGH, categories=(),
            limitations=("A count of families is not a measure of soil health or pest control.",),
        ),
        explanation=IndicatorExplanation(
            what_was_calculated="The number of different crops and botanical families in the sequence.",
            data_and_evidence_used="Botanical families from the Feedipedia taxonomic information for each crop.",
            assumptions="None.",
            what_it_means="More families means the sequence is botanically more varied. FAO guidance links rotation in general to effects such as breaking crop-specific pest cycles.",
            what_it_does_not_establish="Family diversity alone does not measure soil health, pest pressure or yield. No source read supports a rule about the same family in succession.",
            how_to_improve_confidence="Local evidence on which pests and diseases the crops share.",
        ),
    )


def legume_in_sequence(
    strategy: RotationStrategy, crops: Sequence[CropProfile], *, kb: KnowledgeBase, gate: EvidenceGate
) -> tuple[IndicatorResult, tuple[BackgroundNote, ...]]:
    legumes = [item for item in {crop.crop_id: crop for crop in crops}.values() if item.nitrogen_fixing]
    evidence = []
    for crop in legumes:
        attribute = next(item for item in crop.attributes if item.attribute == "nitrogen_fixation")
        decision = gate.check(f"crop:{crop.crop_id}:attribute:nitrogen_fixation", attribute.provenance, EvidenceUse.NUMERIC_INPUT)
        evidence.append(_used(decision, kb, attribute.provenance))
    background = []
    for relationship_id in ("cereal-after-grain-legume", "legume-benefit-is-not-only-nitrogen", "fixed-nitrogen-leaves-with-the-grain", "legumes-and-soil-organic-matter"):
        relationship = next((item for item in kb.relationships if item.relationship_id == relationship_id), None)
        if relationship is None:
            continue
        crop_ids = {item.crop_id for item in crops}
        families = {item.botanical_family for item in crops}
        if not (relationship.applies_generally or crop_ids & set(relationship.applies_to_crops) or families & set(relationship.applies_to_families)):
            continue
        for record in relationship.evidence:
            decision = gate.check(f"relationship:{relationship_id}", record, EvidenceUse.BACKGROUND)
            if decision.admitted:
                background.append(BackgroundNote(topic=relationship_id, statement=relationship.statement, evidence=_used(decision, kb, record)))
                break
    names = ", ".join(item.common_name.lower() for item in legumes)
    headline = (
        f"{strategy.name}: includes {len(legumes)} nitrogen-fixing legume{'s' if len(legumes) != 1 else ''} ({names})."
        if legumes
        else f"{strategy.name}: includes no nitrogen-fixing legume."
    )
    return (
        IndicatorResult(
            indicator_id="legume_in_sequence", name=_DEFINITIONS["legume_in_sequence"].name,
            scope=IndicatorScope.SEQUENCE, status=IndicatorStatus.SUPPORTED, strategy_id=strategy.strategy_id,
            headline=headline,
            values=(IndicatorValue(label="Nitrogen-fixing crops", value=float(len(legumes)), unit=Unit.COUNT),),
            findings=tuple(
                f"Background ({note.evidence.status.value.replace('_', ' ')}): {note.statement}" for note in background
            ),
            evidence=tuple(evidence) + tuple(note.evidence for note in background),
            information_layers=(InformationLayer.LITERATURE_VALUE, InformationLayer.DESCRIPTIVE_CALCULATION),
            uncertainty=assess(
                base=ConfidenceLevel.HIGH,
                categories=(),
                limitations=(
                    "Fixing nitrogen is not the same as leaving it for the next crop; no quantity is estimated.",
                    "The background notes rest partly on a study abstract and explain the result; they do not change it.",
                ),
            ),
            explanation=IndicatorExplanation(
                what_was_calculated="Whether the sequence contains a crop the sources describe as a nitrogen-fixing legume.",
                data_and_evidence_used="Cited crop statements (Feedipedia). Background from a review of legume rotations in sub-Saharan Africa (abstract only).",
                assumptions="None.",
                what_it_means="The review abstract reports that cereals grown after grain legumes yielded more on average, with large variation; this is context, not a prediction.",
                what_it_does_not_establish="It does not estimate nitrogen fixed or left in the soil, soil organic matter change or yield.",
                how_to_improve_confidence="Local trials or soil tests, and the full text of the review.",
            ),
        ),
        tuple(background),
    )


def crop_repetition(strategy: RotationStrategy, crops: Sequence[CropProfile]) -> IndicatorResult:
    sequence = list(crops)
    n = len(sequence)
    pairs = [(sequence[i], sequence[(i + 1) % n]) for i in range(n)]
    same_crop = sum(1 for a, b in pairs if a.crop_id == b.crop_id)
    same_family = sum(1 for a, b in pairs if a.botanical_family == b.botanical_family)
    return IndicatorResult(
        indicator_id="crop_repetition", name=_DEFINITIONS["crop_repetition"].name,
        scope=IndicatorScope.SEQUENCE, status=IndicatorStatus.SUPPORTED, strategy_id=strategy.strategy_id,
        headline=(
            f"{strategy.name}: of the {n} step{'s' if n != 1 else ''} in one cycle, {same_crop} keep{'s' if same_crop == 1 else ''} "
            f"the same crop and {same_family} keep{'s' if same_family == 1 else ''} the same plant family."
        ),
        values=(
            IndicatorValue(label="Steps repeating the same crop", value=float(same_crop), unit=Unit.COUNT),
            IndicatorValue(label="Steps repeating the same family", value=float(same_family), unit=Unit.COUNT),
            IndicatorValue(label="Steps in one cycle", value=float(n), unit=Unit.COUNT),
        ),
        findings=(
            "The count of same-family steps is descriptive only: no source read supports a rule against the same family in succession.",
        ),
        information_layers=(InformationLayer.DESCRIPTIVE_CALCULATION,),
        uncertainty=assess(base=ConfidenceLevel.HIGH, categories=(), limitations=("Counts the sequence as given; real fields may break the cycle.",)),
        explanation=IndicatorExplanation(
            what_was_calculated="How many steps of the repeating cycle, including the return to the first slot, keep the same crop or family.",
            data_and_evidence_used="The crop sequence and each crop's botanical family.",
            assumptions="One crop per slot, slots in succession.",
            what_it_means="FAO guidance says rotation prevents the carry-over of crop-specific pests and diseases; repeating a crop gives no such break.",
            what_it_does_not_establish="It does not measure pest or disease pressure.",
            how_to_improve_confidence="Local records of the pests and diseases affecting each crop.",
        ),
    )


# --------------------------------------------------------------------------- #
# Constraints
# --------------------------------------------------------------------------- #


def _constraint_evidence(constraint: RotationConstraint, kb: KnowledgeBase, gate: EvidenceGate) -> tuple[list[EvidenceUsed], bool]:
    used, refused = [], False
    for record in constraint.evidence:
        decision = gate.check(f"constraint:{constraint.constraint_id}", record, EvidenceUse.BACKGROUND)
        if decision.admitted:
            used.append(_used(decision, kb, record))
        else:
            refused = True
    return used, refused and not used


def evaluate_constraints(
    strategy: RotationStrategy,
    crops: Sequence[CropProfile],
    windows: Sequence[WindowScenarios],
    soil: ResolvedSoil,
    *,
    kb: KnowledgeBase,
    gate: EvidenceGate,
) -> tuple[ConstraintFinding, ...]:
    """Evaluate every stored constraint that applies to the strategy's crops, within its evidence scope."""
    unique = list({crop.crop_id: crop for crop in crops}.values())
    ids = {crop.crop_id for crop in unique}
    has_legume = any(crop.nitrogen_fixing for crop in unique)
    findings: list[ConstraintFinding] = []

    def add(constraint: RotationConstraint, outcome: ConstraintOutcome, finding: str, *, crop_id=None, window_id=None, evidence=None):
        findings.append(
            ConstraintFinding(
                constraint_id=constraint.constraint_id, severity=constraint.severity.value, crop_id=crop_id, window_id=window_id,
                outcome=outcome, finding=finding, user_explanation=constraint.user_explanation,
                evidence=tuple(evidence or ()), limitations=constraint.limitations,
            )
        )

    applicable = []
    for constraint in kb.constraints:
        targets = [crop for crop in unique if kb._applies(constraint, crop)]
        if targets:
            applicable.append((constraint, targets))

    for constraint, targets in applicable:
        evidence, unsupported = _constraint_evidence(constraint, kb, gate)
        cid = constraint.constraint_id
        if unsupported:
            add(constraint, ConstraintOutcome.NOT_APPLIED,
                "Not applied: no source read supports this rule, so it does not affect the comparison.", evidence=())
            continue
        if cid in ("frost-kills-maize", "frost-sensitive-crops"):
            for crop in targets:
                for window in windows:
                    seasons = [item for item in window.classified() if item.frost_days is not None]
                    frosty = sum(1 for item in seasons if (item.frost_days or 0) > 0)
                    outcome = ConstraintOutcome.TRIGGERED if frosty else ConstraintOutcome.NOT_TRIGGERED
                    add(constraint, outcome,
                        f"{crop.common_name}, {window.window.name.lower()}: frost days in {frosty} of {len(seasons)} past seasons in the NASA record.",
                        crop_id=crop.crop_id, window_id=window.window.season_id, evidence=evidence)
        elif cid == "cold-stops-common-bean-growth":
            for crop in targets:
                for window in windows:
                    cold = sum(
                        1 for season in window.classified() for value in season.daily_mean_temperature_c if value is not None and value < 10.0
                    )
                    add(constraint, ConstraintOutcome.TRIGGERED if cold else ConstraintOutcome.NOT_TRIGGERED,
                        f"{crop.common_name}, {window.window.name.lower()}: {cold} days with a daily mean below 10 °C across all past seasons.",
                        crop_id=crop.crop_id, window_id=window.window.season_id, evidence=evidence)
        elif cid == "growing-period-longer-than-season":
            for crop in targets:
                admitted, _ = gate.admitted_requirements(crop, "crop_cycle_length")
                if not admitted:
                    add(constraint, ConstraintOutcome.NOT_EVALUATED, f"{crop.common_name}: no documented growing period.", crop_id=crop.crop_id, evidence=evidence)
                    continue
                requirement = admitted[0][0]
                for window in windows:
                    days = window.window.length_days(2001)
                    longer = (requirement.minimum or 0) > days
                    add(constraint, ConstraintOutcome.TRIGGERED if longer else ConstraintOutcome.NOT_TRIGGERED,
                        f"{crop.common_name}, {window.window.name.lower()}: documented growing period "
                        f"{_range_text(requirement.minimum, requirement.maximum, 'days')} against a {days}-day window.",
                        crop_id=crop.crop_id, window_id=window.window.season_id, evidence=evidence)
        elif cid == "seasonal-water-need-above-rainfall":
            for crop in targets:
                admitted, _ = gate.admitted_requirements(crop, "crop_seasonal_water_requirement")
                if not admitted:
                    add(constraint, ConstraintOutcome.NOT_EVALUATED, f"{crop.common_name}: no usable water-use value.", crop_id=crop.crop_id, evidence=evidence)
                    continue
                low = admitted[0][0].minimum
                for window in windows:
                    seasons = window.classified()
                    short = sum(1 for item in seasons if (item.rainfall_total_mm or 0) < (low or 0))
                    add(constraint, ConstraintOutcome.TRIGGERED if short else ConstraintOutcome.NOT_TRIGGERED,
                        f"{crop.common_name}, {window.window.name.lower()}: season rainfall below the low end of indicative "
                        f"water use ({low:g} mm) in {short} of {len(seasons)} past seasons.",
                        crop_id=crop.crop_id, window_id=window.window.season_id, evidence=evidence)
        elif cid == "soil-ph-outside-documented-range":
            for crop in targets:
                comparisons, _ = compare_ph(crop, soil, gate)
                if soil.ph is None or not comparisons:
                    add(constraint, ConstraintOutcome.NOT_EVALUATED,
                        f"{crop.common_name}: " + ("no soil pH was supplied." if soil.ph is None else "no usable pH range."),
                        crop_id=crop.crop_id, evidence=evidence)
                    continue
                outside = [item for item in comparisons if item.position != "inside"]
                add(constraint, ConstraintOutcome.TRIGGERED if outside else ConstraintOutcome.NOT_TRIGGERED,
                    f"{crop.common_name}: soil pH {soil.ph:g} is "
                    + ("; ".join(f"{item.position} the {item.basis} range" for item in comparisons)) + ".",
                    crop_id=crop.crop_id, evidence=evidence)
        elif cid == "temperature-outside-documented-range":
            for crop in targets:
                admitted, _ = gate.admitted_requirements(crop, "crop_temperature_requirement")
                if not admitted:
                    add(constraint, ConstraintOutcome.NOT_EVALUATED,
                        f"{crop.common_name}: no documented temperature range applies to a whole season.", crop_id=crop.crop_id, evidence=evidence)
                    continue
                for window in windows:
                    count = 0
                    seasons = window.classified()
                    for season in seasons:
                        mean = season.mean_temperature_c
                        if mean is None:
                            continue
                        if any(_position(mean, req.minimum, req.maximum) != "within" for req, _ in admitted):
                            count += 1
                    add(constraint, ConstraintOutcome.TRIGGERED if count else ConstraintOutcome.NOT_TRIGGERED,
                        f"{crop.common_name}, {window.window.name.lower()}: the season mean temperature lay outside at least one "
                        f"documented range in {count} of {len(seasons)} past seasons.",
                        crop_id=crop.crop_id, window_id=window.window.season_id, evidence=evidence)
        elif cid == "waterlogging-sensitive-crop-on-wet-soil":
            for crop in targets:
                if soil.drainage is None:
                    add(constraint, ConstraintOutcome.NOT_EVALUATED,
                        f"{crop.common_name}: soil drainage was not supplied. Whether a season was wet enough to waterlog the "
                        "field cannot be told from rainfall totals.", crop_id=crop.crop_id, evidence=evidence)
                else:
                    poor = soil.drainage is SoilDrainageClass.POORLY_DRAINED
                    add(constraint, ConstraintOutcome.TRIGGERED if poor else ConstraintOutcome.NOT_TRIGGERED,
                        f"{crop.common_name}: the field is described as {soil.drainage.value.replace('_', ' ')}; the sources describe "
                        f"{crop.common_name.lower()} as sensitive to waterlogging.", crop_id=crop.crop_id, evidence=evidence)
        elif cid == "drought-at-flowering-maize":
            for crop in targets:
                add(constraint, ConstraintOutcome.NOT_EVALUATED,
                    f"{crop.common_name}: flowering dates are unknown because sowing dates are not known. The longest dry spell "
                    "of each past season is shown in the scenario data.", crop_id=crop.crop_id, evidence=evidence)
        elif cid == "continuous-cereal-without-legume":
            cereal_only = not has_legume
            add(constraint, ConstraintOutcome.TRIGGERED if cereal_only else ConstraintOutcome.NOT_TRIGGERED,
                "The sequence has cereals and no legume." if cereal_only else "The sequence includes a legume.", evidence=evidence)
        elif cid == "legume-needs-pest-management":
            for crop in targets:
                add(constraint, ConstraintOutcome.TRIGGERED,
                    f"{crop.common_name} is in the sequence; at Machakos it was affected by pests and diseases.",
                    crop_id=crop.crop_id, evidence=evidence)
        elif cid == "perennial-in-seasonal-rotation":
            for crop in targets:
                seasonal = len(strategy.crop_sequence) > 1
                add(constraint, ConstraintOutcome.TRIGGERED if seasonal else ConstraintOutcome.NOT_TRIGGERED,
                    f"{crop.common_name} is a short-lived perennial placed in a slot of a seasonal sequence; one slot may span "
                    "more than one season." if seasonal else f"{crop.common_name} is grown alone.",
                    crop_id=crop.crop_id, evidence=evidence)
        elif cid == "same-crop-in-succession":
            n = len(strategy.crop_sequence)
            repeats = sum(1 for i in range(n) if strategy.crop_sequence[i] == strategy.crop_sequence[(i + 1) % n])
            add(constraint, ConstraintOutcome.TRIGGERED if repeats else ConstraintOutcome.NOT_TRIGGERED,
                f"{repeats} of {n} steps in the cycle repeat the same crop.", evidence=evidence)
        else:
            add(constraint, ConstraintOutcome.NOT_EVALUATED, "No evaluation rule is defined for this constraint.", evidence=evidence)
    return tuple(findings)


# --------------------------------------------------------------------------- #
# Strategy assessment
# --------------------------------------------------------------------------- #


def _windows_for(strategy: RotationStrategy, position: int, scenarios: ScenarioSet) -> tuple[WindowScenarios, ...]:
    if strategy.season_assignment is SeasonAssignment.HYPOTHETICAL:
        return (scenarios.window(strategy.slot_seasons[position]),)
    return scenarios.windows


def assess_strategy(
    strategy: RotationStrategy,
    *,
    scenarios: ScenarioSet,
    soil: ResolvedSoil,
    kb: KnowledgeBase,
    gate: EvidenceGate,
    config: PilotConfiguration,
) -> StrategyAssessment:
    validate_strategy(strategy, kb, config)
    sid = strategy.strategy_id
    sequence = [kb.get_crop(crop_id) for crop_id in strategy.crop_sequence]
    etccdi = gate.audit.method_source("etccdi-indices").citation

    indicators: list[IndicatorResult] = []
    evaluated: dict[str, list[str]] = {}
    seen_pairs: set[tuple[str, str]] = set()
    for position, crop in enumerate(sequence):
        for window in _windows_for(strategy, position, scenarios):
            evaluated.setdefault(crop.crop_id, [])
            if window.window.season_id not in evaluated[crop.crop_id]:
                evaluated[crop.crop_id].append(window.window.season_id)
            pair = (crop.crop_id, window.window.season_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            indicators.append(rainfall_vs_water_use(crop, window, strategy_id=sid, kb=kb, gate=gate))
            indicators.extend(temperature_vs_range(crop, window, strategy_id=sid, kb=kb, gate=gate))
            indicators.append(growing_period_vs_window(crop, window, strategy_id=sid, kb=kb, gate=gate))
    windows_used = []
    for position in range(len(sequence)):
        for window in _windows_for(strategy, position, scenarios):
            if window not in windows_used:
                windows_used.append(window)
    for window in windows_used:
        indicators.append(frost_days(window, strategy_id=sid, etccdi_citation=etccdi))
    unique = list({crop.crop_id: crop for crop in sequence}.values())
    for crop in unique:
        indicators.extend(annual_rainfall_vs_range(crop, scenarios, strategy_id=sid, kb=kb, gate=gate))
        indicators.append(soil_ph_indicator(crop, soil, strategy_id=sid, kb=kb, gate=gate))
        indicators.extend(soil_water_indicators(crop, soil, strategy_id=sid, kb=kb, gate=gate))
    indicators.append(family_diversity(strategy, sequence, kb=kb, gate=gate))
    legume, background = legume_in_sequence(strategy, sequence, kb=kb, gate=gate)
    indicators.append(legume)
    indicators.append(crop_repetition(strategy, sequence))

    if strategy.documented_system_id:
        system = next(item for item in kb.cropping_systems if item.system_id == strategy.documented_system_id)
        for record in system.evidence:
            decision = gate.check(f"cropping_system:{system.system_id}", record, EvidenceUse.BACKGROUND)
            if decision.admitted:
                background = (
                    BackgroundNote(
                        topic="documented_study_outcome",
                        statement=f"{system.statement} Reported outcome: {system.reported_outcome or 'none given'}",
                        evidence=_used(decision, kb, record),
                    ),
                    *background,
                )

    constraints = evaluate_constraints(strategy, sequence, windows_used, soil, kb=kb, gate=gate)
    counts = {status: sum(1 for item in indicators if item.status is status) for status in IndicatorStatus}
    unavailable = tuple(item.headline for item in indicators if item.status is IndicatorStatus.UNAVAILABLE)

    families = tuple(sorted({crop.botanical_family for crop in sequence}))
    profile = StrategyProfile(
        strategy_id=sid, name=strategy.name, evidence=strategy.evidence, documented_system_id=strategy.documented_system_id,
        documented_in=(
            next(item.citation for item in kb.sources if item.source_id == "rao-mathuva-2000")
            if strategy.documented_system_id
            else None
        ),
        crops=tuple(
            CropInSequence(
                position=index + 1, crop_id=crop.crop_id, common_name=crop.common_name, botanical_family=crop.botanical_family,
                nitrogen_fixing=crop.nitrogen_fixing, life_cycle=crop.life_cycle.value if crop.life_cycle else None,
                growing_period_days=next(
                    ((req.minimum, req.maximum) for req, _ in gate.admitted_requirements(crop, "crop_cycle_length")[0]
                     if req.minimum is not None and req.maximum is not None),
                    None,
                ),
                seasons_evaluated=tuple(evaluated.get(crop.crop_id, ())),
            )
            for index, crop in enumerate(sequence)
        ),
        distinct_crops=len(unique), families=families, slots_per_cycle=len(sequence),
        seasons_per_cycle=strategy.seasons_per_cycle, season_assignment=strategy.season_assignment,
        required_soil_information=(
            "Soil pH, for the documented pH ranges.",
            "Field capacity and wilting point, available water capacity, or at least the texture class, for root-zone water.",
            "Drainage class, for crops sensitive to waterlogging.",
        ),
        applicable_constraints=tuple(sorted({item.constraint_id for item in constraints})),
        assumptions=strategy.assumptions, limitations=strategy.limitations,
    )
    risks = tuple(
        dict.fromkeys(
            f"{item.finding} {item.user_explanation}"
            for item in constraints
            if item.outcome is ConstraintOutcome.TRIGGERED and item.severity in ("hard", "advisory", "context_dependent")
        )
    )
    gaps = tuple(dict.fromkeys((*unavailable, *(item.explanation for item in soil.missing))))
    return StrategyAssessment(
        strategy=strategy,
        profile=profile,
        indicators=tuple(indicators),
        constraints=constraints,
        background=tuple(background),
        completeness=EvidenceCompleteness(
            supported=counts[IndicatorStatus.SUPPORTED], conditional=counts[IndicatorStatus.CONDITIONAL],
            unavailable=counts[IndicatorStatus.UNAVAILABLE], unavailable_reasons=unavailable,
        ),
        information_gaps=gaps,
        local_review_risks=risks,
        uses_hypothetical_inputs=soil.hypothetical or strategy.season_assignment is SeasonAssignment.HYPOTHETICAL
        or strategy.evidence is StrategyEvidence.HYPOTHETICAL,
    )


# --------------------------------------------------------------------------- #
# Priorities and tradeoffs
# --------------------------------------------------------------------------- #


def build_priority_view(selection: PrioritySelection, strategies: Sequence[StrategyAssessment], kb: KnowledgeBase) -> PriorityView:
    """Order and annotate indicators by the farmer's priorities. No weights, no ranking of strategies."""
    sections = []
    order: list[str] = []
    for index, dimension in enumerate(selection.dimensions, start=1):
        definition = kb.priority(dimension)
        indicator_ids = PRIORITY_INDICATORS[dimension]
        for item in indicator_ids:
            if item not in order:
                order.append(item)
        notes = []
        for assessment in strategies:
            relevant = [item for item in assessment.indicators if item.indicator_id in indicator_ids]
            notes.append(
                PriorityStrategyNote(
                    strategy_id=assessment.strategy.strategy_id,
                    highlights=tuple(item.headline for item in relevant if item.status is not IndicatorStatus.UNAVAILABLE),
                    missing=tuple(item.headline for item in relevant if item.status is IndicatorStatus.UNAVAILABLE),
                )
            )
        unsupported = None
        if not indicator_ids or definition.evidence_available.value == "not_available":
            unsupported = (
                f"CropShift holds no evidence that can assess '{definition.label}'. Nothing is estimated for it. "
                f"What would be needed: {definition.evidence_requirement}"
            )
            if dimension is PriorityDimension.MARKET_SUITABILITY:
                unsupported += (
                    " No prices, costs or market information are held, so profitability is not estimated. One study "
                    "abstract reports a profitability comparison for 1989 to 1996, but gives no prices or method, so it is not used."
                )
        sections.append(
            PrioritySection(
                dimension=dimension, order=index, label=definition.label, why_it_matters=definition.description,
                evidence_available=definition.evidence_available.value, indicator_ids=indicator_ids,
                strategy_notes=tuple(notes), unsupported_note=unsupported, limitations=definition.limitations,
            )
        )
    for item in INDICATORS:
        if item.indicator_id not in order:
            order.append(item.indicator_id)
    return PriorityView(selection=selection, sections=tuple(sections), indicator_order=tuple(order))


def build_tradeoffs(strategies: Sequence[StrategyAssessment]) -> tuple[TradeoffNote, ...]:
    """Plain statements of how the strategies differ. Deliberately no winner."""
    if len(strategies) < 2:
        return ()
    names = tuple(item.strategy.name for item in strategies)
    notes = []
    families = {item.strategy.name: len(item.profile.families) for item in strategies}
    notes.append(
        TradeoffNote(
            aspect="Plant-family diversity",
            statement="; ".join(f"{name}: {count} famil{'ies' if count != 1 else 'y'}" for name, count in families.items())
            + ". More families means a more varied sequence; on its own it does not measure soil health.",
            strategies_involved=names,
        )
    )
    water = {}
    for item in strategies:
        crops = {crop.crop_id: crop.common_name for crop in item.profile.crops}
        missing = sorted(
            {crops[result.crop_id] for result in item.indicators if result.indicator_id == "rainfall_vs_crop_water_use"
             and result.status is IndicatorStatus.UNAVAILABLE and result.crop_id}
        )
        water[item.strategy.name] = missing
    notes.append(
        TradeoffNote(
            aspect="Water-use evidence",
            statement="; ".join(
                f"{name}: {'indicative water use is documented for every crop' if not missing else 'no verified water use for ' + ', '.join(m.lower() for m in missing)}"
                for name, missing in water.items()
            )
            + ". Where evidence is missing the comparison is incomplete, not favourable.",
            strategies_involved=names,
        )
    )
    legumes = {item.strategy.name: [crop.common_name.lower() for crop in item.profile.crops if crop.nitrogen_fixing] for item in strategies}
    notes.append(
        TradeoffNote(
            aspect="Legumes and pest management",
            statement="; ".join(
                f"{name}: {', '.join(dict.fromkeys(items)) if items else 'no legume'}" for name, items in legumes.items()
            )
            + ". Past study results, not predictions: a review abstract reports higher average cereal yields after grain "
            "legumes in sub-Saharan Africa, with large variation and weaker effects after cowpea than after soybean or "
            "groundnut. At Machakos, maize after cowpea yielded about 17 % more than continuous maize, maize after pigeon "
            "pea only marginally more, and both legumes were affected by pests and diseases.",
            strategies_involved=names,
        )
    )
    shared = set.intersection(*({crop.crop_id for crop in item.profile.crops} for item in strategies))
    if shared:
        crop_names = ", ".join(sorted(shared))
        notes.append(
            TradeoffNote(
                aspect="What is the same",
                statement=f"Every strategy contains {crop_names}; its weather comparisons are identical across strategies. "
                "The strategies differ in what is grown in the other slots.",
                strategies_involved=names,
            )
        )
    return tuple(notes)


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def compare_strategies(
    strategies: Sequence[RotationStrategy] = CANDIDATE_STRATEGIES,
    *,
    scenarios: ScenarioSet,
    kb: KnowledgeBase,
    gate: EvidenceGate,
    config: PilotConfiguration,
    soil: SoilProfileInput | None = None,
    priorities: PrioritySelection | None = None,
    generated_at: datetime | None = None,
) -> ComparisonReport:
    """Compare strategies side by side. Deterministic for the same inputs and ``generated_at``."""
    if not strategies:
        raise ComparisonError("at least one strategy is needed")
    if (scenarios.location.latitude, scenarios.location.longitude) != (config.location.latitude, config.location.longitude):
        raise ComparisonError("the scenarios were built for a different location than the configuration")
    resolved = resolve_soil(soil, location=config.location, gate=gate)
    assessments = tuple(
        assess_strategy(item, scenarios=scenarios, soil=resolved, kb=kb, gate=gate, config=config) for item in strategies
    )
    stamp = generated_at or _now()
    overview = tuple(
        ScenarioOverview(
            window_id=item.window.season_id, name=item.window.name, window_basis=item.window.basis,
            seasons_classified=item.classified_count, dry_upper_mm=item.dry_upper_mm, wet_lower_mm=item.wet_lower_mm,
            representative=item.representative, rainfall_mean_mm=item.rainfall_mean_mm,
            rainfall_cv_percent=item.rainfall_cv_percent, excluded=item.excluded,
        )
        for item in scenarios.windows
    )
    limitations = (
        config.approval_note,
        *scenarios.limitations,
        "No overall score or ranking is produced: the indicators measure unlike things and no defensible weighting exists here.",
        "The knowledge base has not been reviewed by an agronomist.",
    )
    if resolved.hypothetical:
        limitations = ("The soil used is a hypothetical demonstration profile, not data from any field.", *limitations)
    return ComparisonReport(
        report_id=f"comparison-{config.site.site_id}"[:64],
        engine_version=ENGINE_VERSION,
        generated_at=stamp,
        site_id=config.site.site_id,
        site_name=config.site.name,
        pilot_status=config.status,
        approval_note=config.approval_note,
        location=config.location,
        knowledge_base_version=kb.manifest.knowledge_base_version,
        audit_version=gate.audit.audit_version,
        dataset_id=scenarios.dataset_id,
        payload_sha256=scenarios.payload_sha256,
        dataset_citations=scenarios.dataset_citations,
        observation_period=(scenarios.observation_start.isoformat(), scenarios.observation_end.isoformat()),
        scenarios=overview,
        soil=resolved,
        strategies=assessments,
        priorities=build_priority_view(priorities, assessments, kb) if priorities else None,
        tradeoffs=build_tradeoffs(assessments),
        unsupported_outcomes=UNSUPPORTED_OUTCOMES,
        limitations=limitations,
    )


def run_pilot_comparison(
    *,
    settings=None,
    soil: SoilProfileInput | None = None,
    priorities: PrioritySelection | None = None,
    strategies: Sequence[RotationStrategy] = CANDIDATE_STRATEGIES,
) -> ComparisonReport:
    """Load everything for the pilot site and compare. Works offline with bundled data."""
    from src.crop_knowledge import load_knowledge_base
    from src.data_service import load_pilot_dataset
    from src.evidence_audit import load_evidence_gate
    from src.scenario_engine import build_scenarios
    from src.season_config import pilot_configuration

    kb = load_knowledge_base()
    gate = load_evidence_gate(kb)
    config = pilot_configuration()
    dataset = load_pilot_dataset(config.site, settings=settings)
    scenarios = build_scenarios(dataset, config.windows)
    return compare_strategies(
        strategies, scenarios=scenarios, kb=kb, gate=gate, config=config, soil=soil, priorities=priorities
    )


# --------------------------------------------------------------------------- #
# Export to the A1 contracts
# --------------------------------------------------------------------------- #


def _to_comparison_result(report: ComparisonReport) -> ComparisonResult:
    engine = ProvenanceRecord(
        kind=DataKind.DERIVED, source_id=ENGINE_SOURCE_ID, source_name="CropShift comparison engine",
        source_version=ENGINE_VERSION, transformations=("Season totals and counts from validated NASA POWER data.",),
    )
    scenario_ids = []
    for overview in report.scenarios:
        for category in ScenarioCategory:
            if category in overview.representative:
                scenario_ids.append(overview.representative[category])
    results = []
    for assessment in report.strategies:
        families = next(item for item in assessment.indicators if item.indicator_id == "crop_family_diversity")
        family_count = next(value.value for value in families.values if value.label == "Distinct botanical families")
        frost = {item.window_id: item for item in assessment.indicators if item.indicator_id == "frost_days"}
        for overview in report.scenarios:
            for category in ScenarioCategory:
                season_id = overview.representative.get(category)
                if season_id is None or overview.window_id not in frost:
                    continue
                rain = next(
                    (item for item in frost[overview.window_id].season_findings if item.season_id == season_id), None
                )
                results.append(
                    ScenarioResult(
                        rotation_id=assessment.strategy.strategy_id,
                        scenario_id=season_id,
                        indicators=(
                            ScientificValue(variable="indicator_family_count", value=family_count, unit=Unit.COUNT, provenance=engine),
                            ScientificValue(variable="indicator_frost_days", value=rain.value if rain else None,
                                            unit=Unit.COUNT, provenance=engine,
                                            missing="present" if rain and rain.value is not None else "not_provided"),
                        ),
                        uncertainty=frost[overview.window_id].uncertainty,
                        engine_version=ENGINE_VERSION,
                        computed_at=report.generated_at,
                        input_source_ids=("nasa-power", "etccdi-indices"),
                    )
                )
    assessments = []
    for assessment in report.strategies:
        support = [item for item in assessment.background]
        records = [
            ProvenanceRecord(
                kind=DataKind.LITERATURE_VALUE, source_id=note.evidence.source_id, source_name=note.evidence.source_id,
                citation=note.evidence.citation, locator=note.evidence.locator,
            )
            for note in support
        ] or [engine]
        assessments.append(
            RotationAssessment(
                rotation_id=assessment.strategy.strategy_id,
                rationale=assessment.strategy.description,
                supporting_evidence=tuple(records),
                potential_benefits=tuple(note.statement for note in support if note.topic != "documented_study_outcome"),
                information_gaps=assessment.information_gaps,
                local_review_risks=assessment.local_review_risks,
            )
        )
    current = next((item.strategy.strategy_id for item in report.strategies if item.strategy.role.value == "current_practice"), None)
    ids = tuple(item.strategy.strategy_id for item in report.strategies)
    if len(ids) < 2:
        raise ComparisonError("the A1 comparison contract needs at least two strategies")
    return ComparisonResult(
        comparison_id=report.report_id,
        location=report.location,
        rotation_ids=ids,
        scenario_ids=tuple(dict.fromkeys(scenario_ids)),
        current_practice_rotation_id=current,
        results=tuple(results),
        assessments=tuple(assessments),
        priorities=None,
        uncertainty=assess(
            base=ConfidenceLevel.MODERATE,
            categories=(*_NASA, UncertaintyCategory.SEASON_ASSUMPTION, UncertaintyCategory.CONTEXT_DEPENDENT_EVIDENCE),
            limitations=report.limitations,
        ),
        generated_at=report.generated_at,
    )
