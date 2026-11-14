"""NASA data retrieval — placeholder, planned for phase A2.

Not implemented. This module retrieves nothing and contains no data.

Planned responsibility
    Request daily point time series from the NASA POWER API (which serves
    MERRA-2 meteorology, CERES solar radiation and GPM IMERG precipitation),
    cache raw responses under ``Settings.nasa_cache_path`` and return them
    untouched for validation. In offline demo mode, read only from the cache
    or bundled demo files and make no network request.

Planned interface (subject to change in A2)
    fetch_daily_point(location, variables, start, end) -> raw response + metadata
    describe_source(source_id) -> models.DataSourceMetadata

Boundaries
    No unit conversion, gap handling or aggregation here; those belong to
    data_validation and data_processing.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
