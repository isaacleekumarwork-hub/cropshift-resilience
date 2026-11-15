"""NASA POWER client: request validation, URL construction, retries and errors.

Every HTTP exchange here is simulated with ``httpx.MockTransport``. No test in
this file contacts NASA.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from src import nasa_client
from src.models import DataOrigin, TimeStandard
from src.nasa_client import (
    BACKOFF_CAP_SECONDS,
    RETRY_AFTER_CAP_SECONDS,
    PowerClient,
    PowerRequest,
    PowerRequestError,
    PowerResponseError,
    PowerUnavailableError,
)
from src.pilot_sites import PILOT_SITE

BASE = dict(latitude=-1.58, longitude=37.24, start=date(2020, 1, 1), end=date(2020, 3, 31))


def request(**overrides) -> PowerRequest:
    return PowerRequest(**{**BASE, **overrides})


class Recorder:
    """A fake NASA server: replies from a script and records what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[httpx.Request] = []

    def __call__(self, incoming: httpx.Request) -> httpx.Response:
        self.requests.append(incoming)
        reply = self.replies[min(len(self.requests) - 1, len(self.replies) - 1)]
        if isinstance(reply, Exception):
            raise reply
        return reply


def client_for(recorder: Recorder, *, max_retries: int = 3, jitter: float = 1.0):
    sleeps: list[float] = []
    client = PowerClient(
        max_retries=max_retries,
        transport=httpx.MockTransport(recorder),
        sleep=sleeps.append,
        jitter=lambda: jitter,
    )
    return client, sleeps


def ok(recorded_envelope) -> httpx.Response:
    return httpx.Response(200, json=recorded_envelope["payload"])


# --- Coordinate validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"latitude": 90.01},
        {"latitude": -90.01},
        {"longitude": 180.01},
        {"longitude": -180.01},
        {"latitude": float("nan")},
        {"longitude": float("inf")},
        {"latitude": "north"},
    ],
)
def test_invalid_coordinates_are_rejected(fields):
    with pytest.raises(ValidationError):
        request(**fields)


def test_coordinates_are_normalised():
    built = request(latitude=-1.5800004, longitude=37.2399996)
    assert (built.latitude, built.longitude) == (-1.58, 37.24)
    assert str(request(latitude=-0.00001).latitude) == "0.0"  # no negative zero


@pytest.mark.parametrize("latitude,longitude", [(90, 180), (-90, -180), (0, 0)])
def test_boundary_coordinates_are_accepted(latitude, longitude):
    assert request(latitude=latitude, longitude=longitude).latitude == latitude


# --- Date validation ---------------------------------------------------------------


def test_end_before_start_is_rejected():
    with pytest.raises(ValidationError, match="end must not be before start"):
        request(start=date(2020, 2, 1), end=date(2020, 1, 1))


def test_future_dates_are_rejected():
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=2)
    with pytest.raises(ValidationError, match="history only"):
        request(end=tomorrow)


def test_dates_before_the_record_are_rejected():
    with pytest.raises(ValidationError, match="available from 1981-01-01"):
        request(start=date(1980, 12, 31), parameters=("T2M",))
    with pytest.raises(ValidationError, match="ALLSKY_SFC_SW_DWN is available from 1984-01-01"):
        request(start=date(1983, 6, 1))
    assert request(start=date(1981, 1, 1), end=date(1981, 1, 5), parameters=("T2M", "PRECTOTCORR"))


def test_overlong_range_is_rejected(monkeypatch):
    # The whole 42-year solar record fits inside the limit ...
    assert request(start=date(1984, 1, 1), end=date(2025, 12, 31)).expected_days == 15341
    # ... and the limit itself is enforced (lowered here so it can be reached).
    monkeypatch.setattr(nasa_client, "MAX_REQUEST_DAYS", 30)
    with pytest.raises(ValidationError, match="at most 30 days"):
        request()


def test_a_single_day_is_valid():
    assert request(end=date(2020, 1, 1)).expected_days == 1


def test_malformed_dates_are_rejected():
    with pytest.raises(ValidationError):
        request(start="2020-13-01")
    with pytest.raises(ValidationError):
        request(end="yesterday")


# --- Parameter validation ----------------------------------------------------------


def test_parameters_are_normalised():
    built = request(parameters=" t2m , prectotcorr ")
    assert built.parameters == ("PRECTOTCORR", "T2M")
    assert request(parameters=["T2M", "PRECTOTCORR"]) == built


@pytest.mark.parametrize(
    "parameters",
    [("SMAP_SOIL_MOISTURE",), ("T2M", "T2M"), (), ("T2M", "IMERG_PRECTOT"), ("T2M; DROP TABLE",)],
)
def test_unsupported_or_repeated_parameters_are_rejected(parameters):
    with pytest.raises(ValidationError):
        request(parameters=parameters)


def test_only_the_documented_community_and_time_standards_are_accepted():
    with pytest.raises(ValidationError):
        request(community="RE")
    with pytest.raises(ValidationError):
        request(time_standard="GMT")
    assert request(time_standard="LST").time_standard is TimeStandard.LOCAL_SOLAR_TIME


def test_supported_parameters_map_to_registered_variables():
    from src.models import get_variable

    for parameter in nasa_client.POWER_PARAMETERS.values():
        assert get_variable(parameter.variable).unit is parameter.unit
    assert set(nasa_client.CORE_PARAMETERS) <= set(nasa_client.POWER_PARAMETERS)


# --- URL and request construction --------------------------------------------------


def test_query_parameters_are_exact():
    assert request(parameters=("T2M", "PRECTOTCORR")).query_params() == {
        "parameters": "PRECTOTCORR,T2M",
        "community": "AG",
        "longitude": "37.2400",
        "latitude": "-1.5800",
        "start": "20200101",
        "end": "20200331",
        "format": "JSON",
        "time-standard": "UTC",
    }


def test_time_standard_is_always_sent_explicitly():
    assert request().query_params()["time-standard"] == "UTC"
    assert request(time_standard=TimeStandard.LOCAL_SOLAR_TIME).query_params()["time-standard"] == "LST"


def test_url_is_https_and_matches_the_recorded_request(recorded_envelope, recorded_request):
    url = PowerClient().build_url(recorded_request)
    assert url.startswith("https://power.larc.nasa.gov/api/temporal/daily/point?")
    assert url == recorded_envelope["url"]


def test_cache_key_is_stable_and_specific():
    key = request().cache_key()
    assert len(key) == 64 and int(key, 16) >= 0
    assert request(parameters=sorted(request().parameters, reverse=True)).cache_key() == key
    assert request(latitude=-1.58000001).cache_key() == key
    different = [
        request(latitude=-1.59),
        request(longitude=37.25),
        request(start=date(2020, 1, 2)),
        request(end=date(2020, 3, 30)),
        request(parameters=("T2M",)),
        request(time_standard=TimeStandard.LOCAL_SOLAR_TIME),
    ]
    assert len({item.cache_key() for item in different} | {key}) == len(different) + 1


def test_pilot_request_is_valid_and_covers_complete_years():
    pilot = PILOT_SITE.request()
    assert (pilot.start, pilot.end) == (date(2001, 1, 1), date(2025, 12, 31))
    assert pilot.expected_days == 9131
    assert set(nasa_client.CORE_PARAMETERS) <= set(pilot.parameters)
    assert PILOT_SITE.context_is_cited is True  # cited in phase A3
    assert PILOT_SITE.approved is False  # still the A2 proposal, not yet approved


# --- Successful retrieval ----------------------------------------------------------


def test_successful_fetch_returns_the_original_response(recorded_envelope, recorded_request):
    recorder = Recorder(ok(recorded_envelope))
    client, sleeps = client_for(recorder)
    retrieval = client.fetch(recorded_request)

    assert retrieval.payload == recorded_envelope["payload"]
    assert retrieval.payload_sha256 == recorded_envelope["payload_sha256"]
    assert retrieval.origin is DataOrigin.NETWORK
    assert retrieval.status_code == 200 and retrieval.attempts == 1
    assert retrieval.retrieved_at.tzinfo is not None
    assert sleeps == []
    assert len(recorder.requests) == 1
    sent = recorder.requests[0]
    assert sent.method == "GET" and sent.url.scheme == "https"
    assert str(sent.url) == retrieval.url == recorded_envelope["url"]


def test_no_credentials_or_identity_are_sent(recorded_envelope, recorded_request):
    recorder = Recorder(ok(recorded_envelope))
    client_for(recorder)[0].fetch(recorded_request)
    headers = {name.lower() for name in recorder.requests[0].headers}
    assert not headers & {"authorization", "cookie", "x-api-key", "from"}
    assert "user" not in recorder.requests[0].url.params


# --- Retries, rate limits and timeouts ---------------------------------------------


def test_rate_limit_is_retried_and_honours_retry_after(recorded_envelope, recorded_request):
    recorder = Recorder(httpx.Response(429, headers={"Retry-After": "7"}), ok(recorded_envelope))
    client, sleeps = client_for(recorder, jitter=0.0)
    retrieval = client.fetch(recorded_request)
    assert retrieval.attempts == 2
    assert sleeps == [7.0]


def test_retry_after_is_capped(recorded_envelope, recorded_request):
    recorder = Recorder(httpx.Response(429, headers={"Retry-After": "86400"}), ok(recorded_envelope))
    client, sleeps = client_for(recorder)
    client.fetch(recorded_request)
    assert sleeps == [RETRY_AFTER_CAP_SECONDS]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_temporary_server_errors_are_retried_a_bounded_number_of_times(status, recorded_request):
    recorder = Recorder(httpx.Response(status))
    client, sleeps = client_for(recorder, max_retries=3, jitter=1.0)
    with pytest.raises(PowerUnavailableError, match=f"after 4 attempt.*HTTP {status}"):
        client.fetch(recorded_request)
    assert len(recorder.requests) == 4  # one attempt plus three retries, never more
    assert sleeps == [1.0, 2.0, 4.0]  # exponential backoff; no wait after the last attempt


def test_backoff_uses_jitter_and_is_capped():
    low = PowerClient(jitter=lambda: 0.0)
    high = PowerClient(jitter=lambda: 1.0)
    assert low.backoff_seconds(1) == 0.5 and high.backoff_seconds(1) == 1.0
    assert low.backoff_seconds(3) == 2.0 and high.backoff_seconds(3) == 4.0
    assert high.backoff_seconds(50) == BACKOFF_CAP_SECONDS


def test_timeouts_are_retried_then_reported(recorded_envelope, recorded_request):
    recorder = Recorder(httpx.ReadTimeout("slow"), httpx.ConnectTimeout("slow"), ok(recorded_envelope))
    client, sleeps = client_for(recorder)
    assert client.fetch(recorded_request).attempts == 3
    assert len(sleeps) == 2

    always_slow = Recorder(httpx.ReadTimeout("slow"))
    client, _ = client_for(always_slow, max_retries=1)
    with pytest.raises(PowerUnavailableError, match="no response within 30 seconds"):
        client.fetch(recorded_request)
    assert len(always_slow.requests) == 2


def test_connection_failures_are_retried_then_reported(recorded_request):
    recorder = Recorder(httpx.ConnectError("no route"))
    client, _ = client_for(recorder, max_retries=2)
    with pytest.raises(PowerUnavailableError, match="connection problem"):
        client.fetch(recorded_request)
    assert len(recorder.requests) == 3


def test_zero_retries_means_exactly_one_attempt(recorded_request):
    recorder = Recorder(httpx.Response(503))
    client, sleeps = client_for(recorder, max_retries=0)
    with pytest.raises(PowerUnavailableError):
        client.fetch(recorded_request)
    assert len(recorder.requests) == 1 and sleeps == []


@pytest.mark.parametrize("status", [400, 404, 422])
def test_rejected_requests_are_not_retried(status, recorded_request):
    recorder = Recorder(httpx.Response(status, json={"messages": ["Fixture: bad parameter"]}))
    client, sleeps = client_for(recorder)
    with pytest.raises(PowerRequestError, match=f"HTTP {status}.*Fixture: bad parameter"):
        client.fetch(recorded_request)
    assert len(recorder.requests) == 1 and sleeps == []


# --- Malformed responses -------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("<html>Service page</html>", "not valid JSON"),
        ('{"properties": {"parameter": {', "not valid JSON"),
        ("[1, 2, 3]", "not a JSON object"),
        ('{"header": {}}', "properties.parameter"),
        ('{"properties": {"parameter": {}}}', "header"),
        ('{"header": {}, "properties": {"parameter": {"T2M": {"20200101": 1, "20200101": 2}}}}', "repeats the key"),
        ('{"header": {}, "properties": {"parameter": {"T2M": {"20200101": NaN}}}}', "non-numeric constant"),
    ],
)
def test_malformed_responses_raise_clear_errors(body, expected, recorded_request):
    recorder = Recorder(httpx.Response(200, text=body))
    client, sleeps = client_for(recorder)
    with pytest.raises(PowerResponseError, match=expected):
        client.fetch(recorded_request)
    assert len(recorder.requests) == 1 and sleeps == []  # a bad answer is not retried


# --- Client configuration ------------------------------------------------------------


def test_client_refuses_unsafe_configuration():
    with pytest.raises(ValueError, match="https"):
        PowerClient(base_url="http://power.larc.nasa.gov/api/temporal/daily/point")
    with pytest.raises(ValueError, match="timeout"):
        PowerClient(timeout=0)
    with pytest.raises(ValueError, match="max_retries"):
        PowerClient(max_retries=7)
    with pytest.raises(ValueError, match="max_retries"):
        PowerClient(max_retries=-1)


def test_endpoint_is_configurable():
    client = PowerClient(base_url="https://example.org/power/")
    assert client.build_url(request()).startswith("https://example.org/power?")


def test_tls_verification_is_never_disabled():
    source_folder = Path(nasa_client.__file__).parent
    for path in list(source_folder.glob("*.py")) + [source_folder.parent / "app.py"]:
        text = path.read_text(encoding="utf-8")
        assert "verify=False" not in text.replace(" ", ""), path.name


def test_payload_fingerprint_ignores_key_order_but_not_values(recorded_envelope):
    payload = recorded_envelope["payload"]
    reordered = json.loads(json.dumps(payload, sort_keys=True))
    assert nasa_client.payload_digest(reordered) == nasa_client.payload_digest(payload)
    changed = json.loads(json.dumps(payload))
    changed["properties"]["parameter"]["T2M"]["20200101"] += 0.01
    assert nasa_client.payload_digest(changed) != nasa_client.payload_digest(payload)
