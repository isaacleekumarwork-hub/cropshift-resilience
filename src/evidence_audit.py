"""Scientific evidence audit and the evidence gate (phase A4.1).

Responsibility
    Record the outcome of re-checking every source in the evidence registry,
    give every cited claim in the knowledge base an audit status and a required
    action, and stand between the knowledge base and every calculation in A4.

The evidence gate
    No literature value reaches an indicator except through
    ``EvidenceGate.check`` or ``EvidenceGate.requirement``. The gate admits a
    claim for one of two uses:

    * ``NUMERIC_INPUT``: the value drives a comparison result. Only claims whose
      source content was read and re-checked in the A4 audit qualify. A
      context-dependent claim is admitted with its conditions, which the result
      must display.
    * ``BACKGROUND``: the claim may be shown to explain a result, never to
      calculate one. Abstract-only claims qualify for this use only.

    Unverified, provisional, unsupported and contradicted claims are refused for
    both uses, and so is any value whose source is not in the registry. A
    refused value is reported as missing; nothing is substituted for it.

How statuses are assigned
    By rule, from the source's review status and the confidence the A3 reading
    gave the claim:

    ===============================  ========================  ==========================
    Source read and claim confidence  Audit status              Default action
    ===============================  ========================  ==========================
    content read, directly supported  VERIFIED_DIRECT           RETAIN
    content read, context-dependent   VERIFIED_CONDITIONAL      QUALIFY
    abstract read only                ABSTRACT_ONLY             QUALIFY (background only)
    provisional or insufficient       UNVERIFIED                EXCLUDE_FROM_CALCULATION
    source not read or not registered UNVERIFIED                EXCLUDE_FROM_CALCULATION
    ===============================  ========================  ==========================

    Exceptions are listed, each with its reason, in
    ``data/knowledge/evidence_audit.json`` under ``claim_overrides``.

AI assistance: drafted with Claude Code (Anthropic). The audit outcomes were
established by re-reading the sources on 15 Nov 2026; see
docs/scientific_evidence_audit.md.
"""

from __future__ import annotations

import fnmatch
import json
from collections import Counter
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from src.crop_knowledge import (
    KNOWLEDGE_DIRECTORY,
    READ_STATUSES,
    EvidenceSource,
    KnowledgeBase,
    KnowledgeBaseError,
    ReviewStatus,
)
from src.models import (
    Contract,
    CropProfile,
    CropRequirement,
    EvidenceConfidence,
    ProvenanceRecord,
    RequirementBasis,
    Slug,
    Text,
)

AUDIT_FILE = "evidence_audit.json"
AUDIT_SCHEMA_VERSION = 1


class EvidenceAuditError(KnowledgeBaseError):
    """The audit file is missing, malformed or inconsistent with the knowledge base."""


class EvidenceGateError(KnowledgeBaseError):
    """A calculation asked for a value that the evidence does not support."""


# --------------------------------------------------------------------------- #
# Vocabularies
# --------------------------------------------------------------------------- #


class AuditStatus(StrEnum):
    VERIFIED_DIRECT = "verified_direct"  # read, and the source states it for this case
    VERIFIED_CONDITIONAL = "verified_conditional"  # read, but holds only under stated conditions
    ABSTRACT_ONLY = "abstract_only"  # only the published abstract supports it
    UNVERIFIED = "unverified"  # provisional, unsupported, or the source was not read
    CONTRADICTED = "contradicted"  # the source says something different


class AuditAction(StrEnum):
    RETAIN = "retain"
    QUALIFY = "qualify"
    REPLACE_WITH_VERIFIED_SOURCE = "replace_with_verified_source"
    EXCLUDE_FROM_CALCULATION = "exclude_from_calculation"


class EvidenceUse(StrEnum):
    """What a calculation wants to do with a claim."""

    NUMERIC_INPUT = "numeric_input"  # the value drives a comparison result
    BACKGROUND = "background"  # the claim explains a result; it calculates nothing


class SourceAccess(StrEnum):
    FULL_TEXT_OPEN = "full_text_open"
    FULL_TEXT_OPEN_NOT_READ = "full_text_open_not_read"
    ABSTRACT_OPEN_FULL_TEXT_RESTRICTED = "abstract_open_full_text_restricted"


_DEFAULT_ACTION = {
    AuditStatus.VERIFIED_DIRECT: AuditAction.RETAIN,
    AuditStatus.VERIFIED_CONDITIONAL: AuditAction.QUALIFY,
    AuditStatus.ABSTRACT_ONLY: AuditAction.QUALIFY,
    AuditStatus.UNVERIFIED: AuditAction.EXCLUDE_FROM_CALCULATION,
    AuditStatus.CONTRADICTED: AuditAction.EXCLUDE_FROM_CALCULATION,
}

_DEFAULT_USES = {
    AuditStatus.VERIFIED_DIRECT: (EvidenceUse.NUMERIC_INPUT, EvidenceUse.BACKGROUND),
    AuditStatus.VERIFIED_CONDITIONAL: (EvidenceUse.NUMERIC_INPUT, EvidenceUse.BACKGROUND),
    AuditStatus.ABSTRACT_ONLY: (EvidenceUse.BACKGROUND,),
    AuditStatus.UNVERIFIED: (),
    AuditStatus.CONTRADICTED: (),
}


# --------------------------------------------------------------------------- #
# The audit record
# --------------------------------------------------------------------------- #


class SourceAudit(Contract):
    """The A4 re-check of one registered source."""

    source_id: Slug
    reachable: bool
    checked_url: Text
    access: SourceAccess
    metadata_confirmed: bool
    metadata_check: Text
    rechecked_sections: tuple[Text, ...] = ()
    outcome: Text
    issues: tuple[Text, ...] = ()


class ClaimOverride(Contract):
    """An exception to the status rule for one claim, with its reason."""

    where: Text
    status: AuditStatus
    action: AuditAction
    allowed_uses: tuple[EvidenceUse, ...]
    reason: Text
    condition: Text | None = Field(default=None, description="Shown beside the value whenever it is used.")

    @model_validator(mode="after")
    def _check_override(self) -> "ClaimOverride":
        if self.status in (AuditStatus.UNVERIFIED, AuditStatus.CONTRADICTED) and self.allowed_uses:
            raise ValueError("an unverified or contradicted claim cannot be allowed any use")
        if self.status is AuditStatus.ABSTRACT_ONLY and EvidenceUse.NUMERIC_INPUT in self.allowed_uses:
            raise ValueError("an abstract-only claim cannot be a numeric calculation input")
        return self


class AuditFinding(Contract):
    finding_id: Slug
    kind: Slug
    action: AuditAction
    affects: tuple[Text, ...] = ()
    summary: Text


class EvidenceAudit(Contract):
    """Everything in ``data/knowledge/evidence_audit.json``."""

    schema_version: Literal[1]
    audit_version: Text
    audited_on: date
    knowledge_base_version: Text
    method: tuple[Text, ...] = Field(min_length=1)
    sources: tuple[SourceAudit, ...]
    rechecked_claims: tuple[Text, ...] = ()
    claim_overrides: tuple[ClaimOverride, ...] = ()
    method_sources: tuple[EvidenceSource, ...] = ()
    findings: tuple[AuditFinding, ...] = ()

    @model_validator(mode="after")
    def _check_audit(self) -> "EvidenceAudit":
        ids = [item.source_id for item in self.sources]
        if len(set(ids)) != len(ids):
            raise ValueError("each source may be audited once")
        overrides = [item.where for item in self.claim_overrides]
        if len(set(overrides)) != len(overrides):
            raise ValueError("each claim may have one override")
        return self

    def source(self, source_id: str) -> SourceAudit | None:
        return next((item for item in self.sources if item.source_id == source_id), None)

    def method_source(self, source_id: str) -> EvidenceSource:
        for item in self.method_sources:
            if item.source_id == source_id:
                return item
        raise EvidenceAuditError(f"no method source '{source_id}' in the evidence audit")

    def override(self, where: str) -> ClaimOverride | None:
        return next((item for item in self.claim_overrides if item.where == where), None)

    def was_rechecked(self, where: str, source_id: str) -> bool:
        key = f"{where}|{source_id}"
        return any(fnmatch.fnmatchcase(key, pattern) for pattern in self.rechecked_claims)


# --------------------------------------------------------------------------- #
# Claim assessments and the claim-to-evidence matrix
# --------------------------------------------------------------------------- #


class ClaimAssessment(Contract):
    """The audit outcome for one cited claim."""

    claim_id: Text
    where: Text
    claim: Text = Field(description="The claim, as the knowledge base states it.")
    source_id: Slug
    locator: Text | None
    geographic_applicability: Text
    crop_applicability: Text
    confidence: EvidenceConfidence | None
    status: AuditStatus
    action: AuditAction
    allowed_uses: tuple[EvidenceUse, ...]
    rechecked_in_a4: bool
    reason: Text
    condition: Text | None = None


def _derive_status(
    source: EvidenceSource | None, confidence: EvidenceConfidence | None
) -> tuple[AuditStatus, str]:
    if source is None:
        return AuditStatus.UNVERIFIED, "The source is not in the evidence registry."
    if source.review_status not in READ_STATUSES:
        return AuditStatus.UNVERIFIED, f"The source was not read (review status '{source.review_status.value}')."
    if confidence is None:
        return AuditStatus.UNVERIFIED, "The claim has no confidence classification."
    if confidence is EvidenceConfidence.INSUFFICIENT_EVIDENCE:
        return AuditStatus.UNVERIFIED, "No adequate source supports the claim; it is recorded as unsupported."
    if source.review_status is ReviewStatus.ABSTRACT_READ:
        return AuditStatus.ABSTRACT_ONLY, "Only the published abstract was read; it states the claim."
    if confidence is EvidenceConfidence.PROVISIONAL:
        return (
            AuditStatus.UNVERIFIED,
            "The A3 reading marked the claim provisional: the source is ambiguous, inconsistent or garbled here.",
        )
    if confidence is EvidenceConfidence.DIRECTLY_SUPPORTED:
        return AuditStatus.VERIFIED_DIRECT, "The source content was read and states the claim directly."
    return (
        AuditStatus.VERIFIED_CONDITIONAL,
        "The source content was read; the claim holds under the conditions the source states.",
    )


def claim_texts(kb: KnowledgeBase) -> dict[str, str]:
    """The text of every claim location in the knowledge base, keyed as ``Claim.where``."""
    texts: dict[str, str] = {}
    for family in kb.families:
        texts[f"family:{family.name}"] = f"{family.name} is a botanical family."
    for crop in kb.crops:
        texts[f"crop:{crop.crop_id}:identity"] = (
            f"{crop.common_name} is {crop.scientific_name or 'the species named'}, family {crop.botanical_family}."
        )
        for item in crop.requirements:
            texts[f"crop:{crop.crop_id}:requirement:{item.requirement_id}"] = item.statement
        for item in crop.attributes:
            texts[f"crop:{crop.crop_id}:attribute:{item.attribute}"] = item.statement
        for item in crop.regional_evidence:
            texts[f"crop:{crop.crop_id}:regional:{item.attribute}"] = item.statement
    for example in kb.growth_stage_examples:
        texts[f"growth_stage:{example.example_id}"] = (
            f"{example.source_crop_label}, {example.region_label}: stages "
            f"{example.initial_days}/{example.development_days}/{example.mid_season_days}/"
            f"{example.late_season_days} days, total {example.total_days}."
        )
    for reference in kb.soil_texture_references:
        texts[f"soil_reference:{reference.texture_class.value}"] = (
            f"{reference.source_label}: available water {reference.available_water_min}-"
            f"{reference.available_water_max} m3/m3."
        )
    for relationship in kb.relationships:
        texts[f"relationship:{relationship.relationship_id}"] = relationship.statement
    for constraint in kb.constraints:
        texts[f"constraint:{constraint.constraint_id}"] = f"{constraint.description} Condition: {constraint.condition}"
    for system in kb.cropping_systems:
        texts[f"cropping_system:{system.system_id}"] = system.statement
    return texts


def _crop_applicability(where: str, source: EvidenceSource | None) -> str:
    parts = where.split(":")
    if parts[0] == "crop" and len(parts) > 1:
        return parts[1]
    return source.crop_scope if source else "Not stated."


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #


class GateDecision(Contract):
    """Whether one claim may be used for one purpose, and on what conditions."""

    claim_id: Text
    source_id: Slug
    use: EvidenceUse
    admitted: bool
    status: AuditStatus
    action: AuditAction
    reason: Text
    conditions: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check_decision(self) -> "GateDecision":
        if self.admitted and self.status is AuditStatus.VERIFIED_CONDITIONAL and not self.conditions:
            raise ValueError("a conditional claim can be admitted only with its conditions")
        if self.admitted and self.status in (AuditStatus.UNVERIFIED, AuditStatus.CONTRADICTED):
            raise ValueError("an unverified or contradicted claim can never be admitted")
        if self.admitted and self.use is EvidenceUse.NUMERIC_INPUT and self.status is AuditStatus.ABSTRACT_ONLY:
            raise ValueError("an abstract-only claim cannot be a numeric input")
        return self


class EvidenceGate:
    """Decides which knowledge-base claims a calculation may use."""

    def __init__(self, kb: KnowledgeBase, audit: EvidenceAudit) -> None:
        self.kb = kb
        self.audit = audit
        self._sources = {item.source_id: item for item in kb.sources}
        self._texts = claim_texts(kb)

    # --- Assessment -------------------------------------------------------------

    def assess(self, where: str, provenance: ProvenanceRecord, *, claim_id: str | None = None) -> ClaimAssessment:
        source = self._sources.get(provenance.source_id)
        status, reason = _derive_status(source, provenance.confidence)
        override = self.audit.override(where) if source is not None else None
        rechecked = source is not None and self.audit.was_rechecked(where, provenance.source_id)
        if override is not None and status not in (AuditStatus.UNVERIFIED,):
            status, action, uses = override.status, override.action, override.allowed_uses
            reason = override.reason
            condition = override.condition
        else:
            action, uses, condition = _DEFAULT_ACTION[status], _DEFAULT_USES[status], None
        if status is AuditStatus.ABSTRACT_ONLY:
            condition = condition or (
                f"Supported by the abstract of {source.citation if source else provenance.source_id}; "
                "the full study was not read."
            )
        return ClaimAssessment(
            claim_id=claim_id or f"{where}|{provenance.source_id}",
            where=where,
            claim=self._texts.get(where, "Not a knowledge-base claim."),
            source_id=provenance.source_id,
            locator=provenance.locator,
            geographic_applicability=provenance.applicability or (source.geographic_scope if source else "Not stated."),
            crop_applicability=_crop_applicability(where, source),
            confidence=provenance.confidence,
            status=status,
            action=action,
            allowed_uses=uses,
            rechecked_in_a4=rechecked,
            reason=reason,
            condition=condition,
        )

    def matrix(self) -> tuple[ClaimAssessment, ...]:
        """The claim-to-evidence matrix: every cited claim in the knowledge base."""
        seen: Counter[str] = Counter()
        rows = []
        for claim in self.kb.claims():
            key = f"{claim.where}|{claim.provenance.source_id}"
            seen[key] += 1
            claim_id = key if seen[key] == 1 else f"{key}#{seen[key]}"
            rows.append(self.assess(claim.where, claim.provenance, claim_id=claim_id))
        return tuple(rows)

    def summary(self) -> dict[str, dict[str, int]]:
        rows = self.matrix()
        return {
            "status": {item.value: sum(1 for row in rows if row.status is item) for item in AuditStatus},
            "action": {item.value: sum(1 for row in rows if row.action is item) for item in AuditAction},
            "rechecked": {
                "rechecked_in_a4": sum(1 for row in rows if row.rechecked_in_a4),
                "a3_reading_only": sum(1 for row in rows if not row.rechecked_in_a4),
            },
        }

    # --- Decisions --------------------------------------------------------------

    def check(self, where: str, provenance: ProvenanceRecord, use: EvidenceUse, *, extra_conditions: tuple[str, ...] = ()) -> GateDecision:
        """May this claim be used this way? Never raises; read ``admitted``."""
        row = self.assess(where, provenance)

        def decide(admitted: bool, reason: str, conditions: tuple[str, ...] = ()) -> GateDecision:
            return GateDecision(
                claim_id=row.claim_id,
                source_id=row.source_id,
                use=use,
                admitted=admitted,
                status=row.status,
                action=row.action,
                reason=reason,
                conditions=conditions if admitted else (),
            )

        if row.status in (AuditStatus.UNVERIFIED, AuditStatus.CONTRADICTED):
            return decide(False, f"Excluded: {row.reason}")
        if use not in row.allowed_uses:
            if row.status is AuditStatus.ABSTRACT_ONLY:
                return decide(False, "Excluded: an abstract-only claim may explain a result but not calculate one.")
            return decide(False, f"Excluded for this use: {row.reason}")
        if use is EvidenceUse.NUMERIC_INPUT and not row.rechecked_in_a4:
            return decide(
                False,
                "Excluded: the value was not re-checked against its source in the A4 evidence audit, "
                "so it may not drive a calculation.",
            )
        conditions = tuple(
            item for item in (row.condition, *extra_conditions) if item
        )
        if row.status is AuditStatus.VERIFIED_CONDITIONAL and not conditions:
            conditions = (row.geographic_applicability,)
        return decide(True, row.reason, conditions)

    def requirement(
        self,
        crop: CropProfile,
        requirement: CropRequirement,
        use: EvidenceUse = EvidenceUse.NUMERIC_INPUT,
        *,
        stage_dates_known: bool = False,
    ) -> GateDecision:
        """Gate one crop requirement, also checking that it applies to this crop and use."""
        where = f"crop:{crop.crop_id}:requirement:{requirement.requirement_id}"
        if requirement not in crop.requirements:
            row = self.assess(where, requirement.provenance)
            return GateDecision(
                claim_id=row.claim_id,
                source_id=requirement.provenance.source_id,
                use=use,
                admitted=False,
                status=AuditStatus.UNVERIFIED,
                action=AuditAction.EXCLUDE_FROM_CALCULATION,
                reason=f"Excluded: the requirement is not part of the knowledge-base profile of '{crop.crop_id}'.",
            )
        decision = self.check(where, requirement.provenance, use, extra_conditions=(requirement.limitation,))
        if (
            decision.admitted
            and use is EvidenceUse.NUMERIC_INPUT
            and requirement.basis is RequirementBasis.STAGE_SPECIFIC
            and not stage_dates_known
        ):
            return decision.model_copy(
                update={
                    "admitted": False,
                    "conditions": (),
                    "reason": (
                        f"Excluded: the value applies only to the '{requirement.growth_stage}' stage, "
                        "whose dates at the site are unknown, so it cannot be compared with a whole season."
                    ),
                }
            )
        return decision

    def admitted_requirements(
        self,
        crop: CropProfile,
        variable: str,
        use: EvidenceUse = EvidenceUse.NUMERIC_INPUT,
        *,
        stage_dates_known: bool = False,
    ) -> tuple[tuple[tuple[CropRequirement, GateDecision], ...], tuple[tuple[CropRequirement, GateDecision], ...]]:
        """Split a crop's requirements for one variable into admitted and refused."""
        admitted, refused = [], []
        for item in crop.requirements_for(variable):
            decision = self.requirement(crop, item, use, stage_dates_known=stage_dates_known)
            (admitted if decision.admitted else refused).append((item, decision))
        return tuple(admitted), tuple(refused)

    def require(self, where: str, provenance: ProvenanceRecord, use: EvidenceUse) -> GateDecision:
        """Like ``check``, but raise ``EvidenceGateError`` if the claim is refused."""
        decision = self.check(where, provenance, use)
        if not decision.admitted:
            raise EvidenceGateError(f"{where}: {decision.reason}")
        return decision


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def read_audit_file(directory: Path | None = None) -> dict[str, Any]:
    path = (directory or KNOWLEDGE_DIRECTORY) / AUDIT_FILE
    if not path.is_file():
        raise EvidenceAuditError(f"the evidence audit file is missing: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise EvidenceAuditError(f"{AUDIT_FILE} is not valid JSON: {error}") from None
    if not isinstance(raw, dict) or raw.get("schema_version") != AUDIT_SCHEMA_VERSION:
        raise EvidenceAuditError(f"{AUDIT_FILE} must declare schema_version {AUDIT_SCHEMA_VERSION}")
    return raw


def build_evidence_audit(raw: dict[str, Any], kb: KnowledgeBase) -> EvidenceAudit:
    """Validate the audit file and check it against the knowledge base."""
    try:
        audit = EvidenceAudit.model_validate(raw)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        raise EvidenceAuditError(f"{AUDIT_FILE}: {location}: {first['msg']}") from None
    registered = {item.source_id for item in kb.sources}
    audited = {item.source_id for item in audit.sources}
    if audited != registered:
        missing = sorted(registered - audited)
        extra = sorted(audited - registered)
        raise EvidenceAuditError(
            f"the audit must cover every registered source exactly; missing {missing}, unknown {extra}"
        )
    if audit.knowledge_base_version != kb.manifest.knowledge_base_version:
        raise EvidenceAuditError(
            f"the audit was made for knowledge base {audit.knowledge_base_version}, "
            f"but {kb.manifest.knowledge_base_version} is loaded; re-audit before use"
        )
    texts = claim_texts(kb)
    for override in audit.claim_overrides:
        if override.where not in texts:
            raise EvidenceAuditError(f"override for an unknown claim '{override.where}'")
    overlap = registered & {item.source_id for item in audit.method_sources}
    if overlap:
        raise EvidenceAuditError(f"method sources duplicate registered sources: {sorted(overlap)}")
    return audit


def load_evidence_audit(kb: KnowledgeBase, directory: Path | None = None) -> EvidenceAudit:
    return build_evidence_audit(read_audit_file(directory), kb)


def load_evidence_gate(kb: KnowledgeBase, directory: Path | None = None) -> EvidenceGate:
    """The gate every A4 calculation uses. Reads local files only."""
    return EvidenceGate(kb, load_evidence_audit(kb, directory))
