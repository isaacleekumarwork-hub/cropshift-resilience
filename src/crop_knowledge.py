"""Evidence-based agronomic knowledge base (phase A3).

Responsibility
    Load the version-controlled knowledge files in ``data/knowledge``,
    validate them, and hand typed, cited records to later phases. Nothing here
    compares a crop with the weather, ranks a rotation or recommends anything;
    that is phase A4.

What the knowledge base contains
    * an evidence registry: every source, how it was verified and its limits
    * crop profiles: sourced requirements, qualitative attributes, regional
      evidence, and an explicit list of what is not known
    * growth-stage examples and soil-water reference values by texture class
    * rotation relationships, the constraints derived from them, and the cropping
      systems that a cited study actually compared
    * farmer-priority definitions and what evidence each would need
    * mappings from crop requirements to NASA observations and soil inputs,
      as interface contracts for A4

Rules enforced on load
    * Every claim cites a registered source, says where in it, and carries a
      confidence classification.
    * A claim marked "directly supported" must rest on a source whose content
      was actually read.
    * A hard constraint needs directly supporting evidence; a relationship
      with no adequate source must be labelled unsupported.
    * A crop marked as nitrogen-fixing needs a cited statement saying so.
    * Unknown values are listed as unknown. They are never filled in.

The knowledge base works offline: it reads local files only, and no LLM or
external service is involved in building or loading it.

AI assistance: drafted with Claude Code (Anthropic). The facts in the data
files were read from the cited sources during the hackathon; see
docs/evidence_registry.md.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, Annotated, Literal

from pydantic import Field, StringConstraints, ValidationError, model_validator

from src.config import PROJECT_ROOT
from src.models import (
    Contract,
    CropProfile,
    DataKind,
    EvidenceConfidence,
    Explanation,
    KnowledgeStatus,
    PriorityDimension,
    ProvenanceRecord,
    Slug,
    SoilTextureClass,
    Text,
    Unit,
    VariableDomain,
    _require_cited,
    _require_unique,
    _today,
    get_variable,
)

SCHEMA_VERSION = 1
KNOWLEDGE_DIRECTORY: Path = PROJECT_ROOT / "data" / "knowledge"
MANIFEST_FILE = "manifest.json"


class KnowledgeBaseError(Exception):
    """The knowledge files are missing, malformed or make an unsupported claim."""


# --------------------------------------------------------------------------- #
# Evidence registry
# --------------------------------------------------------------------------- #


class SourceType(StrEnum):
    FAO_PUBLICATION = "fao_publication"
    FAO_WEB_RESOURCE = "fao_web_resource"
    PEER_REVIEWED_ARTICLE = "peer_reviewed_article"
    COMPILED_DATASHEET = "compiled_datasheet"  # a secondary compilation citing primary sources
    METHODOLOGY_REFERENCE = "methodology_reference"  # definitions of a method, not agronomic facts (A4)


class ReviewStatus(StrEnum):
    """How much of a source was actually read when the knowledge base was compiled."""

    CONTENT_READ = "content_read"  # the cited tables or passages were read
    ABSTRACT_READ = "abstract_read"  # only the published abstract was read
    METADATA_ONLY = "metadata_only"  # existence confirmed, content not read
    NOT_VERIFIED = "not_verified"


READ_STATUSES = frozenset({ReviewStatus.CONTENT_READ, ReviewStatus.ABSTRACT_READ})


class EvidenceSource(Contract):
    """One identifiable source and what is known about its reliability and reach."""

    source_id: Slug
    title: Text
    authors: tuple[Text, ...] = ()
    institution: Text
    year: int | None = Field(default=None, ge=1900, le=2100)
    source_type: SourceType
    url: Annotated[str, StringConstraints(pattern=r"^https://\S+$")]
    doi: Annotated[str, StringConstraints(pattern=r"^10\.\d{4,9}/\S+$")] | None = None
    citation: Text = Field(description="Full citation, ready for the References field.")
    accessed_on: date
    sections_read: tuple[Text, ...] = Field(description="Exactly which parts were read.")
    geographic_scope: Text
    crop_scope: Text
    review_status: ReviewStatus
    verification_note: Text = Field(description="How the source and its details were checked.")
    limitations: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_source(self) -> "EvidenceSource":
        if self.accessed_on > _today():
            raise ValueError("accessed_on cannot be in the future")
        if self.review_status in READ_STATUSES and not self.sections_read:
            raise ValueError("a source marked as read must list the sections that were read")
        return self


# --------------------------------------------------------------------------- #
# Families, growth stages and soil reference values
# --------------------------------------------------------------------------- #


class BotanicalFamily(Contract):
    """A plant family, as named by a cited taxonomic statement."""

    family_id: Slug
    name: Text
    alternative_names: tuple[Text, ...] = ()
    evidence: tuple[ProvenanceRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_family(self) -> "BotanicalFamily":
        for record in self.evidence:
            _require_cited(record, f"family '{self.name}'")
        return self


class GrowthStageExample(Contract):
    """Published lengths of the four growth stages for one crop in one region.

    These are examples for the region and planting period the source names.
    They are not local values for the pilot site.
    """

    example_id: Slug
    crop_id: Slug
    source_crop_label: Text = Field(description="The crop name exactly as the source prints it.")
    region_label: Text
    planting_period: Text
    initial_days: int = Field(gt=0)
    development_days: int = Field(gt=0)
    mid_season_days: int = Field(gt=0)
    late_season_days: int = Field(ge=0)
    total_days: int = Field(gt=0, description="The total exactly as the source prints it.")
    discrepancy_note: Text | None = Field(
        default=None,
        description="Required when the source's stages do not add up to its stated total.",
    )
    provenance: ProvenanceRecord

    @property
    def stage_sum(self) -> int:
        """The four stage lengths added together."""
        return self.initial_days + self.development_days + self.mid_season_days + self.late_season_days

    @property
    def is_internally_consistent(self) -> bool:
        return self.stage_sum == self.total_days

    @model_validator(mode="after")
    def _check_example(self) -> "GrowthStageExample":
        _require_cited(self.provenance, f"growth-stage example '{self.example_id}'")
        if self.is_internally_consistent:
            if self.discrepancy_note is not None:
                raise ValueError("a discrepancy note is only for rows whose stages do not add up")
            return self
        # The source itself is inconsistent. Keep what it prints, but say so.
        if self.discrepancy_note is None:
            raise ValueError(
                f"stage lengths add up to {self.stage_sum}, not the stated total {self.total_days}; "
                "record the discrepancy explicitly or correct the entry"
            )
        if self.provenance.confidence is not EvidenceConfidence.PROVISIONAL:
            raise ValueError("an internally inconsistent source row can only be provisional")
        return self


class SoilTextureReference(Contract):
    """Typical soil-water characteristics for one texture class, from literature.

    A reference value for a soil *type*. It is not a measurement of any field.
    """

    texture_class: SoilTextureClass
    source_label: Text = Field(description="The class name exactly as the source prints it.")
    field_capacity_min: float = Field(ge=0, le=1)
    field_capacity_max: float = Field(ge=0, le=1)
    wilting_point_min: float = Field(ge=0, le=1)
    wilting_point_max: float = Field(ge=0, le=1)
    available_water_min: float = Field(ge=0, le=1)
    available_water_max: float = Field(ge=0, le=1)
    unit: Literal[Unit.CUBIC_METRE_PER_CUBIC_METRE] = Unit.CUBIC_METRE_PER_CUBIC_METRE
    note: Text | None = None
    provenance: ProvenanceRecord

    @model_validator(mode="after")
    def _check_reference(self) -> "SoilTextureReference":
        for low, high, label in (
            (self.field_capacity_min, self.field_capacity_max, "field capacity"),
            (self.wilting_point_min, self.wilting_point_max, "wilting point"),
            (self.available_water_min, self.available_water_max, "available water"),
        ):
            if low > high:
                raise ValueError(f"{label}: minimum must not be greater than maximum")
        if self.field_capacity_max <= self.wilting_point_min:
            raise ValueError("field capacity must be able to exceed the wilting point")
        _require_cited(self.provenance, f"soil reference '{self.texture_class.value}'")
        return self


# --------------------------------------------------------------------------- #
# Rotation relationships and constraints
# --------------------------------------------------------------------------- #


class RelationshipType(StrEnum):
    SAME_CROP_REPETITION = "same_crop_repetition"
    SAME_FAMILY_REPETITION = "same_family_repetition"
    LEGUME_INCLUSION = "legume_inclusion"
    NITROGEN_BENEFIT = "nitrogen_benefit"
    PEST_DISEASE_CARRYOVER = "pest_disease_carryover"
    WEED_PRESSURE = "weed_pressure"
    SOIL_ORGANIC_MATTER = "soil_organic_matter"
    SOIL_COVER = "soil_cover"
    ROOTING_DIVERSITY = "rooting_diversity"
    ROTATION_DIVERSITY = "rotation_diversity"
    WATER_USE_CONTRAST = "water_use_contrast"


class RelationshipStrength(StrEnum):
    """How strong the claim is. A tendency is not a rule."""

    DOCUMENTED_TENDENCY = "documented_tendency"  # measured across studies; varies by case
    SITE_SPECIFIC_FINDING = "site_specific_finding"  # reported for one place and period
    GENERAL_PRINCIPLE = "general_principle"  # stated as guidance, not quantified
    UNSUPPORTED = "unsupported"  # no adequate source was found


class _Applicability(Contract):
    """Shared: which crops or families a record applies to."""

    applies_to_crops: tuple[Slug, ...] = ()
    applies_to_families: tuple[Text, ...] = ()
    applies_generally: bool = Field(
        default=False, description="True if the source states it for crops in general."
    )

    def _check_applicability(self, what: str) -> None:
        if not (self.applies_to_crops or self.applies_to_families or self.applies_generally):
            raise ValueError(f"{what} must say which crops or families it applies to")
        _require_unique(self.applies_to_crops, "applies_to_crops")
        _require_unique(self.applies_to_families, "applies_to_families")


class RotationRelationship(_Applicability):
    """A sourced statement about how crops in sequence affect each other."""

    relationship_id: Slug
    relationship_type: RelationshipType
    strength: RelationshipStrength
    statement: Text = Field(description="The scientific rationale, close to the source.")
    scope: Text = Field(description="Where and for what the evidence holds.")
    known_exceptions: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = Field(min_length=1)
    evidence: tuple[ProvenanceRecord, ...] = Field(min_length=1)
    explanation: Explanation

    @model_validator(mode="after")
    def _check_relationship(self) -> "RotationRelationship":
        self._check_applicability(f"relationship '{self.relationship_id}'")
        for record in self.evidence:
            _require_cited(record, f"relationship '{self.relationship_id}'")
        insufficient = [
            record.confidence is EvidenceConfidence.INSUFFICIENT_EVIDENCE for record in self.evidence
        ]
        if self.strength is RelationshipStrength.UNSUPPORTED and not all(insufficient):
            raise ValueError("an unsupported relationship must mark its evidence as insufficient")
        if self.strength is not RelationshipStrength.UNSUPPORTED and all(insufficient):
            raise ValueError(
                "a relationship whose only evidence is insufficient must be labelled unsupported"
            )
        return self


class CroppingArrangement(StrEnum):
    CONTINUOUS = "continuous"  # the same crop every season
    ROTATION = "rotation"  # different crops in sequence
    INTERCROP = "intercrop"  # different crops in the field at the same time; not a rotation


class DocumentedCroppingSystem(_Applicability):
    """A cropping system that a cited study actually grew and compared.

    It records what the source reports and, just as importantly, what it does
    not: a source that names the crops of a rotation rarely gives the season
    of each or the length of the cycle. Phase A4 must obtain those from the
    user or another source before it can build a ``CropRotation``.
    """

    system_id: Slug
    name: Text
    arrangement: CroppingArrangement
    crops: tuple[Slug, ...] = Field(min_length=1, description="In the order the source names them.")
    statement: Text
    reported_outcome: Text | None = Field(
        default=None, description="What the study reports for this system, in its own terms."
    )
    not_reported: tuple[Text, ...] = Field(
        min_length=1, description="Details needed to model the system that the source read does not give."
    )
    limitations: tuple[Text, ...] = Field(min_length=1)
    evidence: tuple[ProvenanceRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_system(self) -> "DocumentedCroppingSystem":
        if self.applies_to_crops and set(self.applies_to_crops) != set(self.crops):
            raise ValueError("applies_to_crops must list the same crops as the system")
        _require_unique(self.crops, "crops in a cropping system")
        if self.arrangement is CroppingArrangement.CONTINUOUS and len(self.crops) != 1:
            raise ValueError("a continuous system has exactly one crop")
        if self.arrangement is not CroppingArrangement.CONTINUOUS and len(self.crops) < 2:
            raise ValueError("a rotation or intercrop needs at least two crops")
        for record in self.evidence:
            _require_cited(record, f"cropping system '{self.system_id}'")
        return self

    @property
    def is_rotation(self) -> bool:
        return self.arrangement is CroppingArrangement.ROTATION


class ConstraintSeverity(StrEnum):
    HARD = "hard"  # the evidence says the crop cannot succeed under the condition
    ADVISORY = "advisory"  # worth warning about; not a prohibition
    CONTEXT_DEPENDENT = "context_dependent"  # depends on variety, management or local detail
    UNSUPPORTED = "unsupported"  # commonly asserted, but no adequate source was found


class RotationConstraint(_Applicability):
    """A stored rule for phase A4 to evaluate. Nothing in A3 executes it."""

    constraint_id: Slug
    description: Text
    severity: ConstraintSeverity
    condition: Text = Field(description="The soil, climate or sequence condition, in words.")
    inputs: tuple[Slug, ...] = Field(
        default=(), description="Registered variables A4 would need to evaluate it."
    )
    based_on_relationships: tuple[Slug, ...] = ()
    applicability: Text
    limitations: tuple[Text, ...] = Field(min_length=1)
    user_explanation: Text = Field(description="What a farmer would be told, in plain words.")
    evidence: tuple[ProvenanceRecord, ...] = Field(min_length=1)
    evaluated_in_a3: Literal[False] = False

    @model_validator(mode="after")
    def _check_constraint(self) -> "RotationConstraint":
        self._check_applicability(f"constraint '{self.constraint_id}'")
        for name in self.inputs:
            get_variable(name)
        _require_unique(self.inputs, "inputs")
        confidences = []
        for record in self.evidence:
            _require_cited(record, f"constraint '{self.constraint_id}'")
            confidences.append(record.confidence)
        if self.severity is ConstraintSeverity.HARD and not all(
            item is EvidenceConfidence.DIRECTLY_SUPPORTED for item in confidences
        ):
            raise ValueError("a hard constraint needs evidence that directly supports it")
        insufficient = [item is EvidenceConfidence.INSUFFICIENT_EVIDENCE for item in confidences]
        if self.severity is ConstraintSeverity.UNSUPPORTED and not all(insufficient):
            raise ValueError("an unsupported constraint must mark its evidence as insufficient")
        if self.severity is not ConstraintSeverity.UNSUPPORTED and all(insufficient):
            raise ValueError("a constraint whose only evidence is insufficient must be labelled unsupported")
        return self


# --------------------------------------------------------------------------- #
# Farmer priorities and variable mappings
# --------------------------------------------------------------------------- #


class PriorityOrigin(StrEnum):
    OFFICIAL_CHALLENGE_TEXT = "official_challenge_text"
    PROJECT_ADDITION = "project_addition"


class EvidenceAvailability(StrEnum):
    """Whether the knowledge base holds evidence that could inform a priority."""

    AVAILABLE = "available"
    PARTIAL = "partial"
    NOT_AVAILABLE = "not_available"


class PriorityDefinition(Contract):
    """What a priority means and what evidence would be needed to assess it.

    There is deliberately no weight here. Weights come from the farmer.
    """

    dimension: PriorityDimension
    label: Text
    description: Text
    origin: PriorityOrigin
    evidence_requirement: Text
    evidence_available: EvidenceAvailability
    related_relationships: tuple[Slug, ...] = ()
    related_variables: tuple[Slug, ...] = ()
    limitations: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_priority(self) -> "PriorityDefinition":
        for name in self.related_variables:
            get_variable(name)
        return self


class MappingTarget(StrEnum):
    NASA_OBSERVATION = "nasa_observation"  # a variable the A2 data layer retrieves
    DERIVED_FROM_NASA = "derived_from_nasa"  # needs a calculation that A4 must define
    SOIL_INFORMATION = "soil_information"  # supplied by the user or a soil source, never NASA


class VariableMapping(Contract):
    """An interface contract: which input a crop requirement would be compared with.

    A3 defines the pairing and its limits. A4 performs the comparison.
    """

    mapping_id: Slug
    crop_variable: Slug
    target: MappingTarget
    target_variables: tuple[Slug, ...] = Field(min_length=1)
    comparison_intent: Text
    temporal_basis: Text
    available_from_data_layer: bool = Field(
        description="True if every target variable is retrieved by the A2 data layer today."
    )
    limitations: tuple[Text, ...] = Field(min_length=1)
    implemented: Literal[False] = False

    @model_validator(mode="after")
    def _check_mapping(self) -> "VariableMapping":
        if get_variable(self.crop_variable).domain is not VariableDomain.CROP:
            raise ValueError(f"'{self.crop_variable}' is not a crop variable")
        expected = (
            VariableDomain.SOIL if self.target is MappingTarget.SOIL_INFORMATION else VariableDomain.ENVIRONMENT
        )
        for name in self.target_variables:
            if get_variable(name).domain is not expected:
                raise ValueError(f"'{name}' is not a {expected.value} variable")
        if self.target is MappingTarget.SOIL_INFORMATION and self.available_from_data_layer:
            raise ValueError("soil information never comes from the NASA data layer")
        return self


# --------------------------------------------------------------------------- #
# The knowledge base
# --------------------------------------------------------------------------- #


class KnowledgeManifest(Contract):
    """Version and status of the knowledge base as a whole."""

    schema_version: Literal[1]
    knowledge_base_version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
    status: KnowledgeStatus
    compiled_on: date
    pilot_site_id: Slug
    pilot_site_approved: bool
    files: dict[str, str]
    notes: tuple[Text, ...] = ()


class Claim(Contract):
    """One cited claim somewhere in the knowledge base, for reporting."""

    where: str
    provenance: ProvenanceRecord


class KnowledgeBase(Contract):
    """Everything loaded from ``data/knowledge``, cross-checked."""

    manifest: KnowledgeManifest
    sources: tuple[EvidenceSource, ...]
    families: tuple[BotanicalFamily, ...]
    crops: tuple[CropProfile, ...]
    growth_stage_examples: tuple[GrowthStageExample, ...] = ()
    soil_texture_references: tuple[SoilTextureReference, ...] = ()
    relationships: tuple[RotationRelationship, ...] = ()
    constraints: tuple[RotationConstraint, ...] = ()
    cropping_systems: tuple[DocumentedCroppingSystem, ...] = ()
    priorities: tuple[PriorityDefinition, ...] = ()
    variable_mappings: tuple[VariableMapping, ...] = ()

    # --- Cross-checks ---------------------------------------------------------

    @model_validator(mode="after")
    def _check_knowledge_base(self) -> "KnowledgeBase":
        _require_unique([item.source_id for item in self.sources], "source identifiers")
        _require_unique([item.name for item in self.families], "botanical families")
        _require_unique([item.crop_id for item in self.crops], "crop identifiers")
        _require_unique([item.example_id for item in self.growth_stage_examples], "growth-stage examples")
        _require_unique([item.texture_class.value for item in self.soil_texture_references], "soil texture references")
        _require_unique([item.relationship_id for item in self.relationships], "relationship identifiers")
        _require_unique([item.constraint_id for item in self.constraints], "constraint identifiers")
        _require_unique([item.system_id for item in self.cropping_systems], "cropping system identifiers")
        _require_unique([item.dimension.value for item in self.priorities], "priority definitions")
        _require_unique([item.mapping_id for item in self.variable_mappings], "mapping identifiers")

        sources = {item.source_id: item for item in self.sources}
        families = {item.name for item in self.families}
        crops = {item.crop_id for item in self.crops}
        relationships = {item.relationship_id for item in self.relationships}

        for crop in self.crops:
            if crop.botanical_family not in families:
                raise ValueError(
                    f"crop '{crop.crop_id}' names the family '{crop.botanical_family}', "
                    "which is not in the knowledge base"
                )
            if crop.nitrogen_fixing and not any(
                item.attribute == "nitrogen_fixation" for item in crop.attributes
            ):
                raise ValueError(
                    f"crop '{crop.crop_id}' is marked nitrogen-fixing without a cited statement"
                )

        for example in self.growth_stage_examples:
            if example.crop_id not in crops:
                raise ValueError(f"growth-stage example '{example.example_id}' names an unknown crop")

        for record in (*self.relationships, *self.constraints):
            label = getattr(record, "relationship_id", None) or getattr(record, "constraint_id")
            for crop_id in record.applies_to_crops:
                if crop_id not in crops:
                    raise ValueError(f"'{label}' names the unknown crop '{crop_id}'")
            for family in record.applies_to_families:
                if family not in families:
                    raise ValueError(f"'{label}' names the unknown family '{family}'")

        for system in self.cropping_systems:
            for crop_id in system.crops:
                if crop_id not in crops:
                    raise ValueError(f"cropping system '{system.system_id}' names the unknown crop '{crop_id}'")

        for constraint in self.constraints:
            for relationship_id in constraint.based_on_relationships:
                if relationship_id not in relationships:
                    raise ValueError(
                        f"constraint '{constraint.constraint_id}' builds on the unknown "
                        f"relationship '{relationship_id}'"
                    )

        for priority in self.priorities:
            for relationship_id in priority.related_relationships:
                if relationship_id not in relationships:
                    raise ValueError(
                        f"priority '{priority.dimension.value}' names the unknown relationship "
                        f"'{relationship_id}'"
                    )
        missing = {item.value for item in PriorityDimension} - {item.dimension.value for item in self.priorities}
        if self.priorities and missing:
            raise ValueError(f"no definition for priority: {', '.join(sorted(missing))}")

        for claim in self.claims():
            record = claim.provenance
            source = sources.get(record.source_id)
            if source is None:
                raise ValueError(f"{claim.where}: unknown evidence reference '{record.source_id}'")
            if (
                record.confidence is EvidenceConfidence.DIRECTLY_SUPPORTED
                and source.review_status not in READ_STATUSES
            ):
                raise ValueError(
                    f"{claim.where}: marked directly supported, but the source "
                    f"'{source.source_id}' was not read"
                )
        return self

    # --- Access ---------------------------------------------------------------

    def get_crop(self, crop_id: str) -> CropProfile:
        """Return one crop profile, or raise ``KnowledgeBaseError``."""
        for crop in self.crops:
            if crop.crop_id == crop_id:
                return crop
        raise KnowledgeBaseError(f"no crop '{crop_id}' in the knowledge base")

    def get_source(self, source_id: str) -> EvidenceSource:
        for source in self.sources:
            if source.source_id == source_id:
                return source
        raise KnowledgeBaseError(f"no source '{source_id}' in the evidence registry")

    def crops_in_family(self, family: str) -> tuple[CropProfile, ...]:
        return tuple(crop for crop in self.crops if crop.botanical_family == family)

    def _applies(self, record: _Applicability, crop: CropProfile) -> bool:
        return (
            record.applies_generally
            or crop.crop_id in record.applies_to_crops
            or crop.botanical_family in record.applies_to_families
        )

    def relationships_for(self, crop_id: str) -> tuple[RotationRelationship, ...]:
        """Relationships that name this crop, its family, or crops in general."""
        crop = self.get_crop(crop_id)
        return tuple(item for item in self.relationships if self._applies(item, crop))

    def constraints_for(self, crop_id: str) -> tuple[RotationConstraint, ...]:
        """Constraints that name this crop, its family, or crops in general."""
        crop = self.get_crop(crop_id)
        return tuple(item for item in self.constraints if self._applies(item, crop))

    def documented_rotations(self, *, with_legume: bool = False) -> tuple[DocumentedCroppingSystem, ...]:
        """Cropping systems a cited study grew as rotations, optionally only those with a legume."""
        fixing = {crop.crop_id for crop in self.crops if crop.nitrogen_fixing}
        return tuple(
            item
            for item in self.cropping_systems
            if item.is_rotation and (not with_legume or fixing & set(item.crops))
        )

    def growth_stages_for(self, crop_id: str) -> tuple[GrowthStageExample, ...]:
        return tuple(item for item in self.growth_stage_examples if item.crop_id == crop_id)

    def soil_reference(self, texture_class: SoilTextureClass) -> SoilTextureReference | None:
        """Literature reference values for a texture class, or ``None`` if not sourced."""
        return next(
            (item for item in self.soil_texture_references if item.texture_class is texture_class), None
        )

    def priority(self, dimension: PriorityDimension) -> PriorityDefinition:
        for item in self.priorities:
            # Compared by value, not identity, so a knowledge base cached across a
            # module reload still answers for an equal enum member.
            if item.dimension.value == PriorityDimension(dimension).value:
                return item
        raise KnowledgeBaseError(f"no definition for priority '{dimension.value}'")

    def mappings_for(self, crop_variable: str) -> tuple[VariableMapping, ...]:
        return tuple(item for item in self.variable_mappings if item.crop_variable == crop_variable)

    # --- Evidence reporting ---------------------------------------------------

    def claims(self) -> Iterator[Claim]:
        """Every cited claim in the knowledge base, with where it sits."""
        for family in self.families:
            for record in family.evidence:
                yield Claim(where=f"family:{family.name}", provenance=record)
        for crop in self.crops:
            for record in crop.sources:
                yield Claim(where=f"crop:{crop.crop_id}:identity", provenance=record)
            for requirement in crop.requirements:
                yield Claim(
                    where=f"crop:{crop.crop_id}:requirement:{requirement.requirement_id}",
                    provenance=requirement.provenance,
                )
            for attribute in crop.attributes:
                yield Claim(where=f"crop:{crop.crop_id}:attribute:{attribute.attribute}", provenance=attribute.provenance)
            for attribute in crop.regional_evidence:
                yield Claim(where=f"crop:{crop.crop_id}:regional:{attribute.attribute}", provenance=attribute.provenance)
        for example in self.growth_stage_examples:
            yield Claim(where=f"growth_stage:{example.example_id}", provenance=example.provenance)
        for reference in self.soil_texture_references:
            yield Claim(where=f"soil_reference:{reference.texture_class.value}", provenance=reference.provenance)
        for relationship in self.relationships:
            for record in relationship.evidence:
                yield Claim(where=f"relationship:{relationship.relationship_id}", provenance=record)
        for constraint in self.constraints:
            for record in constraint.evidence:
                yield Claim(where=f"constraint:{constraint.constraint_id}", provenance=record)
        for system in self.cropping_systems:
            for record in system.evidence:
                yield Claim(where=f"cropping_system:{system.system_id}", provenance=record)

    def confidence_summary(self) -> dict[str, int]:
        """Number of claims at each confidence level."""
        counts = Counter(claim.provenance.confidence.value for claim in self.claims() if claim.provenance.confidence)
        return {level.value: counts.get(level.value, 0) for level in EvidenceConfidence}

    def claims_by_source(self) -> dict[str, int]:
        """Number of claims resting on each source, in source order."""
        counts = Counter(claim.provenance.source_id for claim in self.claims())
        return {source.source_id: counts.get(source.source_id, 0) for source in self.sources}

    def unused_sources(self) -> tuple[str, ...]:
        """Registered sources that no claim cites."""
        return tuple(name for name, count in self.claims_by_source().items() if count == 0)

    def unknowns(self) -> dict[str, tuple[str, ...]]:
        """For each crop, the attributes the sources do not establish."""
        return {crop.crop_id: tuple(item.attribute for item in crop.unknowns) for crop in self.crops}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def _provenance(link: Any, sources: dict[str, EvidenceSource], where: str) -> ProvenanceRecord:
    """Turn an evidence link in a data file into a full provenance record."""
    if not isinstance(link, dict) or "source_id" not in link:
        raise KnowledgeBaseError(f"{where}: no evidence reference; every claim must cite a source")
    source = sources.get(link["source_id"])
    if source is None:
        raise KnowledgeBaseError(f"{where}: unknown evidence reference '{link['source_id']}'")
    return ProvenanceRecord(
        kind=link.get("kind", DataKind.LITERATURE_VALUE),
        source_id=source.source_id,
        source_name=source.title,
        source_version=str(source.year) if source.year else None,
        citation=source.citation,
        url=source.url,
        locator=link.get("locator"),
        confidence=link.get("confidence"),
        applicability=link.get("applicability"),
        transformations=tuple(link.get("transformations", ())),
    )


def _many(links: Any, sources: dict[str, EvidenceSource], where: str) -> tuple[ProvenanceRecord, ...]:
    if not isinstance(links, list) or not links:
        raise KnowledgeBaseError(f"{where}: no evidence reference; every claim must cite a source")
    return tuple(_provenance(link, sources, where) for link in links)


def _with_provenance(item: dict[str, Any], sources: dict[str, EvidenceSource], where: str) -> dict[str, Any]:
    fields = {key: value for key, value in item.items() if key != "evidence"}
    fields["provenance"] = _provenance(item.get("evidence"), sources, where)
    return fields


def _with_evidence(item: dict[str, Any], sources: dict[str, EvidenceSource], where: str) -> dict[str, Any]:
    fields = dict(item)
    fields["evidence"] = _many(item.get("evidence"), sources, where)
    return fields


def _build_crop(raw: dict[str, Any], sources: dict[str, EvidenceSource]) -> CropProfile:
    crop_id = raw.get("crop_id", "?")
    where = f"crop '{crop_id}'"
    fields = {
        key: value
        for key, value in raw.items()
        if key not in {"identity_evidence", "requirements", "attributes", "regional_evidence"}
    }
    fields["sources"] = _many(raw.get("identity_evidence"), sources, f"{where} identity")
    fields["requirements"] = tuple(
        _with_provenance(item, sources, f"{where} requirement '{item.get('requirement_id', '?')}'")
        for item in raw.get("requirements", [])
    )
    for group in ("attributes", "regional_evidence"):
        fields[group] = tuple(
            _with_provenance(item, sources, f"{where} {group} '{item.get('attribute', '?')}'")
            for item in raw.get(group, [])
        )
    return CropProfile(**fields)


def _describe(error: ValidationError) -> str:
    first = error.errors()[0]
    place = ".".join(str(part) for part in first["loc"])
    return f"{place}: {first['msg']}" if place else first["msg"]


def build_knowledge_base(raw: dict[str, Any]) -> KnowledgeBase:
    """Validate raw knowledge data and return the typed knowledge base.

    ``raw`` has the keys ``manifest``, ``sources``, ``families``, ``crops``,
    ``growth_stage_examples``, ``soil_texture_references``, ``relationships``,
    ``constraints``, ``cropping_systems``, ``priorities`` and ``variable_mappings``. Records are
    returned in a fixed order whatever order the files use.
    """
    try:
        source_list = sorted(
            (EvidenceSource(**item) for item in raw.get("sources", [])), key=lambda item: item.source_id
        )
        _require_unique([item.source_id for item in source_list], "source identifiers")
        sources = {item.source_id: item for item in source_list}

        families = sorted(
            (
                BotanicalFamily(**_with_evidence(item, sources, f"family '{item.get('name', '?')}'"))
                for item in raw.get("families", [])
            ),
            key=lambda item: item.name,
        )
        crops = sorted((_build_crop(item, sources) for item in raw.get("crops", [])), key=lambda item: item.crop_id)
        examples = sorted(
            (
                GrowthStageExample(**_with_provenance(item, sources, f"growth-stage example '{item.get('example_id', '?')}'"))
                for item in raw.get("growth_stage_examples", [])
            ),
            key=lambda item: item.example_id,
        )
        order = {member: index for index, member in enumerate(SoilTextureClass)}
        soil_references = sorted(
            (
                SoilTextureReference(**_with_provenance(item, sources, f"soil reference '{item.get('texture_class', '?')}'"))
                for item in raw.get("soil_texture_references", [])
            ),
            key=lambda item: order[item.texture_class],
        )
        relationships = sorted(
            (
                RotationRelationship(**_with_evidence(item, sources, f"relationship '{item.get('relationship_id', '?')}'"))
                for item in raw.get("relationships", [])
            ),
            key=lambda item: item.relationship_id,
        )
        constraints = sorted(
            (
                RotationConstraint(**_with_evidence(item, sources, f"constraint '{item.get('constraint_id', '?')}'"))
                for item in raw.get("constraints", [])
            ),
            key=lambda item: item.constraint_id,
        )
        systems = sorted(
            (
                DocumentedCroppingSystem(**_with_evidence(item, sources, f"cropping system '{item.get('system_id', '?')}'"))
                for item in raw.get("cropping_systems", [])
            ),
            key=lambda item: item.system_id,
        )
        priority_order = {member: index for index, member in enumerate(PriorityDimension)}
        priorities = sorted(
            (PriorityDefinition(**item) for item in raw.get("priorities", [])),
            key=lambda item: priority_order[item.dimension],
        )
        mappings = sorted(
            (VariableMapping(**item) for item in raw.get("variable_mappings", [])),
            key=lambda item: item.mapping_id,
        )
        return KnowledgeBase(
            manifest=KnowledgeManifest(**raw.get("manifest", {})),
            sources=tuple(source_list),
            families=tuple(families),
            crops=tuple(crops),
            growth_stage_examples=tuple(examples),
            soil_texture_references=tuple(soil_references),
            relationships=tuple(relationships),
            constraints=tuple(constraints),
            cropping_systems=tuple(systems),
            priorities=tuple(priorities),
            variable_mappings=tuple(mappings),
        )
    except ValidationError as error:
        raise KnowledgeBaseError(f"invalid knowledge base: {_describe(error)}") from None
    except (TypeError, ValueError) as error:
        raise KnowledgeBaseError(f"invalid knowledge base: {error}") from None


def read_knowledge_files(directory: Path | None = None) -> dict[str, Any]:
    """Read the knowledge files into one raw dictionary. Local files only."""
    folder = Path(directory) if directory is not None else KNOWLEDGE_DIRECTORY
    manifest_path = folder / MANIFEST_FILE
    if not manifest_path.is_file():
        raise KnowledgeBaseError(f"no knowledge base found: {manifest_path} is missing")

    def read(name: str) -> dict[str, Any]:
        path = folder / name
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise KnowledgeBaseError(f"knowledge file {name} is missing") from None
        except json.JSONDecodeError as error:
            raise KnowledgeBaseError(f"knowledge file {name} is not valid JSON ({error.msg})") from None
        if not isinstance(content, dict):
            raise KnowledgeBaseError(f"knowledge file {name} must contain a JSON object")
        return content

    manifest = read(MANIFEST_FILE)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise KnowledgeBaseError(
            f"knowledge base schema version {manifest.get('schema_version')!r} is not supported; "
            f"this code reads version {SCHEMA_VERSION}"
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise KnowledgeBaseError("the manifest must list the knowledge files")

    raw: dict[str, Any] = {"manifest": manifest}
    for name in sorted(set(files.values())):
        content = read(name)
        if content.get("schema_version") != SCHEMA_VERSION:
            raise KnowledgeBaseError(f"knowledge file {name} has an unsupported schema version")
        for key, value in content.items():
            if key == "schema_version":
                continue
            if key in raw:
                raise KnowledgeBaseError(f"'{key}' is defined in more than one knowledge file")
            raw[key] = value
    return raw


def load_knowledge_base(directory: Path | None = None) -> KnowledgeBase:
    """Load and validate the knowledge base from local files."""
    return build_knowledge_base(read_knowledge_files(directory))
