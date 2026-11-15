"""The data service: where a response comes from, and what happens offline.

A stub stands in for the NASA client and counts how often it is asked. One
test at the end loads the real bundled pilot dataset from ``data/demo``.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from src import data_service
from src.config import PROJECT_ROOT
from src.data_service import OfflineDataUnavailableError, load_dataset, load_pilot_dataset
from src.data_validation import IssueSeverity, StructuralValidationError, ValidationLevel
from src.models import DataOrigin
from src.nasa_cache import ResponseCache
from src.nasa_client import NasaDataError, PowerRequestError, PowerUnavailableError
from src.pilot_sites import PILOT_SITE

PILOT_FINGERPRINT = "1c2ed230e2661199ac278e4ac68b179c4b5750284091c094745de4a920e0edaf"


class StubClient:
    """Stands in for the NASA client. ``reply`` is a retrieval or an exception."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def fetch(self, request):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


class ForbiddenClient:
    """Fails the test if anything tries to use the network."""

    def fetch(self, request):
        raise AssertionError("the network was contacted")


def issue_codes(dataset) -> list[str]:
    return [issue.code for issue in dataset.quality.issues]


@pytest.fixture
def stores(data_settings):
    """Empty cache and bundled stores matching ``data_settings()``."""
    settings = data_settings()
    return (
        ResponseCache(settings.nasa_cache_path, ttl=None),
        ResponseCache(settings.nasa_demo_path, ttl=None, origin=DataOrigin.BUNDLED),
    )


# --- Online: cache first, then network ----------------------------------------------


def test_first_request_uses_the_network_and_is_cached(data_settings, recorded_request, recorded_retrieval):
    settings, client = data_settings(), StubClient(recorded_retrieval)
    dataset = load_dataset(recorded_request, settings=settings, client=client, site_name="Fixture site")
    assert client.calls == 1
    assert dataset.provenance.origin is DataOrigin.NETWORK
    assert dataset.site_name == "Fixture site" and dataset.quality.accepted
    assert (settings.nasa_cache_path / f"{recorded_request.cache_key()}.json").is_file()


def test_repeated_request_is_served_from_cache_without_a_second_call(data_settings, recorded_request, recorded_retrieval):
    settings, client = data_settings(), StubClient(recorded_retrieval)
    first = load_dataset(recorded_request, settings=settings, client=client)
    second = load_dataset(recorded_request, settings=settings, client=client)
    third = load_dataset(recorded_request, settings=settings, client=ForbiddenClient())
    assert client.calls == 1  # no duplicate request to NASA
    assert second.provenance.origin is DataOrigin.CACHE and third.provenance.origin is DataOrigin.CACHE
    assert second.provenance.payload_sha256 == first.provenance.payload_sha256
    assert second.provenance.retrieved_at == first.provenance.retrieved_at  # original retrieval time kept
    assert [s.observations for s in second.series] == [s.observations for s in first.series]


def test_force_refresh_bypasses_the_cache(data_settings, recorded_request, recorded_retrieval):
    settings, client = data_settings(), StubClient(recorded_retrieval)
    load_dataset(recorded_request, settings=settings, client=client)
    refreshed = load_dataset(recorded_request, settings=settings, client=client, force_refresh=True)
    assert client.calls == 2 and refreshed.provenance.origin is DataOrigin.NETWORK


def test_expired_cache_entry_is_requested_again(data_settings, recorded_request, recorded_retrieval):
    settings = data_settings(nasa_cache_ttl_hours=0.0001)  # the recorded response is hours old
    client = StubClient(recorded_retrieval)
    ResponseCache(settings.nasa_cache_path).put(recorded_retrieval)
    dataset = load_dataset(recorded_request, settings=settings, client=client)
    assert client.calls == 1 and dataset.provenance.origin is DataOrigin.NETWORK


def test_corrupted_cache_entry_is_replaced_and_reported(data_settings, recorded_request, recorded_retrieval):
    settings, client = data_settings(), StubClient(recorded_retrieval)
    cache = ResponseCache(settings.nasa_cache_path)
    cache.put(recorded_retrieval).write_text("damaged", encoding="utf-8")

    dataset = load_dataset(recorded_request, settings=settings, client=client)
    assert client.calls == 1 and dataset.provenance.origin is DataOrigin.NETWORK
    issue = next(item for item in dataset.quality.issues if item.code == "stored_response_unusable")
    assert issue.level is ValidationLevel.SERVICE and issue.severity is IssueSeverity.WARNING
    assert cache.get(recorded_request, allow_expired=True) is not None  # healthy again


def test_unverified_responses_are_never_cached(data_settings, recorded_request, make_retrieval):
    settings = data_settings()
    broken = make_retrieval(lambda payload: payload["header"].pop("fill_value"))
    with pytest.raises(StructuralValidationError):
        load_dataset(recorded_request, settings=settings, client=StubClient(broken))
    assert not list(settings.nasa_cache_path.glob("*.json")) if settings.nasa_cache_path.exists() else True


def test_cache_write_failure_does_not_lose_the_data(tmp_path, data_settings, recorded_request, recorded_retrieval):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the cache folder should be", encoding="utf-8")
    settings = data_settings(nasa_cache_directory=blocker / "cache")
    dataset = load_dataset(recorded_request, settings=settings, client=StubClient(recorded_retrieval))
    assert dataset.provenance.origin is DataOrigin.NETWORK and dataset.quality.accepted
    assert "cache_write_failed" in issue_codes(dataset)


def test_completeness_threshold_comes_from_settings(data_settings, recorded_request, recorded_retrieval):
    settings = data_settings(nasa_min_completeness_percent=75)
    dataset = load_dataset(recorded_request, settings=settings, client=StubClient(recorded_retrieval))
    assert dataset.quality.min_completeness_percent == 75


# --- Online: when NASA cannot be reached --------------------------------------------


def test_unreachable_service_falls_back_to_an_expired_cache_entry(data_settings, recorded_request, recorded_retrieval):
    settings = data_settings(nasa_cache_ttl_hours=0.0001)
    ResponseCache(settings.nasa_cache_path).put(recorded_retrieval)
    client = StubClient(PowerUnavailableError("fixture: service down"))
    dataset = load_dataset(recorded_request, settings=settings, client=client)
    assert client.calls == 1
    assert dataset.provenance.origin is DataOrigin.CACHE
    issue = next(item for item in dataset.quality.issues if item.code == "service_unreachable_fallback")
    assert "older cached response" in issue.message and "14 Nov 2026" in issue.message


def test_unreachable_service_falls_back_to_bundled_data(data_settings, recorded_request, recorded_retrieval, stores):
    stores[1].put(recorded_retrieval)
    dataset = load_dataset(
        recorded_request, settings=data_settings(), client=StubClient(PowerUnavailableError("fixture: down"))
    )
    assert dataset.provenance.origin is DataOrigin.BUNDLED
    assert "bundled dataset" in dataset.quality.warnings[0].message


def test_unreachable_service_with_nothing_stored_fails_clearly(data_settings, recorded_request):
    client = StubClient(PowerUnavailableError("fixture: service down"))
    with pytest.raises(PowerUnavailableError, match="service down"):
        load_dataset(recorded_request, settings=data_settings(), client=client)


def test_a_rejected_request_is_never_papered_over_with_stored_data(data_settings, recorded_request, recorded_retrieval, stores):
    stores[1].put(recorded_retrieval)
    client = StubClient(PowerRequestError("fixture: HTTP 422"))
    with pytest.raises(PowerRequestError):
        load_dataset(recorded_request, settings=data_settings(), client=client, force_refresh=True)


# --- Offline mode --------------------------------------------------------------------


@pytest.fixture
def no_client_allowed(monkeypatch):
    def refuse(settings):
        raise AssertionError("offline mode tried to create a network client")

    monkeypatch.setattr(data_service, "make_client", refuse)


def test_offline_mode_reads_the_cache_without_any_network(data_settings, recorded_request, recorded_retrieval, no_client_allowed):
    settings = data_settings(offline_demo_mode=True)
    ResponseCache(settings.nasa_cache_path).put(recorded_retrieval)
    dataset = load_dataset(recorded_request, settings=settings)
    assert dataset.provenance.origin is DataOrigin.CACHE and dataset.quality.accepted
    assert dataset.provenance.request_url == recorded_retrieval.url  # provenance preserved
    assert dataset.provenance.payload_sha256 == recorded_retrieval.payload_sha256


def test_offline_mode_accepts_an_expired_cache_entry_and_says_so(data_settings, recorded_request, recorded_retrieval, no_client_allowed):
    settings = data_settings(offline_demo_mode=True, nasa_cache_ttl_hours=0.0001)
    ResponseCache(settings.nasa_cache_path).put(recorded_retrieval)
    dataset = load_dataset(recorded_request, settings=settings)
    assert dataset.provenance.origin is DataOrigin.CACHE
    assert "cache_expired_offline" in issue_codes(dataset)


def test_offline_mode_reads_bundled_data(data_settings, recorded_request, recorded_retrieval, stores, no_client_allowed):
    stores[1].put(recorded_retrieval)
    dataset = load_dataset(recorded_request, settings=data_settings(offline_demo_mode=True), client=ForbiddenClient())
    assert dataset.provenance.origin is DataOrigin.BUNDLED
    assert dataset.provenance.retrieved_at == recorded_retrieval.retrieved_at


def test_offline_mode_fails_clearly_when_nothing_is_stored(data_settings, recorded_request, no_client_allowed):
    with pytest.raises(OfflineDataUnavailableError) as failure:
        load_dataset(recorded_request, settings=data_settings(offline_demo_mode=True), client=ForbiddenClient())
    message = str(failure.value)
    assert "Offline mode is on" in message and "OFFLINE_DEMO_MODE=false" in message
    assert "2020-01-01 to 2020-03-31" in message
    assert isinstance(failure.value, NasaDataError)


def test_offline_mode_refuses_to_refresh(data_settings, recorded_request, recorded_retrieval, stores, no_client_allowed):
    stores[1].put(recorded_retrieval)
    with pytest.raises(OfflineDataUnavailableError, match="cannot be refreshed"):
        load_dataset(recorded_request, settings=data_settings(offline_demo_mode=True), force_refresh=True)


def test_offline_mode_skips_a_corrupted_cache_and_uses_bundled_data(data_settings, recorded_request, recorded_retrieval, stores, no_client_allowed):
    stores[0].put(recorded_retrieval).write_text("damaged", encoding="utf-8")
    stores[1].put(recorded_retrieval)
    dataset = load_dataset(recorded_request, settings=data_settings(offline_demo_mode=True))
    assert dataset.provenance.origin is DataOrigin.BUNDLED
    assert "stored_response_unusable" in issue_codes(dataset)


def test_offline_mode_never_invents_data_when_stores_are_corrupted(data_settings, recorded_request, recorded_retrieval, stores, no_client_allowed):
    stores[0].put(recorded_retrieval).write_text("damaged", encoding="utf-8")
    with pytest.raises(OfflineDataUnavailableError):
        load_dataset(recorded_request, settings=data_settings(offline_demo_mode=True))


# --- Invalidation and bundling ------------------------------------------------------


def test_manual_invalidation_forces_a_new_request(data_settings, recorded_request, recorded_retrieval):
    settings, client = data_settings(), StubClient(recorded_retrieval)
    load_dataset(recorded_request, settings=settings, client=client)
    assert data_service.invalidate(recorded_request, settings=settings) is True
    assert data_service.invalidate(recorded_request, settings=settings) is False
    load_dataset(recorded_request, settings=settings, client=client)
    assert client.calls == 2


def test_only_cached_and_accepted_responses_can_be_bundled(data_settings, recorded_request, recorded_retrieval, make_retrieval):
    settings = data_settings()
    with pytest.raises(NasaDataError, match="nothing is cached"):
        data_service.save_as_bundled(recorded_request, settings=settings)

    ResponseCache(settings.nasa_cache_path).put(recorded_retrieval)
    written = data_service.save_as_bundled(recorded_request, settings=settings)
    assert written.endswith(f"{recorded_request.cache_key()}.json")
    offline = load_dataset(recorded_request, settings=data_settings(offline_demo_mode=True, nasa_cache_directory=settings.nasa_cache_path.parent / "empty"))
    assert offline.provenance.origin is DataOrigin.BUNDLED

    def blank_everything(payload):
        for key in payload["properties"]["parameter"]["T2M"]:
            payload["properties"]["parameter"]["T2M"][key] = -999.0

    ResponseCache(settings.nasa_cache_path).put(make_retrieval(blank_everything))
    with pytest.raises(NasaDataError, match="not accepted"):
        data_service.save_as_bundled(recorded_request, settings=settings)


# --- Command line -------------------------------------------------------------------


def test_cli_reports_an_invalid_request_without_contacting_nasa(capsys):
    code = data_service.main(["fetch", "--lat", "95", "--lon", "0", "--start", "2020-01-01", "--end", "2020-01-02"])
    assert code == 1
    assert "Invalid request" in capsys.readouterr().err


def test_cli_shows_the_bundled_pilot_dataset_offline(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OFFLINE_DEMO_MODE", "true")
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", str(tmp_path / "cache"))
    assert data_service.main(["pilot"]) == 0
    output = capsys.readouterr().out
    assert "Katumani" in output and "from bundled" in output
    assert "Accepted:    yes" in output and "9131 days, UTC" in output
    assert "precipitation" in output and "100.00%" in output


def test_cli_reports_missing_offline_data_clearly(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OFFLINE_DEMO_MODE", "true")
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", str(tmp_path / "cache"))
    monkeypatch.setenv("NASA_DEMO_DIRECTORY", str(tmp_path / "demo"))
    assert data_service.main(["pilot"]) == 1
    assert "Offline mode is on" in capsys.readouterr().err


def test_cli_can_invalidate_one_request(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", str(tmp_path / "cache"))
    arguments = ["fetch", "--lat", "-1.58", "--lon", "37.24", "--start", "2020-01-01", "--end", "2020-03-31", "--invalidate"]
    assert data_service.main(arguments) == 0
    assert "Nothing was cached" in capsys.readouterr().out


# --- Independence -------------------------------------------------------------------


def test_data_layer_does_not_depend_on_the_interface_or_ai_services():
    script = (
        "import sys, src.data_service, src.data_processing;"
        "loaded=[name for name in ('streamlit','openai') if name in sys.modules];"
        "sys.exit(1 if loaded else 0)"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=PROJECT_ROOT, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr.decode()


# --- The real bundled pilot dataset -------------------------------------------------


def test_bundled_pilot_dataset_is_real_complete_and_unaltered(make_settings, tmp_path, no_client_allowed):
    settings = make_settings(offline_demo_mode=True, nasa_cache_directory=tmp_path / "cache")
    dataset = load_pilot_dataset(settings=settings)
    provenance = dataset.provenance

    assert provenance.origin is DataOrigin.BUNDLED
    assert provenance.payload_sha256 == PILOT_FINGERPRINT  # as documented in data/demo/README.md
    assert provenance.service_version == "v2.10.3"
    assert provenance.request_url.startswith("https://power.larc.nasa.gov/api/temporal/daily/point?")
    assert "time-standard=UTC" in provenance.request_url
    assert dataset.site_name == PILOT_SITE.name

    assert dataset.quality.accepted and dataset.quality.expected_days == 9131
    assert len(dataset.series) == 6
    for series in dataset.series:
        assert len(series.observations) == 9131 and series.missing_count == 0
    assert dataset.quality.lowest_completeness_percent == 100.0
    assert dataset.quality.issues == ()
