"""Shared, deterministic fixtures.

No routine test touches the network, the developer's real ``.env`` file, the
developer's environment variables or the developer's local cache. The only
tests allowed to contact NASA are marked ``live`` and run only on request
(``pytest --run-live``).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from src import config, models
from src.nasa_client import PowerRequest, PowerRetrieval, payload_digest

SETTING_NAMES = (
    "OFFLINE_DEMO_MODE",
    "ENABLE_OPENAI",
    "ENABLE_MANUS",
    "NASA_REQUEST_TIMEOUT",
    "NASA_CACHE_DIRECTORY",
    "NASA_POWER_BASE_URL",
    "NASA_MAX_RETRIES",
    "NASA_CACHE_TTL_HOURS",
    "NASA_DEMO_DIRECTORY",
    "NASA_MIN_COMPLETENESS_PERCENT",
    "DATABASE_PATH",
    "LOG_LEVEL",
    "OPENAI_API_KEY",
    "MANUS_API_KEY",
)

# A fixed moment during the hackathon, used wherever a timestamp is needed.
FIXED_TIME = datetime(2026, 11, 14, 2, 0, 0, tzinfo=timezone.utc)
FIXED_DAY = date(2024, 7, 1)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
RECORDED_RESPONSE = FIXTURE_DIR / "power_daily_katumani_2020q1.json"
"""A real NASA POWER response recorded on 14 Nov 2026. See fixtures/README.md."""


# --- Live tests are opt-in -----------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="also run tests that contact the real NASA POWER service",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-live"):
        return
    skip = pytest.mark.skip(reason="contacts NASA; run with --run-live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def block_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any real HTTP request fail loudly unless the test is marked ``live``."""
    if request.node.get_closest_marker("live"):
        return

    def refuse(self: httpx.HTTPTransport, outgoing: httpx.Request) -> httpx.Response:
        raise AssertionError(f"a routine test tried to contact {outgoing.url.host}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)


# --- Environment isolation -------------------------------------------------------


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
def data_settings(tmp_path: Path, make_settings):
    """Settings whose cache and demo folders are empty temporary folders."""

    def _make(**overrides):
        fields = dict(
            nasa_cache_directory=tmp_path / "cache",
            nasa_demo_directory=tmp_path / "demo",
            nasa_max_retries=0,
        )
        fields.update(overrides)
        return make_settings(**fields)

    return _make


# --- Recorded NASA response -------------------------------------------------------


@pytest.fixture(scope="session")
def recorded_envelope() -> dict[str, Any]:
    """The recorded response as stored on disk. Never modify this object."""
    return json.loads(RECORDED_RESPONSE.read_text(encoding="utf-8"))


@pytest.fixture
def recorded_request(recorded_envelope) -> PowerRequest:
    return PowerRequest(**recorded_envelope["request"])


@pytest.fixture
def make_retrieval(recorded_envelope, recorded_request) -> Callable[..., PowerRetrieval]:
    """Build a retrieval from the recorded response, optionally altering a copy.

    ``alter`` receives a private copy of the response. Anything it changes is a
    test input, not NASA data.
    """

    def _make(
        alter: Callable[[dict[str, Any]], None] | None = None,
        *,
        request: PowerRequest | None = None,
        retrieved_at: datetime | None = None,
        origin: models.DataOrigin = models.DataOrigin.NETWORK,
    ) -> PowerRetrieval:
        payload = copy.deepcopy(recorded_envelope["payload"])
        if alter is not None:
            alter(payload)
        return PowerRetrieval(
            request=request or recorded_request,
            url=recorded_envelope["url"],
            status_code=200,
            retrieved_at=retrieved_at or datetime.fromisoformat(recorded_envelope["retrieved_at"]),
            attempts=1,
            payload=payload,
            payload_sha256=payload_digest(payload),
            origin=origin,
        )

    return _make


@pytest.fixture
def recorded_retrieval(make_retrieval) -> PowerRetrieval:
    return make_retrieval()


def daily(payload: dict[str, Any], parameter: str) -> dict[str, Any]:
    """Shortcut to one parameter's date-to-value mapping inside a response."""
    return payload["properties"]["parameter"][parameter]


# --- Knowledge base (A3) ----------------------------------------------------------


@pytest.fixture(scope="session")
def kb():
    """The real knowledge base, loaded once from ``data/knowledge``."""
    from src.crop_knowledge import load_knowledge_base

    return load_knowledge_base()


@pytest.fixture(scope="session")
def _raw_knowledge() -> dict[str, Any]:
    from src.crop_knowledge import read_knowledge_files

    return read_knowledge_files()


@pytest.fixture
def raw(_raw_knowledge) -> dict[str, Any]:
    """A private copy of the raw knowledge data for a test to damage."""
    return copy.deepcopy(_raw_knowledge)


def find(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    """Return the first record in a raw list whose ``key`` equals ``value``."""
    return next(item for item in items if item[key] == value)


# --- Evidence audit and engine (A4) ---------------------------------------------------


@pytest.fixture(scope="session")
def gate(kb):
    """The real evidence gate, built from the knowledge base and the A4 audit."""
    from src.evidence_audit import load_evidence_gate

    return load_evidence_gate(kb)


@pytest.fixture(scope="session")
def _raw_audit() -> dict[str, Any]:
    from src.evidence_audit import read_audit_file

    return read_audit_file()


@pytest.fixture
def raw_audit(_raw_audit) -> dict[str, Any]:
    """A private copy of the raw audit file for a test to damage."""
    return copy.deepcopy(_raw_audit)


@pytest.fixture(scope="session")
def pilot_dataset(tmp_path_factory):
    """The bundled real NASA pilot dataset from ``data/demo``, read offline.

    The cache folder is an empty temporary folder, so the data can only come
    from the verified bundled response; no network request is possible.
    """
    from src.config import Settings
    from src.data_service import load_pilot_dataset

    settings = Settings(
        _env_file=None,
        offline_demo_mode=True,
        nasa_cache_directory=tmp_path_factory.mktemp("empty-cache"),
    )
    return load_pilot_dataset(settings=settings)


# --- A1 fixtures ------------------------------------------------------------------


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
