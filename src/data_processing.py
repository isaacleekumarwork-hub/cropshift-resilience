"""Processing of validated environmental data — placeholder, planned for phase A2.

Not implemented. This module calculates nothing yet.

Planned responsibility
    Deterministic, documented transformations of validated observations:
    aggregation from daily values to growing-season and annual summaries,
    derived variables such as reference evapotranspiration, and the ranking of
    past seasons that later defines dry, typical and wet historical scenarios.
    Every transformation is recorded in the value's provenance.

Planned interface (subject to change in A2)
    aggregate(series, resolution) -> models.ObservationSeries
    rank_periods(series, baseline) -> ranked historical periods

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
