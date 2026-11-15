"""Comparison export (phase A5).

Responsibility
    Turn a finished ``ComparisonReport`` into files a farmer or reviewer can
    keep: a plain-text summary (Markdown), the full report as JSON, and the
    same comparison in the A1 ``ComparisonResult`` contract as JSON. Everything
    is built from the engine's result objects; nothing is recalculated,
    reworded by AI or added. No file is written to disk by this module: the
    interface offers the text for download.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

from src.comparison_engine import ComparisonReport, ConstraintOutcome, IndicatorStatus


def report_json(report: ComparisonReport) -> str:
    """The complete report, every field, as JSON."""
    return report.model_dump_json(indent=2)


def comparison_result_json(report: ComparisonReport) -> str:
    """The comparison in the A1 ``ComparisonResult`` contract, as JSON."""
    return report.to_comparison_result().model_dump_json(indent=2)


def summary_markdown(report: ComparisonReport) -> str:
    """A readable summary with every result, its status, the tradeoffs and the limits."""
    lines = [
        "# CropShift RESILIENCE: rotation comparison",
        "",
        f"Generated {report.generated_at:%d %B %Y %H:%M} UTC by engine {report.engine_version}.",
        "",
        f"**Site:** {report.site_name} (latitude {report.location.latitude}, longitude {report.location.longitude}). "
        f"Status: {report.pilot_status.value}. {report.approval_note}",
        "",
        f"**Data:** NASA POWER daily record, {report.observation_period[0]} to {report.observation_period[1]}, "
        f"response fingerprint {report.payload_sha256}. Knowledge base {report.knowledge_base_version}, "
        f"evidence audit {report.audit_version}.",
        "",
        "**No overall score.** The strategies are shown side by side; none is ranked or recommended.",
        "",
        "## Soil information used",
        "",
    ]
    if report.soil.records:
        if report.soil.hypothetical:
            lines.append("Illustrative soil profile, invented for demonstration. It describes no real field.")
        for record in report.soil.records:
            value = record.value if record.value is not None else record.category
            lines.append(f"- {record.variable}: {value} ({record.source_class.value}, {record.verification.value})")
    else:
        lines.append("None supplied. Soil indicators are unavailable.")
    lines += ["", "## Historical seasons", ""]
    for item in report.scenarios:
        lines.append(
            f"- {item.name}: {item.seasons_classified} past seasons; dry up to {item.dry_upper_mm} mm, wet from "
            f"{item.wet_lower_mm} mm. Historical, not a forecast."
        )
    lines += ["", "## What changes between these strategies?", ""]
    lines += [f"- **{note.aspect}.** {note.statement}" for note in report.tradeoffs]
    for assessment in report.strategies:
        counts = assessment.completeness
        lines += [
            "",
            f"## {assessment.strategy.name}",
            "",
            f"Crops: {' → '.join(crop.common_name for crop in assessment.profile.crops)}. "
            f"Families: {', '.join(assessment.profile.families)}. "
            f"Indicators: {counts.supported} supported, {counts.conditional} conditional, {counts.unavailable} unavailable.",
            "",
        ]
        for result in assessment.indicators:
            confidence = result.uncertainty.confidence.value.replace("_", " ")
            lines.append(f"- [{result.status.value}, confidence {confidence}] {result.headline}")
            if result.status is IndicatorStatus.CONDITIONAL:
                lines.append(f"  - Condition: {result.conditions[0]}")
        triggered = [item for item in assessment.constraints if item.outcome is ConstraintOutcome.TRIGGERED]
        if triggered:
            lines += ["", "Considerations for local review:"]
            lines += [f"- {item.finding}" for item in triggered]
    lines += ["", "## What CropShift does not estimate", ""]
    lines += [f"- **{item.outcome}.** {item.reason}" for item in report.unsupported_outcomes]
    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in report.limitations]
    lines += ["", "## Data citations", ""]
    lines += [f"- {item}" for item in report.dataset_citations]
    lines += ["", report.disclaimer, ""]
    return "\n".join(lines)
