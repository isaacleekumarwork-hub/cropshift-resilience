"""Uncertainty reporting — placeholder, planned for phase A4.

Not implemented. This module assesses nothing yet.

Planned responsibility
    Build ``models.UncertaintyStatement`` objects from facts the system
    actually knows: how much input data was missing, how far two NASA
    precipitation estimates disagree, how coarse the data grid is compared
    with a field, and which crop parameters lacked a source. Confidence is
    never stated without the reason for it.

Planned interface (subject to change in A4)
    assess(inputs, result) -> models.UncertaintyStatement

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
