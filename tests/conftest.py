"""Shared, deterministic fixtures.

No test touches the network, the developer's real ``.env`` file or the
developer's environment variables.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src import config, models

SETTING_NAMES = (
    "OFFLINE_DEMO_MODE",
    "ENABLE_OPENAI",
    "ENABLE_MANUS",
    "NASA_REQUEST_TIMEOUT",
    "NASA_CACHE_DIRECTORY",
    "DATABASE_PATH",
    "LOG_LEVEL",
    "OPENAI_API_KEY",
    "MANUS_API_KEY",
)

# A fixed moment during the hackathon, used wherever a timestamp is needed.
FIXED_TIME = datetime(2026, 11, 14, 2, 0, 0, tzinfo=timezone.utc)
FIXED_DAY = date(2024, 7, 1)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch):
    """Start every test with none of the app's variables set and no cached settings."""
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def make_settings():
    """Build settings from the current environment only, ignoring any .env file."""

    def _make(**overrides):
        return config.Settings(_env_file=None, **overrides)

    return _make


@pytest.fixture
def location() -> models.GeoLocation:
    return models.GeoLocation(latitude=42.03, longitude=-93.62, name="Test point", country_code="US")


@pytest.fixture
def reanalysis() -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        kind=models.DataKind.REANALYSIS,
        source_id="test-reanalysis",
        source_name="Test reanalysis source",
        source_version="v0",
        citation="Test citation (fixture, not a real dataset)",
        retrieved_at=FIXED_TIME,
        spatial_resolution="0.5° x 0.625°",
        temporal_resolution=models.TemporalResolution.DAILY,
        time_standard=models.TimeStandard.UTC,
    )


@pytest.fixture
def literature() -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        kind=models.DataKind.LITERATURE_VALUE,
        source_id="test-reference",
        source_name="Test reference",
        citation="Test citation (fixture, not a real publication)",
    )


@pytest.fixture
def user_reported() -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        kind=models.DataKind.USER_REPORTED,
        source_id="user",
        source_name="Entered by the user",
    )


@pytest.fixture
def modeled() -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        kind=models.DataKind.MODELED,
        source_id="test-engine",
        source_name="Test engine",
        source_version="0.0",
        transformations=("fixture calculation",),
    )


@pytest.fixture
def uncertainty() -> models.UncertaintyStatement:
    return models.UncertaintyStatement(
        confidence=models.ConfidenceLevel.NOT_ASSESSED,
        confidence_basis="Fixture: nothing has been assessed.",
        limitations=("Fixture limitation.",),
    )


@pytest.fixture
def make_observation(location, reanalysis):
    """Factory for a valid daily precipitation observation; override any field."""

    def _make(**overrides):
        fields = dict(
            variable="precipitation",
            value=3.2,
            unit=models.Unit.MILLIMETRE_PER_DAY,
            provenance=reanalysis,
            location=location,
            period_start=FIXED_DAY,
            period_end=FIXED_DAY,
            temporal_resolution=models.TemporalResolution.DAILY,
        )
        fields.update(overrides)
        return models.EnvironmentalObservation(**fields)

    return _make


@pytest.fixture
def test_indicator():
    """Temporarily declare an indicator variable; real ones arrive in phase A4."""
    definition = models.register_variable(
        models.VariableDefinition(
            name="test_only_indicator",
            domain=models.VariableDomain.INDICATOR,
            unit=models.Unit.MILLIMETRE,
            description="Fixture indicator with no scientific meaning",
            valid_min=0,
        )
    )
    yield definition
    models.unregister_variable(definition.name)
