"""Validation of retrieved data — placeholder, planned for phase A2.

Not implemented. This module validates nothing yet.

Planned responsibility
    Turn raw NASA responses into ``models.EnvironmentalObservation`` objects:
    replace source fill values (for example -999) with explicit missing
    statuses, confirm units against the variable registry, flag implausible
    values as suspect, and report how complete each series is.

Planned interface (subject to change in A2)
    to_observations(raw_response, source) -> models.ObservationSeries
    completeness_report(series) -> summary of gaps and quality flags

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
