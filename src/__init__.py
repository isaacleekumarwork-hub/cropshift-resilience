"""CropShift RESILIENCE — crop-rotation decision support built on NASA Earth data.

This package holds the application's building blocks. The table below is the
single honest record of what exists: the Streamlit page reads it to show the
build status, and the tests check it against the files actually present.

AI assistance: this code was drafted with Claude Code (Anthropic) under the
participant's direction during the 2026 NASA Space Apps Challenge. See
docs/provenance.md.
"""

from __future__ import annotations

from typing import NamedTuple

__version__ = "0.9.0"

PROJECT_NAME = "CropShift RESILIENCE"
CHALLENGE_NAME = "Field Shift: Adapting Farms with NASA Data"
EVENT_NAME = "NASA Space Apps Challenge 2026"
CURRENT_PHASE = "A9"


class Phase(NamedTuple):
    """One implementation phase of the Balanced Architecture plan."""

    code: str
    title: str
    status: str  # "complete", "in progress", "deferred" or "not started"


class Module(NamedTuple):
    """One module in ``src/`` and whether it does anything yet."""

    name: str
    phase: str
    responsibility: str
    implemented: bool
    deferred: str | None = None  # why a placeholder was deliberately not built in its phase


PHASES: tuple[Phase, ...] = (
    Phase("A1", "Repository, requirements, architecture and foundation", "complete"),
    Phase("A2", "NASA data ingestion, validation, provenance and caching", "complete"),
    Phase("A3", "Evidence-based agronomic knowledge base", "complete"),
    Phase("A4", "Scenario and comparison engine", "complete"),
    Phase("A5", "Complete Streamlit interface", "complete"),
    Phase("A6", "Optional OpenAI explanations", "deferred"),
    Phase("A7", "Optional Manus research reports", "deferred"),
    Phase("A8", "Final validation", "complete"),
    Phase("A9", "Demonstration and submission", "in progress"),
)

MODULES: tuple[Module, ...] = (
    Module("config", "A1", "Typed settings loaded from the environment", True),
    Module("models", "A1", "Scientific data contracts", True),
    Module("nasa_client", "A2", "Validated requests to the NASA POWER Daily API with bounded retries", True),
    Module("nasa_cache", "A2", "Verified local cache of NASA responses; reads bundled demo data", True),
    Module("pilot_sites", "A2", "The documented pilot location and historical period", True),
    Module("data_validation", "A2", "Structural, physical and completeness checks; typed observations", True),
    Module("data_processing", "A2", "Daily tables, monthly totals and means, descriptive summaries", True),
    Module("data_service", "A2", "Entry point: cache, offline mode and network in one call", True),
    Module("crop_knowledge", "A3", "Cited crop profiles, rotation relationships, constraints and evidence registry", True),
    Module("evidence_audit", "A4", "Evidence audit of every source and the gate every calculation passes", True),
    Module("soil_inputs", "A4", "Validated soil inputs with provenance for the three soil mappings", True),
    Module("season_config", "A4", "Provisional pilot configuration, season windows and rotation strategies", True),
    Module("scenario_engine", "A4", "Dry, typical and wet past seasons from the NASA record", True),
    Module("comparison_engine", "A4", "Side-by-side rotation indicators, constraints and farmer priorities", True),
    Module("uncertainty", "A4", "Confidence, limitations and six-part explanations for every indicator", True),
    Module("visualizations", "A5", "Accessible Plotly charts built from engine results", True),
    Module("ui_state", "A5", "Widget values to typed engine inputs; soil form validation", True),
    Module(
        "persistence", "A5", "Save and reload comparisons in SQLite", False,
        deferred="Not built: the A5 brief says not to persist user inputs without an explicit need; downloads cover keeping a result.",
    ),
    Module("report_service", "A5", "Export a comparison as Markdown and JSON", True),
    Module("ui_theme", "A5", "Starry Night visual theme: stylesheet, background artwork and chart restyling", True),
    Module("openai_service", "A6", "Optional plain-language explanations", False),
    Module("manus_service", "A7", "Optional asynchronous research reports", False),
)
