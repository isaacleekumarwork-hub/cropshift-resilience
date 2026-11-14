"""Crop knowledge base — placeholder, planned for phase A3.

Not implemented. This module contains no crop data and no agronomic rules.

Planned responsibility
    Hold cited ``models.CropProfile`` records for the supported crops and the
    candidate ``models.CropRotation`` options for each pilot region. Every
    parameter must carry a citation; a parameter with no published source is
    left out and reported as an information gap rather than estimated.

Planned interface (subject to change in A3)
    get_crop(crop_id) -> models.CropProfile
    list_rotations(region_id) -> tuple[models.CropRotation, ...]

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
