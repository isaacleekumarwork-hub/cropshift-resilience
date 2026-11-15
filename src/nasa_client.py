"""Client for the NASA POWER Daily API (single point).

Responsibility
    Build a validated request, send it over HTTPS with bounded retries, and
    return the original response together with what is needed to verify and
    cite it. Nothing else: no unit conversion, gap handling or aggregation.

What this module guarantees
    * Importing it makes no network request.
    * TLS certificate verification is never disabled.
    * A request is attempted at most ``max_retries + 1`` times.
    * Only rate limits, timeouts and temporary server errors are retried.
    * A malformed response raises a clear error; it is never repaired.
    * No credentials are involved, so none can be logged.

Official documentation
    https://power.larc.nasa.gov/docs/services/api/temporal/daily/

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any, Literal

import httpx
from pydantic import AwareDatetime, Field, field_validator, model_validator

from src.config import DEFAULT_NASA_POWER_URL, MAX_NASA_RETRIES
from src.models import Contract, DataKind, DataOrigin, TimeStandard, Unit, get_variable

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Facts about the service (verified against the official documentation and
# the live parameter catalogue on 14 Nov 2026; see docs/data_sources.md)
# --------------------------------------------------------------------------- #

DATASET_ID = "nasa-power-daily-point"
SERVICE_NAME = "NASA POWER Daily API"
OFFICIAL_URL = "https://power.larc.nasa.gov/"
DOCUMENTATION_URL = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"

POWER_RECORD_START = date(1981, 1, 1)
"""First day of daily meteorology in POWER."""

MAX_PARAMETERS_PER_REQUEST = 20
"""Limit stated in the official documentation for a single point."""

MAX_REQUEST_DAYS = 366 * 50
"""Our own upper bound on one request, to keep responses bounded."""

COORDINATE_DECIMALS = 4
"""Coordinates are rounded to about 11 m before a request is built."""

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_CAP_SECONDS = 30.0
RETRY_AFTER_CAP_SECONDS = 60.0

MERRA2_GRID = "0.5° latitude x 0.625° longitude (about 55 km x 70 km at the equator)"
CERES_GRID = "1° latitude x 1° longitude (about 110 km at the equator)"


class PowerParameter(Contract):
    """One POWER parameter and how it maps onto a CropShift variable."""

    name: str = Field(description="Identifier used by the POWER API.")
    variable: str = Field(description="Registered CropShift variable.")
    power_unit: str = Field(description="Unit string POWER returns for the AG community.")
    unit: Unit
    kind: DataKind
    product: str = Field(description="Upstream NASA product that supplies the values.")
    spatial_resolution: str
    record_start: date
    description: str


def _parameter(
    name: str,
    variable: str,
    power_unit: str,
    kind: DataKind,
    product: str,
    grid: str,
    start: date,
    description: str,
) -> PowerParameter:
    return PowerParameter(
        name=name,
        variable=variable,
        power_unit=power_unit,
        unit=get_variable(variable).unit,
        kind=kind,
        product=product,
        spatial_resolution=grid,
        record_start=start,
        description=description,
    )


_MERRA2 = "MERRA-2 reanalysis (GEOS-IT for the most recent months)"
_CERES = "CERES SYN1deg (GEWEX SRB before 2001, FLASHFlux for the most recent months)"

POWER_PARAMETERS: dict[str, PowerParameter] = {
    item.name: item
    for item in (
        _parameter(
            "T2M", "air_temperature_mean", "C", DataKind.REANALYSIS, _MERRA2, MERRA2_GRID,
            POWER_RECORD_START, "Daily mean air temperature at 2 m",
        ),
        _parameter(
            "T2M_MAX", "air_temperature_max", "C", DataKind.REANALYSIS, _MERRA2, MERRA2_GRID,
            POWER_RECORD_START, "Daily maximum air temperature at 2 m",
        ),
        _parameter(
            "T2M_MIN", "air_temperature_min", "C", DataKind.REANALYSIS, _MERRA2, MERRA2_GRID,
            POWER_RECORD_START, "Daily minimum air temperature at 2 m",
        ),
        _parameter(
            "PRECTOTCORR", "precipitation", "mm/day", DataKind.REANALYSIS, _MERRA2, MERRA2_GRID,
            POWER_RECORD_START, "Daily bias-corrected total precipitation",
        ),
        _parameter(
            "ALLSKY_SFC_SW_DWN", "solar_irradiance", "MJ/m^2/day", DataKind.SATELLITE_RETRIEVAL,
            _CERES, CERES_GRID, date(1984, 1, 1),
            "Daily all-sky shortwave irradiance on a horizontal surface",
        ),
        _parameter(
            "RH2M", "relative_humidity", "%", DataKind.REANALYSIS, _MERRA2, MERRA2_GRID,
            POWER_RECORD_START, "Daily mean relative humidity at 2 m",
        ),
    )
}
"""The parameters this project supports. Anything else is refused."""

CORE_PARAMETERS: tuple[str, ...] = ("PRECTOTCORR", "T2M")
DEFAULT_PARAMETERS: tuple[str, ...] = tuple(sorted(POWER_PARAMETERS))


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class NasaDataError(Exception):
    """Base class for every failure in the NASA data layer."""


class PowerRequestError(NasaDataError):
    """The service rejected the request; retrying would not help."""


class PowerUnavailableError(NasaDataError):
    """The service could not be reached or kept failing after bounded retries."""


class PowerResponseError(NasaDataError):
    """The service answered, but not with a response we can trust."""


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #


class PowerRequest(Contract):
    """A validated, normalised request for daily data at one point."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start: date
    end: date
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS
    community: Literal["AG"] = Field(
        default="AG",
        description="Agroclimatology. Fixed, because units differ between communities.",
    )
    time_standard: TimeStandard = Field(
        default=TimeStandard.UTC,
        description="How days are bounded. Always sent explicitly.",
    )

    @field_validator("latitude", "longitude")
    @classmethod
    def _round_coordinate(cls, value: float) -> float:
        return round(value, COORDINATE_DECIMALS) + 0.0  # "+ 0.0" turns -0.0 into 0.0

    @field_validator("parameters", mode="before")
    @classmethod
    def _normalise_parameters(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, (list, tuple, set, frozenset)):
            cleaned = [str(item).strip().upper() for item in value]
            return tuple(sorted(cleaned))
        return value

    @model_validator(mode="after")
    def _check_request(self) -> "PowerRequest":
        if not self.parameters:
            raise ValueError("request at least one parameter")
        if len(set(self.parameters)) != len(self.parameters):
            raise ValueError("parameters must not repeat")
        if len(self.parameters) > MAX_PARAMETERS_PER_REQUEST:
            raise ValueError(f"at most {MAX_PARAMETERS_PER_REQUEST} parameters per request")
        unknown = [name for name in self.parameters if name not in POWER_PARAMETERS]
        if unknown:
            raise ValueError(
                f"unsupported parameter(s) {', '.join(unknown)}; "
                f"supported: {', '.join(sorted(POWER_PARAMETERS))}"
            )
        if self.end < self.start:
            raise ValueError("end must not be before start")
        if self.end > datetime.now(timezone.utc).date():
            raise ValueError("end cannot be in the future; this tool retrieves history only")
        if self.expected_days > MAX_REQUEST_DAYS:
            raise ValueError(f"a request may cover at most {MAX_REQUEST_DAYS} days")
        for name in self.parameters:
            first = POWER_PARAMETERS[name].record_start
            if self.start < first:
                raise ValueError(f"{name} is available from {first.isoformat()}; start is too early")
        return self

    @property
    def expected_days(self) -> int:
        """Number of days the request covers, both ends included."""
        return (self.end - self.start).days + 1

    def query_params(self) -> dict[str, str]:
        """Query string parameters, in a fixed order."""
        return {
            "parameters": ",".join(self.parameters),
            "community": self.community,
            "longitude": f"{self.longitude:.{COORDINATE_DECIMALS}f}",
            "latitude": f"{self.latitude:.{COORDINATE_DECIMALS}f}",
            "start": self.start.strftime("%Y%m%d"),
            "end": self.end.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": self.time_standard.value,
        }

    def cache_key(self) -> str:
        """Stable identifier of this request: same request, same key."""
        identity = {"dataset": DATASET_ID, **self.query_params()}
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Result
# --------------------------------------------------------------------------- #


def payload_digest(payload: dict[str, Any]) -> str:
    """SHA-256 fingerprint of a response, independent of key order."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PowerRetrieval(Contract):
    """An original POWER response with the facts needed to verify and cite it."""

    request: PowerRequest
    url: str = Field(description="The exact URL that was requested.")
    status_code: int
    retrieved_at: AwareDatetime
    attempts: int = Field(ge=1)
    payload: dict[str, Any] = Field(description="The response body, unmodified.")
    payload_sha256: str
    origin: DataOrigin

    @model_validator(mode="after")
    def _check_fingerprint(self) -> "PowerRetrieval":
        if payload_digest(self.payload) != self.payload_sha256:
            raise ValueError("the response does not match its recorded fingerprint")
        return self


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PowerResponseError(f"the response repeats the key '{key}'")
        result[key] = value
    return result


def _reject_constant(name: str) -> Any:
    raise PowerResponseError(f"the response contains the non-numeric constant {name}")


def decode_response_text(text: str) -> dict[str, Any]:
    """Parse a response body strictly: no duplicate keys, no NaN or Infinity."""
    try:
        payload = json.loads(
            text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
        )
    except json.JSONDecodeError as error:
        raise PowerResponseError(f"the response is not valid JSON ({error.msg})") from None
    if not isinstance(payload, dict):
        raise PowerResponseError("the response is not a JSON object")
    return payload


def check_envelope(payload: dict[str, Any]) -> None:
    """Confirm the response has the overall shape of a POWER point response."""
    properties = payload.get("properties")
    if not isinstance(properties, dict) or not isinstance(properties.get("parameter"), dict):
        raise PowerResponseError("the response has no 'properties.parameter' section")
    if not isinstance(payload.get("header"), dict):
        raise PowerResponseError("the response has no 'header' section")


def _error_detail(response: httpx.Response) -> str:
    """Extract the service's own explanation of a rejected request, safely."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200].strip() or "no detail given"
    if isinstance(body, dict):
        for key in ("messages", "detail", "message", "header"):
            if body.get(key):
                return str(body[key])[:300]
    return "no detail given"


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None  # HTTP-date form is not used by this service; ignore it


class PowerClient:
    """Sends requests to the NASA POWER Daily API.

    ``transport``, ``sleep`` and ``jitter`` exist so tests can run without a
    network, without waiting and without randomness.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_NASA_POWER_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        if not base_url.lower().startswith("https://"):
            raise ValueError("the NASA endpoint must use https")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if not 0 <= max_retries <= MAX_NASA_RETRIES:
            raise ValueError(f"max_retries must be between 0 and {MAX_NASA_RETRIES}")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport = transport
        self._sleep = sleep
        self._jitter = jitter

    def build_url(self, request: PowerRequest) -> str:
        """The exact URL a request resolves to."""
        return str(httpx.URL(self.base_url, params=request.query_params()))

    def backoff_seconds(self, attempt: int, retry_after: float | None = None) -> float:
        """Wait before the next attempt: exponential, capped, with jitter."""
        exponential = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * 2 ** (attempt - 1))
        delay = exponential * (0.5 + 0.5 * self._jitter())
        if retry_after is not None:
            delay = max(delay, min(retry_after, RETRY_AFTER_CAP_SECONDS))
        return delay

    def fetch(self, request: PowerRequest) -> PowerRetrieval:
        """Retrieve one response. Raises a ``NasaDataError`` subclass on failure."""
        url = self.build_url(request)
        total_attempts = self.max_retries + 1
        last_problem = "no attempt was made"

        # verify=True is httpx's default and is deliberately left untouched.
        with httpx.Client(timeout=self.timeout, transport=self._transport) as http:
            for attempt in range(1, total_attempts + 1):
                retry_after: float | None = None
                logger.info("NASA POWER request, attempt %d of %d: %s", attempt, total_attempts, url)
                try:
                    response = http.get(url)
                except httpx.TimeoutException:
                    last_problem = f"no response within {self.timeout:g} seconds"
                except httpx.TransportError as error:
                    last_problem = f"connection problem ({type(error).__name__})"
                else:
                    if response.status_code == 200:
                        payload = decode_response_text(response.text)
                        check_envelope(payload)
                        return PowerRetrieval(
                            request=request,
                            url=url,
                            status_code=response.status_code,
                            retrieved_at=datetime.now(timezone.utc),
                            attempts=attempt,
                            payload=payload,
                            payload_sha256=payload_digest(payload),
                            origin=DataOrigin.NETWORK,
                        )
                    if response.status_code not in RETRYABLE_STATUS:
                        raise PowerRequestError(
                            f"NASA POWER rejected the request (HTTP {response.status_code}): "
                            f"{_error_detail(response)}"
                        )
                    retry_after = _retry_after_seconds(response)
                    last_problem = (
                        "rate limited (HTTP 429)"
                        if response.status_code == 429
                        else f"temporary server error (HTTP {response.status_code})"
                    )

                logger.warning("NASA POWER attempt %d failed: %s", attempt, last_problem)
                if attempt < total_attempts:
                    self._sleep(self.backoff_seconds(attempt, retry_after))

        raise PowerUnavailableError(
            f"NASA POWER could not be reached after {total_attempts} attempt(s): {last_problem}"
        )
