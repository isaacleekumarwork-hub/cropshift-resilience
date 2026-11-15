"""Pilot configuration, rainy-season windows and rotation strategies (phase A4.3).

Responsibility
    Say where the comparison is made, which part of the year each historical
    season covers, and which crop sequences are compared, with every
    assumption recorded beside the setting it affects.

The pilot site is provisional
    Katumani, Machakos County, Kenya, at the coordinates used in A2. The
    participant has not approved it, so the configuration is ``PROVISIONAL``
    and every result says so. The site is replaceable: nothing in the engine
    refers to Katumani by name.

Season windows are analysis windows, not sowing dates
    FAO GIEWS describes the long rains in Kenya's marginal bimodal-rainfall
    south-eastern areas as typically extending from March to May, and the short
    rains as October to December. CropShift totals the NASA record over those
    calendar windows. It does not assume a crop is sown on the first day of a
    window, and it reports when a crop's documented growing period is longer
    than the window.

Crop sequences
    The three candidate strategies are the rotations and the baseline that Rao
    and Mathuva (2000) grew at Machakos. The abstract read does not say which
    crop was grown in which season, so by default the season of every crop is
    ``UNKNOWN`` and the engine shows each crop against both rainy seasons. A user
    may choose a season for each slot; that sequence is then labelled
    ``HYPOTHETICAL`` and is never presented as the study's design.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import calendar
from datetime import date
from enum import StrEnum

from pydantic import Field, model_validator

from src.crop_knowledge import KnowledgeBase, KnowledgeBaseError
from src.models import Contract, GeoLocation, RotationRole, Slug, Text, _require_unique
from src.pilot_sites import PILOT_SITE, PilotSite


class UnknownCropError(KnowledgeBaseError):
    """A strategy names a crop that the knowledge base does not hold."""


# --------------------------------------------------------------------------- #
# Season windows
# --------------------------------------------------------------------------- #


class WindowSource(StrEnum):
    CITED = "cited"  # stated by a registered source
    USER_DEFINED = "user_defined"  # chosen by the user; no source


class SeasonWindow(Contract):
    """A recurring part of the year over which past weather is summarised."""

    season_id: Slug
    name: Text
    start_month: int = Field(ge=1, le=12)
    start_day: int = Field(default=1, ge=1, le=31)
    end_month: int = Field(ge=1, le=12)
    end_day: int | None = Field(default=None, ge=1, le=31, description="None means the last day of the month.")
    source_status: WindowSource
    source_ids: tuple[Slug, ...] = ()
    basis: Text = Field(description="Where the window comes from, in words.")
    limitations: tuple[Text, ...] = Field(min_length=1)
    is_sowing_date: bool = Field(default=False, description="Always False: a window is not a sowing date.")

    @model_validator(mode="after")
    def _check_window(self) -> "SeasonWindow":
        if self.is_sowing_date:
            raise ValueError("a season window is an analysis window, never a sowing date")
        # Day numbers are checked against a non-leap year; 29 February is not a valid boundary.
        if self.start_day > calendar.monthrange(2001, self.start_month)[1]:
            raise ValueError("start_day does not exist in start_month")
        if self.end_day is not None and self.end_day > calendar.monthrange(2001, self.end_month)[1]:
            raise ValueError("end_day does not exist in end_month")
        if self.source_status is WindowSource.CITED and not self.source_ids:
            raise ValueError("a cited window must name its source")
        if self.source_status is WindowSource.USER_DEFINED and self.source_ids:
            raise ValueError("a user-defined window has no source; record the user's reason in basis")
        start, end = (self.start_month, self.start_day), (self.end_month, self.end_day or 31)
        if start == end:
            raise ValueError("a season window must last more than one day")
        return self

    @property
    def crosses_year(self) -> bool:
        """True if the window starts in one calendar year and ends in the next."""
        return (self.end_month, self.end_day or 31) < (self.start_month, self.start_day)

    def dates_for(self, season_year: int) -> tuple[date, date]:
        """First and last day of the window for the season that starts in ``season_year``."""
        start = date(season_year, self.start_month, self.start_day)
        end_year = season_year + 1 if self.crosses_year else season_year
        end_day = self.end_day or calendar.monthrange(end_year, self.end_month)[1]
        return start, date(end_year, self.end_month, end_day)

    def length_days(self, season_year: int) -> int:
        start, end = self.dates_for(season_year)
        return (end - start).days + 1

    def label_for(self, season_year: int) -> str:
        start, end = self.dates_for(season_year)
        if self.crosses_year:
            return f"{self.name} {start.year}/{end.year}"
        return f"{self.name} {season_year}"


_GIEWS_LIMITS = (
    "An analysis window, not a sowing date. Actual onset and end vary from year to year; the same FAO "
    "brief reports that the 2026 long rains began early, in mid-February.",
    "The FAO brief describes a broad zone and does not name Machakos; placing the site in that zone is "
    "this project's assumption.",
)

LONG_RAINS = SeasonWindow(
    season_id="long-rains",
    name="Long rains",
    start_month=3,
    end_month=5,
    source_status=WindowSource.CITED,
    source_ids=("fao-giews-kenya",),
    basis="FAO GIEWS: in marginal bimodal-rainfall south-eastern areas the long rains 'typically extend from March to May'.",
    limitations=_GIEWS_LIMITS,
)

SHORT_RAINS = SeasonWindow(
    season_id="short-rains",
    name="Short rains",
    start_month=10,
    end_month=12,
    source_status=WindowSource.CITED,
    source_ids=("fao-giews-kenya",),
    basis="FAO GIEWS refers to the October-December short rains for the same areas.",
    limitations=_GIEWS_LIMITS,
)

PILOT_WINDOWS: tuple[SeasonWindow, ...] = (LONG_RAINS, SHORT_RAINS)


# --------------------------------------------------------------------------- #
# Pilot configuration
# --------------------------------------------------------------------------- #


class PilotStatus(StrEnum):
    PROVISIONAL = "provisional"  # proposed, not approved by the participant
    APPROVED = "approved"


class LocationCheck(Contract):
    """A recorded check that the coordinates are where the site is said to be."""

    checked_on: date
    method: Text
    result: Text


class PilotConfiguration(Contract):
    """Everything about where and when the comparison is made."""

    site: PilotSite
    status: PilotStatus
    windows: tuple[SeasonWindow, ...] = Field(min_length=1)
    location_checks: tuple[LocationCheck, ...] = ()
    assumptions: tuple[Text, ...] = ()
    approval_note: Text

    @model_validator(mode="after")
    def _check_configuration(self) -> "PilotConfiguration":
        if self.status is PilotStatus.APPROVED and not self.site.approved:
            raise ValueError("a configuration can be approved only for a site the participant approved")
        if self.status is PilotStatus.PROVISIONAL and self.site.approved:
            raise ValueError("an approved site should not be configured as provisional")
        _require_unique([item.season_id for item in self.windows], "season windows")
        return self

    @property
    def location(self) -> GeoLocation:
        return self.site.location

    def window(self, season_id: str) -> SeasonWindow:
        for item in self.windows:
            if item.season_id == season_id:
                return item
        raise KeyError(f"no season window '{season_id}' in the configuration")


def pilot_configuration(site: PilotSite = PILOT_SITE, windows: tuple[SeasonWindow, ...] = PILOT_WINDOWS) -> PilotConfiguration:
    """The configuration for a site; provisional until the participant approves the site."""
    return PilotConfiguration(
        site=site,
        status=PilotStatus.APPROVED if site.approved else PilotStatus.PROVISIONAL,
        windows=windows,
        location_checks=(
            LocationCheck(
                checked_on=date(2026, 11, 15),
                method="Reverse geocoding of the A2 coordinates (-1.58, 37.24) with OpenStreetMap Nominatim, one request.",
                result="Mua ward, Machakos Town, Machakos County, Kenya. Data © OpenStreetMap contributors (ODbL).",
            ),
            LocationCheck(
                checked_on=date(2026, 11, 14),
                method="NASA POWER echo of the requested point in the A2 pilot retrieval.",
                result="NASA POWER returned the same coordinates, with a grid-cell elevation of 1,327.62 m.",
            ),
        )
        if site.site_id == "katumani-machakos-ke"
        else (),
        assumptions=(
            "The NASA grid cells containing the point represent conditions in the surrounding area; they "
            "are not measurements from any farm.",
            "The season windows describe the rainy seasons of the area; crops may be sown before, at or after "
            "the start of a window.",
        ),
        approval_note=(
            "The participant has approved this site."
            if site.approved
            else "Provisional: the participant has not approved this pilot site. It must not be presented as "
            "the project's finalised site until approved."
        ),
    )


# --------------------------------------------------------------------------- #
# Rotation strategies
# --------------------------------------------------------------------------- #


class StrategyEvidence(StrEnum):
    DOCUMENTED_SYSTEM = "documented_system"  # grown and compared in a cited study
    HYPOTHETICAL = "hypothetical"  # assembled by the user; no study grew it


class SeasonAssignment(StrEnum):
    UNKNOWN = "unknown"  # the season of each crop is not known: every window is shown
    HYPOTHETICAL = "hypothetical"  # the user chose a season for each slot


class PlantingDateStatus(StrEnum):
    UNKNOWN = "unknown"
    HYPOTHETICAL_USER_SELECTED = "hypothetical_user_selected"
    DOCUMENTED = "documented"


class RotationStrategy(Contract):
    """An ordered, repeating crop sequence to compare.

    ``crop_sequence`` lists one crop per slot, in order; the cycle repeats. If
    the season of each slot is not known, ``slot_seasons`` is empty.
    """

    strategy_id: Slug
    name: Text
    crop_sequence: tuple[Slug, ...] = Field(min_length=1)
    role: RotationRole
    evidence: StrategyEvidence
    documented_system_id: Slug | None = None
    season_assignment: SeasonAssignment = SeasonAssignment.UNKNOWN
    slot_seasons: tuple[Slug, ...] = ()
    planting_dates: PlantingDateStatus = PlantingDateStatus.UNKNOWN
    seasons_per_cycle: int | None = Field(
        default=None, ge=1, le=40, description="None when the cycle length was not reported."
    )
    description: Text
    assumptions: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check_strategy(self) -> "RotationStrategy":
        if self.evidence is StrategyEvidence.DOCUMENTED_SYSTEM and self.documented_system_id is None:
            raise ValueError("a documented strategy must name the cropping system a study grew")
        if self.evidence is StrategyEvidence.HYPOTHETICAL and self.documented_system_id is not None:
            raise ValueError("a hypothetical strategy cannot claim a documented system")
        if self.season_assignment is SeasonAssignment.UNKNOWN:
            if self.slot_seasons:
                raise ValueError("slot seasons are given, so the assignment is hypothetical, not unknown")
            if self.planting_dates is not PlantingDateStatus.UNKNOWN:
                raise ValueError("planting dates cannot be known when the season of each crop is not")
        else:
            if len(self.slot_seasons) != len(self.crop_sequence):
                raise ValueError("give one season for every slot in the crop sequence")
            if not any("hypothetical" in item.lower() for item in self.assumptions):
                raise ValueError("a hypothetical season assignment must be declared in the assumptions")
        if self.planting_dates is PlantingDateStatus.DOCUMENTED:
            raise ValueError("no source read documents planting dates for these strategies")
        return self

    @property
    def is_continuous(self) -> bool:
        return len(set(self.crop_sequence)) == 1

    def with_seasons(self, slot_seasons: tuple[str, ...], *, reason: str) -> "RotationStrategy":
        """A copy with a user-chosen season for each slot, labelled hypothetical throughout."""
        return self.model_copy(
            update={
                "season_assignment": SeasonAssignment.HYPOTHETICAL,
                "slot_seasons": tuple(slot_seasons),
                "planting_dates": PlantingDateStatus.HYPOTHETICAL_USER_SELECTED,
                "assumptions": (
                    *self.assumptions,
                    f"Hypothetical season assignment chosen by the user ({reason}). It does not reproduce "
                    "the design of any published study.",
                ),
            }
        )


_SEASON_NOT_REPORTED = (
    "The study abstract does not say which crop was grown in which rainy season, so each crop is shown "
    "against both seasons."
)

CONTINUOUS_MAIZE = RotationStrategy(
    strategy_id="continuous-maize",
    name="Continuous maize",
    crop_sequence=("maize",),
    role=RotationRole.CURRENT_PRACTICE,
    evidence=StrategyEvidence.DOCUMENTED_SYSTEM,
    documented_system_id="machakos-continuous-maize",
    seasons_per_cycle=1,
    description="Maize in every season. The comparison baseline in the Machakos experiment (Rao and Mathuva, 2000).",
    assumptions=(
        "Treated as the baseline because it was the baseline of the Machakos experiment. Whether it is "
        "any particular farmer's current practice is for the user to say.",
    ),
    limitations=(_SEASON_NOT_REPORTED,),
)

MAIZE_COWPEA = RotationStrategy(
    strategy_id="maize-cowpea",
    name="Maize rotated with cowpea",
    crop_sequence=("maize", "cowpea"),
    role=RotationRole.ALTERNATIVE,
    evidence=StrategyEvidence.DOCUMENTED_SYSTEM,
    documented_system_id="machakos-maize-cowpea-rotation",
    description="Maize in sequence with cowpea, a short-duration legume, as grown at Machakos (Rao and Mathuva, 2000).",
    assumptions=("One crop per slot, slots in succession; the length of one cycle was not reported.",),
    limitations=(
        _SEASON_NOT_REPORTED,
        "No seasonal water need, growing period or soil pH range is held for cowpea.",
    ),
)

MAIZE_PIGEON_PEA = RotationStrategy(
    strategy_id="maize-pigeon-pea",
    name="Maize rotated with pigeon pea",
    crop_sequence=("maize", "pigeon-pea"),
    role=RotationRole.ALTERNATIVE,
    evidence=StrategyEvidence.DOCUMENTED_SYSTEM,
    documented_system_id="machakos-maize-pigeon-pea-rotation",
    description="Maize rotated with pigeon pea, a long-duration legume, as grown at Machakos (Rao and Mathuva, 2000).",
    assumptions=("One crop per slot, slots in succession; the length of one cycle was not reported.",),
    limitations=(
        _SEASON_NOT_REPORTED,
        "Pigeon pea is a short-lived perennial and a long-duration crop; one slot may span more than one season.",
        "No verified water requirement, growing period or depletion fraction is held for pigeon pea.",
    ),
)

CANDIDATE_STRATEGIES: tuple[RotationStrategy, ...] = (CONTINUOUS_MAIZE, MAIZE_COWPEA, MAIZE_PIGEON_PEA)


def validate_strategy(strategy: RotationStrategy, kb: KnowledgeBase, config: PilotConfiguration) -> RotationStrategy:
    """Check a strategy against the knowledge base and the configuration; return it unchanged."""
    for crop_id in strategy.crop_sequence:
        try:
            kb.get_crop(crop_id)
        except KnowledgeBaseError:
            raise UnknownCropError(
                f"strategy '{strategy.strategy_id}' names the crop '{crop_id}', which is not in the knowledge base"
            ) from None
    if strategy.documented_system_id is not None:
        system = next((item for item in kb.cropping_systems if item.system_id == strategy.documented_system_id), None)
        if system is None:
            raise KnowledgeBaseError(f"strategy '{strategy.strategy_id}' cites an unknown cropping system")
        if set(system.crops) != set(strategy.crop_sequence):
            raise KnowledgeBaseError(
                f"strategy '{strategy.strategy_id}' does not use the crops of the system it cites"
            )
    for season_id in strategy.slot_seasons:
        config.window(season_id)
    return strategy
