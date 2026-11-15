"""The single entry point of the NASA data layer.

Responsibility
    Given a request, return a validated dataset, deciding where the response
    comes from: the local cache, the bundled demonstration data or the NASA
    service. The decision is recorded in the dataset and reported to the user.

Order of preference
    Offline mode (``OFFLINE_DEMO_MODE=true``):
        1. local cache, even if expired
        2. bundled demonstration data
        3. otherwise fail with a clear message
        The network is never contacted; no client is even created.

    Online mode:
        1. local cache, if present and not expired
        2. the NASA service; the verified response is then cached
        3. if the service cannot be reached: an expired cache entry, then the
           bundled data, each with a visible warning
        4. otherwise fail with the service's error

This module knows nothing about Streamlit, OpenAI, Manus or any workflow
tool. It is the boundary a future automation layer would call, and it remains
usable on its own from the command line:

    python -m src.data_service pilot
    python -m src.data_service fetch --lat -1.58 --lon 37.24 --start 2020-01-01 --end 2020-12-31

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from pydantic import ValidationError

from src.config import Settings, configure_logging, get_settings
from src.data_validation import (
    EnvironmentalDataset,
    IssueSeverity,
    ValidationIssue,
    ValidationLevel,
    build_dataset,
    check_structure,
)
from src.models import DataOrigin, TimeStandard
from src.nasa_cache import CacheCorruptedError, ResponseCache
from src.nasa_client import (
    DEFAULT_PARAMETERS,
    NasaDataError,
    PowerClient,
    PowerRequest,
    PowerRetrieval,
    PowerUnavailableError,
)
from src.pilot_sites import PILOT_SITE, PilotSite

logger = logging.getLogger(__name__)


class OfflineDataUnavailableError(NasaDataError):
    """Offline mode is on and no stored response matches the request."""


def make_client(settings: Settings) -> PowerClient:
    """Build the NASA client from settings."""
    return PowerClient(
        base_url=settings.nasa_power_base_url,
        timeout=settings.nasa_request_timeout,
        max_retries=settings.nasa_max_retries,
    )


def make_cache(settings: Settings) -> ResponseCache:
    """The writable local cache."""
    return ResponseCache(settings.nasa_cache_path, ttl=settings.nasa_cache_ttl)


def make_bundled_store(settings: Settings) -> ResponseCache:
    """The read-only store of real responses shipped with the project."""
    return ResponseCache(
        settings.nasa_demo_path, ttl=None, origin=DataOrigin.BUNDLED, read_only=True
    )


def _service_issue(code: str, message: str, severity: IssueSeverity = IssueSeverity.WARNING) -> ValidationIssue:
    return ValidationIssue(level=ValidationLevel.SERVICE, severity=severity, code=code, message=message)


def _read_store(
    store: ResponseCache, request: PowerRequest, *, allow_expired: bool, issues: list[ValidationIssue]
) -> PowerRetrieval | None:
    """Read from a store, turning corruption into a visible issue instead of a crash."""
    try:
        return store.get(request, allow_expired=allow_expired)
    except CacheCorruptedError as error:
        logger.warning("Ignoring unusable stored response: %s", error)
        issues.append(_service_issue("stored_response_unusable", f"A stored response was ignored because it failed verification: {error}."))
        return None


def retrieve(
    request: PowerRequest,
    *,
    settings: Settings | None = None,
    client: PowerClient | None = None,
    cache: ResponseCache | None = None,
    bundled: ResponseCache | None = None,
    force_refresh: bool = False,
) -> tuple[PowerRetrieval, tuple[ValidationIssue, ...]]:
    """Obtain the original response for a request, plus notes on how it was obtained."""
    active = settings or get_settings()
    cache = cache or make_cache(active)
    bundled = bundled or make_bundled_store(active)
    issues: list[ValidationIssue] = []

    if active.offline_demo_mode:
        if force_refresh:
            raise OfflineDataUnavailableError(
                "Offline mode is on, so data cannot be refreshed from NASA. "
                "Set OFFLINE_DEMO_MODE=false to retrieve it."
            )
        stored = _read_store(cache, request, allow_expired=True, issues=issues)
        if stored is not None:
            if cache.is_expired(stored):
                issues.append(_service_issue("cache_expired_offline", "Offline mode: showing a cached response that is older than the configured cache lifetime.", IssueSeverity.INFO))
            return stored, tuple(issues)
        stored = _read_store(bundled, request, allow_expired=True, issues=issues)
        if stored is not None:
            return stored, tuple(issues)
        raise OfflineDataUnavailableError(
            "Offline mode is on and no stored NASA response matches this request "
            f"({request.latitude}, {request.longitude}, {request.start} to {request.end}). "
            "Set OFFLINE_DEMO_MODE=false to retrieve it, or request the bundled pilot dataset."
        )

    if not force_refresh:
        stored = _read_store(cache, request, allow_expired=False, issues=issues)
        if stored is not None:
            return stored, tuple(issues)

    try:
        fetched = (client or make_client(active)).fetch(request)
    except PowerUnavailableError as error:
        for store, label in ((cache, "an older cached response"), (bundled, "the bundled dataset")):
            stored = _read_store(store, request, allow_expired=True, issues=issues)
            if stored is not None:
                issues.append(_service_issue("service_unreachable_fallback", f"NASA POWER could not be reached, so {label} retrieved on {stored.retrieved_at:%d %b %Y} is shown instead. ({error})"))
                return stored, tuple(issues)
        raise

    check_structure(fetched)  # only verified responses are cached
    try:
        cache.put(fetched)
    except OSError as error:
        issues.append(_service_issue("cache_write_failed", f"The response could not be saved to the cache ({type(error).__name__}); it will be requested again next time."))
    return fetched, tuple(issues)


def load_dataset(
    request: PowerRequest,
    *,
    settings: Settings | None = None,
    client: PowerClient | None = None,
    cache: ResponseCache | None = None,
    bundled: ResponseCache | None = None,
    force_refresh: bool = False,
    site_name: str | None = None,
) -> EnvironmentalDataset:
    """Return validated observations for a request. See the module docstring."""
    active = settings or get_settings()
    retrieval, notes = retrieve(
        request, settings=active, client=client, cache=cache, bundled=bundled, force_refresh=force_refresh
    )
    return build_dataset(
        retrieval,
        site_name=site_name,
        min_completeness_percent=active.nasa_min_completeness_percent,
        service_issues=notes,
    )


def load_pilot_dataset(
    site: PilotSite = PILOT_SITE, *, settings: Settings | None = None, force_refresh: bool = False
) -> EnvironmentalDataset:
    """Return the validated dataset for the pilot site."""
    return load_dataset(site.request(), settings=settings, force_refresh=force_refresh, site_name=site.name)


def invalidate(request: PowerRequest, *, settings: Settings | None = None) -> bool:
    """Remove one request's response from the local cache. True if one was removed."""
    return make_cache(settings or get_settings()).invalidate(request)


def save_as_bundled(request: PowerRequest, *, settings: Settings | None = None) -> str:
    """Copy a verified, accepted cached response into the bundled demo folder.

    Used once, deliberately, to prepare offline demonstration data from a real
    retrieval. Refuses anything that is not already cached and accepted.
    """
    active = settings or get_settings()
    stored = make_cache(active).get(request, allow_expired=True)
    if stored is None:
        raise NasaDataError("retrieve the dataset first; nothing is cached for this request")
    build_dataset(stored, min_completeness_percent=active.nasa_min_completeness_percent).require_accepted()
    writable = ResponseCache(active.nasa_demo_path, ttl=None, origin=DataOrigin.BUNDLED)
    return str(writable.put(stored))


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def describe(dataset: EnvironmentalDataset) -> str:
    """A plain-text summary of a dataset, for the command line."""
    provenance, quality = dataset.provenance, dataset.quality
    lines = [
        f"Site:        {dataset.site_name or 'unnamed point'} "
        f"({dataset.location.latitude}, {dataset.location.longitude})",
        f"Source:      {provenance.service_name} {provenance.service_version or ''}".rstrip(),
        f"Obtained:    from {provenance.origin.value}; retrieved {provenance.retrieved_at:%Y-%m-%d %H:%M} UTC",
        f"Request:     {provenance.request_url}",
        f"Period:      {quality.requested_start} to {quality.requested_end} ({quality.expected_days} days, {provenance.time_standard.value})",
        f"Accepted:    {'yes' if quality.accepted else 'NO'} (minimum completeness {quality.min_completeness_percent:g}%)",
        "",
        f"{'Variable':<24}{'Unit':<12}{'Valid':>7}{'Missing':>9}{'Complete':>10}{'Min':>9}{'Mean':>9}{'Max':>9}",
    ]
    for item in quality.variables:
        low, mean, high = (
            f"{number:.2f}" if number is not None else "-" for number in (item.minimum, item.mean, item.maximum)
        )
        lines.append(
            f"{item.variable:<24}{item.unit.value:<12}{item.valid_count:>7}{item.missing_count:>9}"
            f"{item.completeness_percent:>9.2f}%{low:>9}{mean:>9}{high:>9}"
        )
    if quality.issues:
        lines.append("")
        lines.extend(f"[{issue.severity.value}] {issue.message}" for issue in quality.issues)
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data_service",
        description="Retrieve and validate NASA POWER daily data for one point.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    pilot = commands.add_parser("pilot", help="the documented pilot site and period")
    pilot.add_argument("--refresh", action="store_true", help="ignore the cache and request again")
    pilot.add_argument("--save-bundled", action="store_true", help="copy the verified response into the bundled demo folder")

    fetch = commands.add_parser("fetch", help="any valid point and historical date range")
    fetch.add_argument("--lat", type=float, required=True)
    fetch.add_argument("--lon", type=float, required=True)
    fetch.add_argument("--start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    fetch.add_argument("--end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    fetch.add_argument("--parameters", default=",".join(DEFAULT_PARAMETERS), help="comma-separated NASA POWER parameters")
    fetch.add_argument("--time-standard", choices=[item.value for item in TimeStandard], default=TimeStandard.UTC.value)
    fetch.add_argument("--refresh", action="store_true", help="ignore the cache and request again")
    fetch.add_argument("--invalidate", action="store_true", help="delete this request's cache entry and stop")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point. Returns a process exit code."""
    arguments = _parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings)
    try:
        if arguments.command == "pilot":
            request, site_name = PILOT_SITE.request(), PILOT_SITE.name
        else:
            request = PowerRequest(
                latitude=arguments.lat,
                longitude=arguments.lon,
                start=arguments.start,
                end=arguments.end,
                parameters=arguments.parameters,
                time_standard=arguments.time_standard,
            )
            site_name = None
            if arguments.invalidate:
                removed = invalidate(request, settings=settings)
                print("Cache entry removed." if removed else "Nothing was cached for this request.")
                return 0
        dataset = load_dataset(
            request, settings=settings, force_refresh=arguments.refresh, site_name=site_name
        )
        print(describe(dataset))
        if arguments.command == "pilot" and arguments.save_bundled:
            print(f"\nBundled copy written to {save_as_bundled(request, settings=settings)}")
        return 0 if dataset.quality.accepted else 2
    except ValidationError as error:
        problems = "; ".join(item["msg"] for item in error.errors())
        print(f"Invalid request: {problems}", file=sys.stderr)
        return 1
    except NasaDataError as error:
        print(f"Could not load NASA data: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
