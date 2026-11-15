"""Interface state helpers (phase A5).

Responsibility
    Turn the raw values of the interface's widgets into the typed inputs the
    A4 engine accepts, and back. Page code reads selections through
    ``read_selections`` instead of raw session keys. Nothing here imports
    Streamlit: every function takes a plain mapping, so it can be tested on
    its own.

Rules
    * A soil field left empty stays missing. No default is inserted.
    * Invalid soil inputs are reported as plain messages and never reach the
      engine; the previous valid profile is not silently reused.
    * Priorities keep the order the farmer chose them in. There are no weights.
    * Nothing the user enters is written to disk.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import ValidationError

from src.comparison_engine import PrioritySelection
from src.models import PriorityDimension, ScenarioCategory, SoilDrainageClass, SoilTextureClass
from src.soil_inputs import (
    SoilDrainageInput,
    SoilProfileInput,
    SoilSourceClass,
    SoilTextureInput,
    SoilValueInput,
    demonstration_soil_profile,
)

# Session keys. Page code uses these names only through this module.
WINDOW_KEY = "season_window"
CATEGORY_KEY = "season_category"
PRIORITIES_KEY = "farmer_priorities"
SOIL_MODE_KEY = "soil_mode"
ENTERED_SOIL_KEY = "entered_soil_profile"
SOIL_ERRORS_KEY = "soil_errors"

SOIL_MODE_NONE = "none"
SOIL_MODE_ENTERED = "entered"
SOIL_MODE_DEMO = "demonstration"
SOIL_MODE_LABELS = {
    SOIL_MODE_NONE: "No soil information (default)",
    SOIL_MODE_ENTERED: "Enter my soil information",
    SOIL_MODE_DEMO: "Illustrative soil profile (not measured at Katumani)",
}

ALL_SEASONS = "all"
CATEGORY_CHOICES = (ALL_SEASONS, *(item.value for item in ScenarioCategory))
CATEGORY_LABELS = {ALL_SEASONS: "All past seasons", "dry": "Dry seasons", "typical": "Typical seasons", "wet": "Wet seasons"}

SOURCE_LABELS = {
    SoilSourceClass.USER_REPORTED.value: "My own knowledge or observation",
    SoilSourceClass.LAB_MEASURED.value: "A laboratory soil test (I have the report)",
    SoilSourceClass.PUBLIC_SOIL_DATASET.value: "A public soil map or dataset (name it below)",
}
NOT_KNOWN = "not_known"
WATER_BASIS_LABELS = {
    NOT_KNOWN: "Not known",
    "texture": "I know the soil texture class",
    "fc_wp": "I know field capacity and wilting point",
    "awc": "I know the available water capacity",
}
TEXTURE_LABELS = {item.value: item.value.replace("_", " ").capitalize() for item in SoilTextureClass}
DRAINAGE_LABELS = {NOT_KNOWN: "Not known", **{item.value: item.value.replace("_", " ").capitalize() for item in SoilDrainageClass}}


@dataclass(frozen=True)
class Selections:
    """Everything the user has chosen, as typed values."""

    window_id: str
    category: ScenarioCategory | None
    priorities: tuple[PriorityDimension, ...]
    soil_mode: str
    soil: SoilProfileInput | None

    @property
    def priority_selection(self) -> PrioritySelection | None:
        return PrioritySelection(dimensions=self.priorities) if self.priorities else None

    def cache_key(self) -> tuple[str, tuple[str, ...]]:
        """What the comparison result depends on (soil and priorities, not the display filters)."""
        soil = self.soil.model_dump_json() if self.soil is not None else "no-soil"
        return soil, tuple(item.value for item in self.priorities)


def read_selections(state: Mapping[str, Any], *, window_ids: Sequence[str]) -> Selections:
    """Read the user's choices from session state, with safe defaults for anything unset."""
    window_id = state.get(WINDOW_KEY) or window_ids[0]
    if window_id not in window_ids:
        window_id = window_ids[0]
    raw_category = state.get(CATEGORY_KEY) or ALL_SEASONS
    category = None if raw_category == ALL_SEASONS else ScenarioCategory(raw_category)
    priorities = tuple(PriorityDimension(item) for item in state.get(PRIORITIES_KEY) or ())
    mode = state.get(SOIL_MODE_KEY) or SOIL_MODE_NONE
    if mode == SOIL_MODE_DEMO:
        soil = demonstration_soil_profile()
    elif mode == SOIL_MODE_ENTERED:
        soil = state.get(ENTERED_SOIL_KEY)
    else:
        soil = None
    return Selections(window_id=window_id, category=category, priorities=priorities, soil_mode=mode, soil=soil)


def _number(values: Mapping[str, Any], key: str) -> float | None:
    value = values.get(key)
    return None if value is None else float(value)


def _source(values: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    source_class = values.get(f"{prefix}_source") or SoilSourceClass.USER_REPORTED.value
    identifier = (values.get("source_identifier") or "").strip() or None
    sampled = values.get("collected_on")
    return {
        "source_class": source_class,
        "source_identifier": identifier,
        "collected_on": sampled if isinstance(sampled, date) else None,
        "applies_to": (values.get("applies_to") or "").strip() or None,
    }


def friendly_errors(error: ValidationError) -> list[str]:
    """Validation errors as sentences a farmer can act on, without internal detail."""
    messages = []
    for item in error.errors():
        message = str(item.get("msg", "")).removeprefix("Value error, ")
        location = ".".join(str(part) for part in item.get("loc", ()) if not isinstance(part, int))
        messages.append(f"{location.replace('_', ' ')}: {message}" if location else message)
    return messages


def soil_form_to_profile(values: Mapping[str, Any]) -> tuple[SoilProfileInput | None, list[str]]:
    """Build a validated soil profile from the soil form. Empty fields stay empty.

    Returns the profile (or None when nothing was entered) and a list of
    problems. When there are problems the profile is None: an invalid entry
    never reaches the engine.
    """
    fields: dict[str, Any] = {}
    try:
        ph = _number(values, "ph")
        if ph is not None:
            fields["soil_ph"] = SoilValueInput(value=ph, **_source(values, "ph"))

        basis = values.get("water_basis") or NOT_KNOWN
        if basis == "texture":
            texture = values.get("texture")
            if not texture:
                return None, ["Choose a texture class, or set soil water to 'Not known'."]
            fields["texture"] = SoilTextureInput(texture_class=texture, **_source(values, "water"))
        elif basis == "fc_wp":
            capacity, wilting = _number(values, "field_capacity"), _number(values, "wilting_point")
            if capacity is None or wilting is None:
                return None, ["Enter both field capacity and wilting point, or choose another option for soil water."]
            fields["field_capacity"] = SoilValueInput(value=capacity, **_source(values, "water"))
            fields["wilting_point"] = SoilValueInput(value=wilting, **_source(values, "water"))
        elif basis == "awc":
            capacity = _number(values, "available_water_capacity")
            if capacity is None:
                return None, ["Enter the available water capacity, or choose another option for soil water."]
            fields["available_water_capacity"] = SoilValueInput(value=capacity, **_source(values, "water"))

        drainage = values.get("drainage") or NOT_KNOWN
        if drainage != NOT_KNOWN:
            fields["drainage"] = SoilDrainageInput(drainage_class=drainage, **_source(values, "drainage"))

        if not fields:
            return None, []
        top, bottom = _number(values, "depth_top_cm"), _number(values, "depth_bottom_cm")
        if top is not None:
            fields["depth_top_cm"] = top
        if bottom is not None:
            fields["depth_bottom_cm"] = bottom
        label = (values.get("applies_to") or "").strip() or "Soil information entered by the user"
        return SoilProfileInput(label=label, **fields), []
    except ValidationError as error:
        return None, friendly_errors(error)
