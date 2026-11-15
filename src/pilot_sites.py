"""Pilot site for the NASA data layer (phase A2).

One site is enough to prove the ingestion pipeline. The client itself accepts
any valid coordinates and date range.

The site has not been approved by the participant. It is the proposal made
in phase A2, and everything that depends on it is provisional.

The agricultural context below was rewritten in phase A3 so that every factual
statement rests on a source in the evidence registry
(``data/knowledge/evidence_registry.json``) or on the NASA record itself.
Statements that could not be sourced were removed. No crop data or agronomic
rule lives here.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

from datetime import date

from pydantic import Field, model_validator

from src.models import Contract, GeoLocation, Slug, Text, TimeStandard
from src.nasa_client import DEFAULT_PARAMETERS, PowerRequest


class PilotSite(Contract):
    """A location and historical period used to demonstrate the data layer."""

    site_id: Slug
    name: Text
    location: GeoLocation
    period_start: date
    period_end: date
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS
    time_standard: TimeStandard = TimeStandard.UTC
    approved: bool = Field(
        default=False, description="True only once the participant has approved the site."
    )
    agricultural_context: Text
    context_sources: tuple[Slug, ...] = Field(
        default=(), description="Evidence-registry sources the context rests on."
    )
    context_assumptions: tuple[Text, ...] = Field(
        default=(), description="Steps in the context that are this project's own inference."
    )
    justification: tuple[Text, ...] = Field(min_length=1)
    period_rationale: tuple[Text, ...] = Field(min_length=1)
    representativeness_note: Text
    context_is_cited: bool = Field(
        default=False, description="True when every factual statement in the context is sourced."
    )

    @model_validator(mode="after")
    def _check_period(self) -> "PilotSite":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        if self.context_is_cited and not self.context_sources:
            raise ValueError("a context marked as cited must name its sources")
        return self

    def request(self) -> PowerRequest:
        """The NASA POWER request for this site's documented period."""
        return PowerRequest(
            latitude=self.location.latitude,
            longitude=self.location.longitude,
            start=self.period_start,
            end=self.period_end,
            parameters=self.parameters,
            time_standard=self.time_standard,
        )


KATUMANI = PilotSite(
    site_id="katumani-machakos-ke",
    name="Katumani area, Machakos County, Kenya",
    location=GeoLocation(
        latitude=-1.58,
        longitude=37.24,
        name="Katumani area, Machakos County, Kenya",
        country_code="KE",
    ),
    period_start=date(2001, 1, 1),
    period_end=date(2025, 12, 31),
    approved=False,
    agricultural_context=(
        "Machakos is described in the research literature as semi-arid Kenya. A "
        "cropping-systems experiment at the ICRAF research station at Machakos, from "
        "November 1989 to February 1996, compared maize grown continuously with maize "
        "rotated or intercropped with cowpea and pigeon pea (Rao and Mathuva, 2000). "
        "FAO describes Kenya's marginal bimodal-rainfall south-eastern areas as having "
        "long rains that typically extend from March to May and short rains from October "
        "to December (FAO GIEWS, 2026). The NASA record retrieved for this site shows "
        "the same two wetter periods, centred on April and November."
    ),
    context_sources=("rao-mathuva-2000", "fao-giews-kenya"),
    context_assumptions=(
        "That the pilot site lies within the 'marginal bimodal rainfall southeastern' "
        "areas FAO describes. The FAO brief does not name Machakos; the match with the "
        "NASA rainfall record is the only support for this.",
        "That conditions at the ICRAF station in 1989 to 1996 are relevant to the "
        "Katumani area today.",
    ),
    context_is_cited=True,
    justification=(
        "The two rainy seasons a year seen in the NASA record give several cropping "
        "seasons to compare within one rotation cycle.",
        "Published experimental evidence on legume and maize rotations exists for "
        "Machakos itself (Rao and Mathuva, 2000).",
        "Mean rainfall in the NASA record is about 650 mm a year, split between two "
        "seasons, which is low against the indicative seasonal water needs of maize. "
        "That makes the comparison of dry, typical and wet seasons meaningful here.",
        "Project rationale, not evidence: a tool built on free global data is aimed at "
        "places where local measurements are scarce.",
    ),
    period_rationale=(
        "25 complete calendar years (2001 to 2025) with no partial year.",
        "Starts where NASA POWER's solar record switches to a single product, CERES "
        "SYN1deg (1 Jan 2001), so solar values come from one source throughout.",
        "Ends more than ten months before retrieval, well clear of the recent months "
        "that NASA POWER fills from near-real-time systems and may later revise.",
        "Lies inside the satellite rainfall (GPM IMERG) record, so a second rainfall "
        "source can be compared like for like if it is added later.",
    ),
    representativeness_note=(
        "The values describe NASA grid cells tens of kilometres wide that contain this "
        "point, at each cell's average elevation. Terrain around Machakos varies by "
        "hundreds of metres, so conditions on a particular farm can differ noticeably. "
        "These are not measurements from any individual farm."
    ),
)

PILOT_SITE: PilotSite = KATUMANI
"""The single verified pilot site for phase A2."""
