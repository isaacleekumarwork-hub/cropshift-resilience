"""Local storage — placeholder, planned for phase A5.

Not implemented. No database is created or opened.

Planned responsibility
    Save and reload ``models.ComparisonResult`` objects as JSON in a local
    SQLite file at ``Settings.database_file``, so a comparison can be reopened
    or exported later. Used only where persistence is genuinely needed.

Planned interface (subject to change in A5)
    save_comparison(result) -> None
    load_comparison(comparison_id) -> models.ComparisonResult

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
