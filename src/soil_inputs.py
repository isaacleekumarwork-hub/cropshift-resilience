"""Soil inputs and the three soil-dependent mappings (phase A4.2).

Responsibility
    Accept soil information from a farmer (or, later, the A5 interface),
    validate it, keep its provenance, and supply the three soil-dependent
    comparisons that the A3 mapping registry defines:

    =====================================  ============================  ==========================================
    A3 mapping                              Crop value                    Soil input
    =====================================  ============================  ==========================================
    ``soil-ph-requirement-to-soil-ph``      documented pH range           soil pH
    ``rooting-depth-to-soil-water``         maximum rooting depth (m)     available water: field capacity minus
                                                                          wilting point, or available water capacity
    ``depletion-fraction-to-soil-water``    depletion fraction p          the same available water
    =====================================  ============================  ==========================================

    The two soil-water mappings use FAO-56 Chapter 8, Equations 82 and 83,
    re-read in the A4 evidence audit:

    * total available water in the root zone, TAW = 1000 (θFC − θWP) Zr  [mm]
    * readily available water, RAW = p TAW  [mm]

Rules
    * **Soil is never inferred from NASA data.** No function here accepts or
      reads a weather value.
    * **What the user says is recorded as what the user says.** A value the
      user reports as a laboratory measurement keeps that label, but CropShift
      has not seen the laboratory report, so its verification status is "not
      verified" and its evidence kind is "user reported".
    * **Missing stays missing.** An absent input makes the dependent indicators
      unavailable, says what is missing and how a farmer could obtain it, and
      leaves every other indicator untouched. No default soil is inserted.
    * **Typical values are labelled as typical.** If only a texture class is
      known, the FAO-56 Table 19 range for that class is used, labelled as a
      literature reference for a soil type, never as a measurement of the field.
      The garbled silty clay row is refused by the evidence gate.
    * **Hypothetical profiles are allowed only as such.** A demonstration
      profile is flagged throughout, and every result built on it says so.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import Field, model_validator

from src.evidence_audit import EvidenceGate, EvidenceUse, GateDecision
from src.models import (
    Contract,
    CropProfile,
    DataKind,
    GeoLocation,
    ProvenanceRecord,
    ScientificValue,
    SoilDrainageClass,
    SoilInformation,
    SoilTextureClass,
    Text,
    Unit,
    _today,
    get_variable,
)

USER_SOURCE_ID = "user-soil-input"

# Plausibility screens. Values outside them are accepted with a warning, because
# a real field can be unusual; values outside physical limits are rejected.
PH_DOCUMENTED_SPAN = (4.0, 9.0)
"""The widest span covered by any crop pH range in the knowledge base."""

AVAILABLE_WATER_TABLE_SPAN = (0.05, 0.20)
"""Lowest and highest available water (m3/m3) in FAO-56 Table 19, all classes."""

FIELD_CAPACITY_TABLE_SPAN = (0.07, 0.42)
WILTING_POINT_TABLE_SPAN = (0.02, 0.29)
WATER_CONSISTENCY_TOLERANCE_MM_PER_M = 10.0
"""Allowed difference between a stated available water capacity and 1000 (θFC − θWP)."""


class SoilSourceClass(StrEnum):
    """Where the user says a soil value comes from. Never interchangeable."""

    USER_REPORTED = "user_reported"  # the farmer's own knowledge or observation
    LAB_MEASURED = "lab_measured"  # the user reports a laboratory measurement
    PUBLIC_SOIL_DATASET = "public_soil_dataset"  # the user read it from a public soil map or dataset
    PROVISIONAL_ASSUMPTION = "provisional_assumption"  # a hypothetical value for a demonstration
    UNKNOWN = "unknown"  # not provided


class SoilVerificationStatus(StrEnum):
    NOT_VERIFIED = "not_verified"  # supplied by the user; CropShift has not checked it
    LITERATURE_REFERENCE = "literature_reference"  # a typical value for a soil type, not this field
    DERIVED_FROM_INPUTS = "derived_from_inputs"  # calculated from other supplied values
    HYPOTHETICAL = "hypothetical"  # a demonstration value; never a real field
    NOT_PROVIDED = "not_provided"


class SoilWaterBasis(StrEnum):
    AVAILABLE_WATER_CAPACITY = "available_water_capacity"  # stated directly, mm/m
    FIELD_CAPACITY_AND_WILTING_POINT = "field_capacity_and_wilting_point"  # θFC − θWP
    TEXTURE_CLASS_REFERENCE = "texture_class_reference"  # FAO-56 Table 19 range for the class


# --------------------------------------------------------------------------- #
# Input models: what A5 submits
# --------------------------------------------------------------------------- #


class SoilEntrySource(Contract):
    """Who or what supplied one soil entry, as the user states it."""

    source_class: SoilSourceClass
    source_identifier: Text | None = Field(
        default=None, description="Laboratory, report number, map or dataset name, if known."
    )
    collected_on: date | None = Field(default=None, description="Sampling, test or entry date, if known.")
    applies_to: Text | None = Field(
        default=None, description="Where the value applies, for example 'north field, top 30 cm'."
    )
    note: Text | None = None

    @model_validator(mode="after")
    def _check_source(self) -> "SoilEntrySource":
        if self.source_class is SoilSourceClass.UNKNOWN:
            raise ValueError("a value with an unknown source cannot be entered; leave the field empty instead")
        if self.source_class is SoilSourceClass.PUBLIC_SOIL_DATASET and self.source_identifier is None:
            raise ValueError("a value from a public soil dataset must name the dataset")
        if self.collected_on is not None and self.collected_on > _today():
            raise ValueError("a soil sample or entry date cannot be in the future")
        return self


class SoilValueInput(SoilEntrySource):
    """One numeric soil value as entered."""

    value: float


class SoilTextureInput(SoilEntrySource):
    texture_class: SoilTextureClass


class SoilDrainageInput(SoilEntrySource):
    drainage_class: SoilDrainageClass


class SoilProfileInput(Contract):
    """Soil information for one field. Every item is optional; absence stays absence.

    Units: pH in pH units; field capacity and wilting point as volumetric water
    content (m3/m3, for example 0.30); available water capacity in millimetres
    of water per metre of soil depth.
    """

    label: Text | None = None
    depth_top_cm: float = Field(default=0, ge=0, le=2000)
    depth_bottom_cm: float = Field(default=30, gt=0, le=2000)
    soil_ph: SoilValueInput | None = None
    texture: SoilTextureInput | None = None
    field_capacity: SoilValueInput | None = None
    wilting_point: SoilValueInput | None = None
    available_water_capacity: SoilValueInput | None = None
    drainage: SoilDrainageInput | None = None
    hypothetical: bool = Field(
        default=False, description="True for a demonstration profile that describes no real field."
    )

    @model_validator(mode="after")
    def _check_profile(self) -> "SoilProfileInput":
        if self.depth_bottom_cm <= self.depth_top_cm:
            raise ValueError("depth_bottom_cm must be greater than depth_top_cm")
        entries = self.entries()
        if self.hypothetical:
            for name, entry in entries:
                if entry.source_class is not SoilSourceClass.PROVISIONAL_ASSUMPTION:
                    raise ValueError(f"every value in a hypothetical profile must be a provisional assumption ({name})")
        else:
            for name, entry in entries:
                if entry.source_class is SoilSourceClass.PROVISIONAL_ASSUMPTION:
                    raise ValueError(
                        f"'{name}' is a provisional assumption; mark the whole profile as hypothetical"
                    )
        if (self.field_capacity is None) != (self.wilting_point is None):
            raise ValueError("give field capacity and wilting point together, or neither")
        for name, item, variable in (
            ("soil_ph", self.soil_ph, "soil_ph"),
            ("field_capacity", self.field_capacity, "soil_field_capacity"),
            ("wilting_point", self.wilting_point, "soil_wilting_point"),
            ("available_water_capacity", self.available_water_capacity, "soil_available_water_capacity"),
        ):
            if item is None:
                continue
            definition = get_variable(variable)
            if definition.valid_min is not None and item.value < definition.valid_min:
                raise ValueError(f"{name} {item.value:g} is below the physical minimum {definition.valid_min:g}")
            if definition.valid_max is not None and item.value > definition.valid_max:
                raise ValueError(f"{name} {item.value:g} is above the physical maximum {definition.valid_max:g}")
        if self.field_capacity is not None and self.wilting_point is not None:
            if self.field_capacity.value <= self.wilting_point.value:
                raise ValueError("field capacity must be greater than the wilting point")
            if self.available_water_capacity is not None:
                derived = 1000 * (self.field_capacity.value - self.wilting_point.value)
                if abs(derived - self.available_water_capacity.value) > WATER_CONSISTENCY_TOLERANCE_MM_PER_M:
                    raise ValueError(
                        f"available water capacity {self.available_water_capacity.value:g} mm/m contradicts "
                        f"field capacity minus wilting point ({derived:g} mm/m); enter one or the other"
                    )
        return self

    def entries(self) -> tuple[tuple[str, SoilEntrySource], ...]:
        return tuple(
            (name, item)
            for name, item in (
                ("soil_ph", self.soil_ph),
                ("texture", self.texture),
                ("field_capacity", self.field_capacity),
                ("wilting_point", self.wilting_point),
                ("available_water_capacity", self.available_water_capacity),
                ("drainage", self.drainage),
            )
            if item is not None
        )


def demonstration_soil_profile() -> SoilProfileInput:
    """A hypothetical profile for showing the tool. It describes no real field.

    The values are invented for demonstration and are not Katumani soil data.
    Loam is used because FAO-56 Table 19 gives reference values for it.
    """
    entry = dict(
        source_class=SoilSourceClass.PROVISIONAL_ASSUMPTION,
        note="Invented for a demonstration; not a measurement of any field.",
    )
    return SoilProfileInput(
        label="Hypothetical demonstration soil (not real data)",
        soil_ph=SoilValueInput(value=6.5, **entry),
        texture=SoilTextureInput(texture_class=SoilTextureClass.LOAM, **entry),
        drainage=SoilDrainageInput(drainage_class=SoilDrainageClass.WELL_DRAINED, **entry),
        hypothetical=True,
    )


# --------------------------------------------------------------------------- #
# Resolved soil: values with provenance, and what is missing
# --------------------------------------------------------------------------- #


class SoilValueRecord(Contract):
    """One soil item as the engine will use it, with everything needed to judge it."""

    variable: Text
    value: float | None = None
    category: Text | None = Field(default=None, description="For texture and drainage classes.")
    unit: Unit | None = None
    source_class: SoilSourceClass
    source_identifier: Text | None = None
    applies_to: Text
    collected_on: date | None = None
    verification: SoilVerificationStatus
    limitations: tuple[Text, ...] = Field(min_length=1)
    warnings: tuple[Text, ...] = ()
    provenance: ProvenanceRecord


class MissingSoilItem(Contract):
    variable: Text
    needed_for: tuple[Text, ...] = Field(min_length=1, description="Mapping identifiers that need it.")
    explanation: Text
    how_to_obtain: Text


class SoilWater(Contract):
    """Plant-available water per unit soil volume, as a range, with its basis."""

    available_water_min: float = Field(ge=0, le=1, description="θFC − θWP, m3/m3")
    available_water_max: float = Field(ge=0, le=1)
    basis: SoilWaterBasis
    source_class: SoilSourceClass
    verification: SoilVerificationStatus
    provenance: ProvenanceRecord
    gate: GateDecision | None = Field(default=None, description="Set when a literature reference was used.")
    limitations: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_range(self) -> "SoilWater":
        if self.available_water_min > self.available_water_max:
            raise ValueError("available_water_min must not exceed available_water_max")
        return self


class ResolvedSoil(Contract):
    """Validated soil information, ready for the comparison engine."""

    label: Text | None
    hypothetical: bool
    records: tuple[SoilValueRecord, ...] = ()
    water: SoilWater | None = None
    missing: tuple[MissingSoilItem, ...] = ()
    information: SoilInformation | None = Field(
        default=None, description="The same values in the A1 soil contract, for export."
    )

    def get(self, variable: str) -> SoilValueRecord | None:
        return next((item for item in self.records if item.variable == variable), None)

    @property
    def ph(self) -> float | None:
        record = self.get("soil_ph")
        return record.value if record else None

    @property
    def drainage(self) -> SoilDrainageClass | None:
        record = self.get("drainage_class")
        return SoilDrainageClass(record.category) if record and record.category else None

    def missing_for(self, mapping_id: str) -> tuple[MissingSoilItem, ...]:
        return tuple(item for item in self.missing if mapping_id in item.needed_for)


_PH_MAPPING = "soil-ph-requirement-to-soil-ph"
_WATER_MAPPINGS = ("rooting-depth-to-soil-water", "depletion-fraction-to-soil-water")

_HOW_TO = {
    "soil_ph": (
        "Soil pH is needed to compare the field with each crop's documented pH range.",
        "A soil test from a soil-testing laboratory or the local agricultural extension service reports pH.",
    ),
    "soil_water": (
        "How much water the soil holds is needed to estimate the water each crop's roots can reach.",
        "A soil laboratory can measure field capacity and wilting point. If only the soil texture class "
        "is known (for example from a soil test), typical values for that class are used instead.",
    ),
    "drainage_class": (
        "Drainage is needed to flag crops that the sources describe as sensitive to waterlogging.",
        "Describe how quickly water drains from the field after heavy rain (well, moderately or poorly drained).",
    ),
}

_VERIFICATION = {
    SoilSourceClass.USER_REPORTED: SoilVerificationStatus.NOT_VERIFIED,
    SoilSourceClass.LAB_MEASURED: SoilVerificationStatus.NOT_VERIFIED,
    SoilSourceClass.PUBLIC_SOIL_DATASET: SoilVerificationStatus.NOT_VERIFIED,
    SoilSourceClass.PROVISIONAL_ASSUMPTION: SoilVerificationStatus.HYPOTHETICAL,
}

_CLASS_LIMITATION = {
    SoilSourceClass.USER_REPORTED: "Reported by the user; not measured or checked by CropShift.",
    SoilSourceClass.LAB_MEASURED: (
        "The user reports a laboratory measurement. CropShift has not seen the laboratory report, "
        "so the value is not independently verified."
    ),
    SoilSourceClass.PUBLIC_SOIL_DATASET: (
        "Read by the user from a public soil dataset. Mapped soil values are estimates for an area "
        "and can differ from the field."
    ),
    SoilSourceClass.PROVISIONAL_ASSUMPTION: "Hypothetical value for a demonstration. It describes no real field.",
}


def _provenance(entry: SoilEntrySource, label: str) -> ProvenanceRecord:
    if entry.source_class is SoilSourceClass.PROVISIONAL_ASSUMPTION:
        return ProvenanceRecord(
            kind=DataKind.ASSUMED,
            source_id=USER_SOURCE_ID,
            source_name="Hypothetical demonstration value",
            assumption=f"{label}: invented for a demonstration; not a measurement of any field.",
        )
    stated = entry.source_class.value.replace("_", " ")
    return ProvenanceRecord(
        kind=DataKind.USER_REPORTED,
        source_id=USER_SOURCE_ID,
        source_name=f"Entered by the user (stated source: {stated})",
        source_version=entry.source_identifier,
    )


def _record(
    entry: SoilEntrySource,
    variable: str,
    *,
    value: float | None = None,
    category: str | None = None,
    unit: Unit | None = None,
    warnings: tuple[str, ...] = (),
    depth: str,
) -> SoilValueRecord:
    return SoilValueRecord(
        variable=variable,
        value=value,
        category=category,
        unit=unit,
        source_class=entry.source_class,
        source_identifier=entry.source_identifier,
        applies_to=entry.applies_to or f"The field described by the user, {depth}.",
        collected_on=entry.collected_on,
        verification=_VERIFICATION[entry.source_class],
        limitations=(_CLASS_LIMITATION[entry.source_class],),
        warnings=warnings,
        provenance=_provenance(entry, variable),
    )


def _outside(value: float, span: tuple[float, float], what: str) -> tuple[str, ...]:
    low, high = span
    if low <= value <= high:
        return ()
    return (f"{value:g} lies outside {what} ({low:g} to {high:g}). Please check the value.",)


def resolve_soil(
    profile: SoilProfileInput | None,
    *,
    location: GeoLocation,
    gate: EvidenceGate,
) -> ResolvedSoil:
    """Validate soil inputs and resolve the soil water basis. Never invents a value."""
    if profile is None:
        profile = SoilProfileInput()
    depth = f"{profile.depth_top_cm:g} to {profile.depth_bottom_cm:g} cm"
    records: list[SoilValueRecord] = []
    missing: list[MissingSoilItem] = []

    if profile.soil_ph is not None:
        records.append(
            _record(
                profile.soil_ph, "soil_ph", value=profile.soil_ph.value, unit=Unit.PH, depth=depth,
                warnings=_outside(profile.soil_ph.value, PH_DOCUMENTED_SPAN, "the span of every crop pH range held"),
            )
        )
    else:
        explanation, how = _HOW_TO["soil_ph"]
        missing.append(MissingSoilItem(variable="soil_ph", needed_for=(_PH_MAPPING,), explanation=explanation, how_to_obtain=how))

    if profile.texture is not None:
        records.append(
            _record(profile.texture, "texture_class", category=profile.texture.texture_class.value, depth=depth)
        )
    if profile.field_capacity is not None and profile.wilting_point is not None:
        records.append(
            _record(
                profile.field_capacity, "soil_field_capacity", value=profile.field_capacity.value,
                unit=Unit.CUBIC_METRE_PER_CUBIC_METRE, depth=depth,
                warnings=_outside(profile.field_capacity.value, FIELD_CAPACITY_TABLE_SPAN, "the FAO-56 Table 19 range"),
            )
        )
        records.append(
            _record(
                profile.wilting_point, "soil_wilting_point", value=profile.wilting_point.value,
                unit=Unit.CUBIC_METRE_PER_CUBIC_METRE, depth=depth,
                warnings=_outside(profile.wilting_point.value, WILTING_POINT_TABLE_SPAN, "the FAO-56 Table 19 range"),
            )
        )
    if profile.available_water_capacity is not None:
        records.append(
            _record(
                profile.available_water_capacity, "soil_available_water_capacity",
                value=profile.available_water_capacity.value, unit=Unit.MILLIMETRE_PER_METRE, depth=depth,
                warnings=_outside(
                    profile.available_water_capacity.value / 1000, AVAILABLE_WATER_TABLE_SPAN,
                    "the FAO-56 Table 19 range in m3/m3",
                ),
            )
        )
    if profile.drainage is not None:
        records.append(
            _record(profile.drainage, "drainage_class", category=profile.drainage.drainage_class.value, depth=depth)
        )
    else:
        explanation, how = _HOW_TO["drainage_class"]
        missing.append(
            MissingSoilItem(
                variable="drainage_class", needed_for=("waterlogging-sensitive-crop-on-wet-soil",),
                explanation=explanation, how_to_obtain=how,
            )
        )

    water, water_missing = _resolve_water(profile, gate)
    if water_missing is not None:
        missing.append(water_missing)

    return ResolvedSoil(
        label=profile.label,
        hypothetical=profile.hypothetical,
        records=tuple(records),
        water=water,
        missing=tuple(missing),
        information=_as_information(profile, location),
    )


def _resolve_water(profile: SoilProfileInput, gate: EvidenceGate) -> tuple[SoilWater | None, MissingSoilItem | None]:
    common_limits = (
        "Assumes the soil holds water the same way through the whole root zone, although the values "
        f"describe {profile.depth_top_cm:g} to {profile.depth_bottom_cm:g} cm.",
        "Published rooting depths assume no layer that stops roots; the depth of soil at the field is not known.",
    )
    if profile.available_water_capacity is not None:
        entry = profile.available_water_capacity
        share = entry.value / 1000
        return (
            SoilWater(
                available_water_min=share, available_water_max=share,
                basis=SoilWaterBasis.AVAILABLE_WATER_CAPACITY, source_class=entry.source_class,
                verification=_VERIFICATION[entry.source_class], provenance=_provenance(entry, "available water capacity"),
                limitations=(_CLASS_LIMITATION[entry.source_class], *common_limits),
            ),
            None,
        )
    if profile.field_capacity is not None and profile.wilting_point is not None:
        entry = profile.field_capacity
        share = round(profile.field_capacity.value - profile.wilting_point.value, 6)
        hypothetical = entry.source_class is SoilSourceClass.PROVISIONAL_ASSUMPTION
        return (
            SoilWater(
                available_water_min=share, available_water_max=share,
                basis=SoilWaterBasis.FIELD_CAPACITY_AND_WILTING_POINT, source_class=entry.source_class,
                verification=SoilVerificationStatus.HYPOTHETICAL if hypothetical else SoilVerificationStatus.DERIVED_FROM_INPUTS,
                provenance=ProvenanceRecord(
                    kind=DataKind.ASSUMED if hypothetical else DataKind.DERIVED,
                    source_id=USER_SOURCE_ID,
                    source_name="Calculated from the user's field capacity and wilting point",
                    assumption="Hypothetical demonstration values." if hypothetical else None,
                    transformations=("θFC − θWP, as in FAO-56 Equation 82",),
                ),
                limitations=(_CLASS_LIMITATION[entry.source_class], *common_limits),
            ),
            None,
        )
    explanation, how = _HOW_TO["soil_water"]
    if profile.texture is None:
        return None, MissingSoilItem(
            variable="soil_water", needed_for=_WATER_MAPPINGS, explanation=explanation, how_to_obtain=how
        )
    texture = profile.texture.texture_class
    reference = gate.kb.soil_reference(texture)
    if reference is None:
        return None, MissingSoilItem(
            variable="soil_water", needed_for=_WATER_MAPPINGS,
            explanation=(
                f"FAO-56 Table 19 gives no reference values for {texture.value.replace('_', ' ')}, "
                "so the soil water held cannot be estimated from the texture class alone."
            ),
            how_to_obtain=how,
        )
    decision = gate.check(f"soil_reference:{texture.value}", reference.provenance, EvidenceUse.NUMERIC_INPUT)
    if not decision.admitted:
        return None, MissingSoilItem(
            variable="soil_water", needed_for=_WATER_MAPPINGS,
            explanation=f"The reference values for {texture.value.replace('_', ' ')} cannot be used. {decision.reason}",
            how_to_obtain="A soil laboratory can measure field capacity and wilting point for this field.",
        )
    return (
        SoilWater(
            available_water_min=reference.available_water_min,
            available_water_max=reference.available_water_max,
            basis=SoilWaterBasis.TEXTURE_CLASS_REFERENCE,
            source_class=profile.texture.source_class,
            verification=(
                SoilVerificationStatus.HYPOTHETICAL
                if profile.hypothetical
                else SoilVerificationStatus.LITERATURE_REFERENCE
            ),
            provenance=reference.provenance,
            gate=decision,
            limitations=(
                "Typical values for the texture class from FAO-56 Table 19, not a measurement of this field.",
                f"The texture class itself: {_CLASS_LIMITATION[profile.texture.source_class]}",
                *common_limits,
            ),
        ),
        None,
    )


def _as_information(profile: SoilProfileInput, location: GeoLocation) -> SoilInformation | None:
    """The same inputs as an A1 ``SoilInformation`` record, for export and provenance."""
    if not profile.entries():
        return None
    properties = []
    for entry, variable in (
        (profile.soil_ph, "soil_ph"),
        (profile.field_capacity, "soil_field_capacity"),
        (profile.wilting_point, "soil_wilting_point"),
        (profile.available_water_capacity, "soil_available_water_capacity"),
    ):
        if entry is not None:
            properties.append(
                ScientificValue(
                    variable=variable,
                    value=entry.value,
                    unit=get_variable(variable).unit,
                    provenance=_provenance(entry, variable),
                )
            )
    return SoilInformation(
        location=location,
        depth_top_cm=profile.depth_top_cm,
        depth_bottom_cm=profile.depth_bottom_cm,
        texture_class=profile.texture.texture_class if profile.texture else None,
        texture_provenance=_provenance(profile.texture, "texture") if profile.texture else None,
        drainage_class=profile.drainage.drainage_class if profile.drainage else None,
        drainage_provenance=_provenance(profile.drainage, "drainage") if profile.drainage else None,
        properties=tuple(properties),
        notes=profile.label,
    )


# --------------------------------------------------------------------------- #
# Soil compatibility: the three mappings, per crop
# --------------------------------------------------------------------------- #


class PhComparison(Contract):
    requirement_id: Text
    basis: Text
    minimum: float | None
    maximum: float | None
    position: Text = Field(description="'inside', 'below' or 'above' the documented range.")
    decision: GateDecision


class RootZoneWater(Contract):
    """FAO-56 Equations 82 and 83 for one crop, as ranges."""

    rooting_depth_min_m: float
    rooting_depth_max_m: float
    taw_min_mm: float
    taw_max_mm: float
    depletion_fraction: float | None = None
    raw_min_mm: float | None = None
    raw_max_mm: float | None = None
    rooting_decision: GateDecision
    depletion_decision: GateDecision | None = None


def compare_ph(crop: CropProfile, soil: ResolvedSoil, gate: EvidenceGate) -> tuple[tuple[PhComparison, ...], tuple[str, ...]]:
    """Soil pH against each admitted pH range of the crop. Returns comparisons and reasons for gaps."""
    ph = soil.ph
    admitted, refused = gate.admitted_requirements(crop, "crop_soil_ph_requirement")
    gaps = [f"{item.requirement_id}: {decision.reason}" for item, decision in refused]
    if not admitted:
        gaps.append(f"No documented soil pH range is held for {crop.common_name.lower()}.")
    if ph is None:
        return (), tuple(gaps)
    results = []
    for requirement, decision in admitted:
        if requirement.minimum is not None and ph < requirement.minimum:
            position = "below"
        elif requirement.maximum is not None and ph > requirement.maximum:
            position = "above"
        else:
            position = "inside"
        results.append(
            PhComparison(
                requirement_id=requirement.requirement_id, basis=requirement.basis.value,
                minimum=requirement.minimum, maximum=requirement.maximum, position=position, decision=decision,
            )
        )
    return tuple(results), tuple(gaps)


def root_zone_water(crop: CropProfile, soil: ResolvedSoil, gate: EvidenceGate) -> tuple[RootZoneWater | None, tuple[str, ...]]:
    """Total and readily available water in the crop's root zone (FAO-56 Eq. 82 and 83)."""
    gaps: list[str] = []
    if soil.water is None:
        gaps.append("No soil water information was supplied.")
    rooting, refused = gate.admitted_requirements(crop, "crop_max_rooting_depth")
    gaps.extend(f"{item.requirement_id}: {decision.reason}" for item, decision in refused)
    if not rooting:
        gaps.append(f"No documented rooting depth is held for {crop.common_name.lower()}.")
    if soil.water is None or not rooting:
        return None, tuple(gaps)
    requirement, rooting_decision = rooting[0]
    zr_min = requirement.minimum if requirement.minimum is not None else requirement.maximum
    zr_max = requirement.maximum if requirement.maximum is not None else requirement.minimum
    taw_min = round(1000 * soil.water.available_water_min * zr_min, 1)  # type: ignore[operator]
    taw_max = round(1000 * soil.water.available_water_max * zr_max, 1)  # type: ignore[operator]

    depletion, refused_p = gate.admitted_requirements(crop, "crop_depletion_fraction")
    gaps.extend(f"{item.requirement_id}: {decision.reason}" for item, decision in refused_p)
    p = raw_min = raw_max = None
    depletion_decision = None
    if depletion:
        p_requirement, depletion_decision = depletion[0]
        p = p_requirement.minimum
        raw_min, raw_max = round(p * taw_min, 1), round(p * taw_max, 1)  # type: ignore[operator]
    else:
        gaps.append(
            f"No documented depletion fraction is held for {crop.common_name.lower()}, "
            "so readily available water cannot be calculated."
        )
    return (
        RootZoneWater(
            rooting_depth_min_m=zr_min, rooting_depth_max_m=zr_max,  # type: ignore[arg-type]
            taw_min_mm=taw_min, taw_max_mm=taw_max,
            depletion_fraction=p, raw_min_mm=raw_min, raw_max_mm=raw_max,
            rooting_decision=rooting_decision, depletion_decision=depletion_decision,
        ),
        tuple(gaps),
    )
