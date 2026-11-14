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

__version__ = "0.1.0"

PROJECT_NAME = "CropShift RESILIENCE"
CHALLENGE_NAME = "Field Shift: Adapting Farms with NASA Data"
EVENT_NAME = "NASA Space Apps Challenge 2026"
CURRENT_PHASE = "A1"


class Phase(NamedTuple):
    """One implementation phase of the Balanced Architecture plan."""

    code: str
    title: str
    status: str  # "complete", "in progress" or "not started"


class Module(NamedTuple):
    """One module in ``src/`` and whether it does anything yet."""

    name: str
    phase: str
    responsibility: str
    implemented: bool


PHASES: tuple[Phase, ...] = (
    Phase("A1", "Repository, requirements, architecture and foundation", "complete"),
    Phase("A2", "NASA data ingestion", "not started"),
    Phase("A3", "Agronomic knowledge base", "not started"),
    Phase("A4", "Scenario and comparison engine", "not started"),
    Phase("A5", "Complete Streamlit interface", "not started"),
    Phase("A6", "Optional OpenAI explanations", "not started"),
    Phase("A7", "Optional Manus research reports", "not started"),
    Phase("A8", "Final validation", "not started"),
    Phase("A9", "Demonstration and submission", "not started"),
)

MODULES: tuple[Module, ...] = (
    Module("config", "A1", "Typed settings loaded from the environment", True),
    Module("models", "A1", "Scientific data contracts", True),
    Module("nasa_client", "A2", "Retrieve NASA data and cache responses", False),
    Module("data_validation", "A2", "Check retrieved data and flag missing values", False),
    Module("data_processing", "A2", "Aggregate and derive environmental series", False),
    Module("crop_knowledge", "A3", "Cited crop characteristics and rotation rules", False),
    Module("scenario_engine", "A4", "Deterministic rotation-by-scenario calculations", False),
    Module("comparison_engine", "A4", "Compare rotations against farmer priorities", False),
    Module("uncertainty", "A4", "Describe confidence, assumptions and limitations", False),
    Module("visualizations", "A5", "Accessible Plotly charts", False),
    Module("ui_state", "A5", "Streamlit session state helpers", False),
    Module("persistence", "A5", "Save and reload comparisons in SQLite", False),
    Module("report_service", "A5", "Export a comparison summary", False),
    Module("openai_service", "A6", "Optional plain-language explanations", False),
    Module("manus_service", "A7", "Optional asynchronous research reports", False),
)
