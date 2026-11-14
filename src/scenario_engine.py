"""Scenario engine — placeholder, planned for phase A4.

Not implemented. This module produces no indicators and no results.

Planned responsibility
    For one rotation and one historical scenario, calculate transparent
    indicators from validated environmental data, soil information and cited
    crop characteristics. Calculations are deterministic: the same inputs
    always give the same result, with no random numbers and no AI service.
    Indicators are always labelled as modeled or derived, never as observed.

Planned interface (subject to change in A4)
    run_scenario(rotation, scenario, soil, crops, observations) -> models.ScenarioResult

Out of scope
    Yield prediction, fertiliser prescriptions and weather forecasting.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""
