"""Uncertainty, limitations and explanations (phase A4.7).

Responsibility
    Turn what the engine knows about its inputs into an
    ``models.UncertaintyStatement`` for every indicator, and give every
    indicator a six-part plain-language explanation. Everything here is
    deterministic: fixed rules and templates filled from structured data. No AI
    service is involved, so every explanation is available offline.

Confidence rule
    Confidence is never stated without its reasons. It starts from what the
    indicator is built on and is capped by the weakest input:

    * a structural fact from verified taxonomy (for example how many plant
      families a sequence contains) starts at HIGH;
    * a description of the NASA record starts at MODERATE, because the record is
      a reanalysis for a grid cell tens of kilometres wide (location
      approximation, model limitation);
    * any context-dependent or abstract-only evidence, unverified soil input or
      season assumption caps confidence at LOW;
    * an unavailable or unsupported indicator is NOT_ASSESSED.

Information layers
    Every indicator lists which kinds of information it combines, so that NASA
    observations, CropShift's own descriptive calculations, literature values,
    user-entered soil information and hypothetical assumptions are never
    confused with each other.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import Field

from src.models import ConfidenceLevel, Contract, Text, UncertaintyCategory, UncertaintyStatement


class InformationLayer(StrEnum):
    NASA_OBSERVATION = "nasa_observation"  # values from NASA POWER, unmodified
    DESCRIPTIVE_CALCULATION = "descriptive_calculation"  # CropShift totals, counts and comparisons
    LITERATURE_VALUE = "literature_value"  # a cited crop or soil characteristic
    USER_SOIL_INPUT = "user_soil_input"  # soil information supplied by the user
    HYPOTHETICAL_ASSUMPTION = "hypothetical_assumption"  # a demonstration value or a chosen sequence
    UNAVAILABLE = "unavailable"  # the information needed does not exist in the tool


CATEGORY_TEXT: dict[UncertaintyCategory, str] = {
    UncertaintyCategory.DATA_MISSING: "Some information this indicator needs is missing.",
    UncertaintyCategory.SOURCE_UNVERIFIED: "Part of the evidence could not be verified against its source.",
    UncertaintyCategory.ABSTRACT_ONLY_EVIDENCE: (
        "Part of the evidence rests on a study abstract; the full study was not read."
    ),
    UncertaintyCategory.CONTEXT_DEPENDENT_EVIDENCE: (
        "The crop values hold under conditions the source describes, which may differ at this site."
    ),
    UncertaintyCategory.LOCATION_APPROXIMATION: (
        "The NASA values describe grid cells tens of kilometres wide, not a particular farm."
    ),
    UncertaintyCategory.SEASON_ASSUMPTION: (
        "Season windows are fixed calendar windows and sowing dates are not known."
    ),
    UncertaintyCategory.SOIL_INPUT_UNVERIFIED: (
        "The soil information was supplied by the user, or is a typical or hypothetical value, and has not "
        "been verified."
    ),
    UncertaintyCategory.MODEL_LIMITATION: (
        "The NASA weather values come from a reanalysis, a weather model constrained by observations, and the "
        "indicator is a simple description, not a crop or water-balance model."
    ),
    UncertaintyCategory.INCOMPLETE_OBSERVATION_PERIOD: "Some seasons or years could not be used because data were missing.",
    UncertaintyCategory.UNSUPPORTED_INDICATOR: "The evidence needed for this indicator does not exist in the tool.",
}

_CAP_LOW = frozenset(
    {
        UncertaintyCategory.CONTEXT_DEPENDENT_EVIDENCE,
        UncertaintyCategory.ABSTRACT_ONLY_EVIDENCE,
        UncertaintyCategory.SOIL_INPUT_UNVERIFIED,
        UncertaintyCategory.SEASON_ASSUMPTION,
        UncertaintyCategory.SOURCE_UNVERIFIED,
    }
)
_CAP_MODERATE = frozenset({UncertaintyCategory.LOCATION_APPROXIMATION, UncertaintyCategory.MODEL_LIMITATION})
_ORDER = (ConfidenceLevel.NOT_ASSESSED, ConfidenceLevel.LOW, ConfidenceLevel.MODERATE, ConfidenceLevel.HIGH)


class IndicatorExplanation(Contract):
    """The six questions every indicator answers, in plain language."""

    what_was_calculated: Text
    data_and_evidence_used: Text
    assumptions: Text
    what_it_means: Text
    what_it_does_not_establish: Text
    how_to_improve_confidence: Text


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return tuple(seen)


def assess(
    *,
    base: ConfidenceLevel,
    categories: Iterable[UncertaintyCategory],
    limitations: Iterable[str],
    assumptions: Iterable[str] = (),
    available: bool = True,
) -> UncertaintyStatement:
    """Build the uncertainty statement for one indicator from what is known about it."""
    found = tuple(dict.fromkeys(categories))
    if not available:
        found = tuple(dict.fromkeys((*found, UncertaintyCategory.UNSUPPORTED_INDICATOR)))
        level = ConfidenceLevel.NOT_ASSESSED
    else:
        level = base
        if any(item in _CAP_MODERATE for item in found) and _ORDER.index(level) > _ORDER.index(ConfidenceLevel.MODERATE):
            level = ConfidenceLevel.MODERATE
        if any(item in _CAP_LOW for item in found):
            level = ConfidenceLevel.LOW
    reasons = [CATEGORY_TEXT[item] for item in found]
    if not available:
        basis = "Not assessed: the indicator could not be calculated. " + " ".join(reasons)
    elif not reasons:
        basis = f"{level.value.title()}: built only on verified facts and deterministic counting."
    else:
        basis = f"{level.value.title()} because: " + " ".join(reasons)
    limits = _unique(limitations) or ("No further limitation recorded.",)
    return UncertaintyStatement(
        confidence=level,
        confidence_basis=basis,
        sources_of_uncertainty=tuple(reasons),
        assumptions=_unique(assumptions),
        limitations=limits,
        requires_local_review=True,
        categories=found,
    )


class UnsupportedOutcome(Contract):
    """Something a farmer may want to know that this tool deliberately does not estimate."""

    outcome: Text
    reason: Text
    what_would_be_needed: Text


UNSUPPORTED_OUTCOMES: tuple[UnsupportedOutcome, ...] = (
    UnsupportedOutcome(
        outcome="Crop yield",
        reason="No validated crop model is part of the tool. Yield changes reported by one study are shown as "
        "background, never as a prediction.",
        what_would_be_needed="A crop model calibrated and validated for the site, its soils and its varieties.",
    ),
    UnsupportedOutcome(
        outcome="Profit or economic return",
        reason="The tool holds no prices, costs, labour or market information.",
        what_would_be_needed="Local prices, input costs and labour data, and a farm budget method.",
    ),
    UnsupportedOutcome(
        outcome="Amount of nitrogen fixed or left for the next crop",
        reason="The sources give wide ranges for other places, and one reports that most fixed nitrogen leaves "
        "the field with the pigeon pea grain.",
        what_would_be_needed="Field measurements, or a validated nitrogen model, for local varieties and management.",
    ),
    UnsupportedOutcome(
        outcome="Change in soil organic carbon",
        reason="No soil carbon model is part of the tool, and the review read reports that studies generally "
        "find no effect of grain legumes on soil organic matter.",
        what_would_be_needed="Repeated soil measurements or a validated soil carbon model.",
    ),
    UnsupportedOutcome(
        outcome="Irrigation requirement",
        reason="Rainfall alone cannot give irrigation demand: crop water use, effective rainfall and soil storage "
        "are needed, and reference evapotranspiration is not yet calculated (it needs wind speed).",
        what_would_be_needed="A daily soil water balance with reference evapotranspiration (FAO-56).",
    ),
    UnsupportedOutcome(
        outcome="Pest or disease incidence",
        reason="No pest or disease model or local survey data are part of the tool; the review read says evidence "
        "on rotation effects on cereal pests in sub-Saharan Africa is lacking.",
        what_would_be_needed="Local pest and disease records and expert assessment.",
    ),
    UnsupportedOutcome(
        outcome="Soil erosion",
        reason="The knowledge base holds no erosion evidence for these crops or this site.",
        what_would_be_needed="Slope, soil and cover information and an erosion assessment method.",
    ),
    UnsupportedOutcome(
        outcome="An overall resilience score or a 'best' rotation",
        reason="No defensible method exists here for weighing unlike indicators against each other, so results "
        "are shown side by side with their tradeoffs instead.",
        what_would_be_needed="An agreed, validated scoring method and the farmer's own judgement.",
    ),
)


class TradeoffNote(Contract):
    """A plain statement of how strategies differ on one aspect, without ranking them."""

    aspect: Text
    statement: Text
    strategies_involved: tuple[Text, ...] = Field(min_length=1)
