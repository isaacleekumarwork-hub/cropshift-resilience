"""Response cache: keys, atomic writes, corruption, expiry and invalidation."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.models import DataOrigin
from src.nasa_cache import CACHE_FORMAT, CacheCorruptedError, CacheReadOnlyError, ResponseCache
from src.nasa_client import PowerRequest


@pytest.fixture
def cache(tmp_path: Path) -> ResponseCache:
    return ResponseCache(tmp_path / "cache", ttl=timedelta(hours=24))


def test_round_trip_preserves_the_response(cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)
    restored = cache.get(recorded_request, allow_expired=True)
    assert restored is not None
    assert restored.payload == recorded_retrieval.payload
    assert restored.payload_sha256 == recorded_retrieval.payload_sha256
    assert restored.url == recorded_retrieval.url
    assert restored.retrieved_at == recorded_retrieval.retrieved_at
    assert restored.origin is DataOrigin.CACHE  # the cache says where it came from
    assert path.name == f"{recorded_request.cache_key()}.json"


def test_absent_entry_returns_none(cache, recorded_request):
    assert cache.get(recorded_request) is None
    assert cache.contains(recorded_request) is False


def test_entry_stores_request_metadata_alongside_the_response(cache, recorded_retrieval):
    envelope = json.loads(cache.put(recorded_retrieval).read_text(encoding="utf-8"))
    assert envelope["cache_format"] == CACHE_FORMAT
    assert envelope["key"] == recorded_retrieval.request.cache_key()
    assert envelope["url"] == recorded_retrieval.url
    assert envelope["request"]["time_standard"] == "UTC"
    assert envelope["request"]["parameters"] == list(recorded_retrieval.request.parameters)
    assert envelope["payload"] == recorded_retrieval.payload


def test_different_requests_use_different_files(cache, make_retrieval, recorded_request):
    other = PowerRequest(**{**recorded_request.model_dump(), "end": date(2020, 3, 30)})
    first = cache.put(make_retrieval())
    second = cache.put(make_retrieval(request=other))
    assert first != second
    assert len(list(cache.directory.glob("*.json"))) == 2


# --- Atomic writes -------------------------------------------------------------------


def test_write_leaves_no_temporary_files(cache, recorded_retrieval):
    cache.put(recorded_retrieval)
    assert [path.name for path in cache.directory.iterdir()] == [
        f"{recorded_retrieval.request.cache_key()}.json"
    ]


def test_failed_write_keeps_the_previous_entry_intact(cache, make_retrieval, recorded_request, monkeypatch):
    cache.put(make_retrieval())
    before = cache.path_for(recorded_request).read_bytes()

    def fail(source, destination):
        raise OSError("fixture: disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        cache.put(make_retrieval())
    monkeypatch.undo()

    assert cache.path_for(recorded_request).read_bytes() == before
    assert len(list(cache.directory.iterdir())) == 1  # no temporary file left behind
    assert cache.get(recorded_request, allow_expired=True) is not None


# --- Corruption ----------------------------------------------------------------------


def _rewrite(path: Path, change) -> None:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    change(envelope)
    path.write_text(json.dumps(envelope), encoding="utf-8")


def test_unreadable_file_is_reported_as_corrupted(cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)
    path.write_text("this is not json", encoding="utf-8")
    with pytest.raises(CacheCorruptedError, match="cannot be read as JSON"):
        cache.get(recorded_request, allow_expired=True)


def test_truncated_file_is_reported_as_corrupted(cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)
    path.write_bytes(path.read_bytes()[:500])
    with pytest.raises(CacheCorruptedError):
        cache.get(recorded_request, allow_expired=True)


def test_altered_values_are_detected(cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)

    def tamper(envelope):
        envelope["payload"]["properties"]["parameter"]["PRECTOTCORR"]["20200101"] = 999.0

    _rewrite(path, tamper)
    with pytest.raises(CacheCorruptedError, match="fingerprint"):
        cache.get(recorded_request, allow_expired=True)


@pytest.mark.parametrize("field", ["payload", "payload_sha256", "request", "retrieved_at", "key"])
def test_missing_field_is_detected(field, cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)
    _rewrite(path, lambda envelope: envelope.pop(field))
    with pytest.raises(CacheCorruptedError, match="lacks"):
        cache.get(recorded_request, allow_expired=True)


def test_unknown_format_version_is_detected(cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)
    _rewrite(path, lambda envelope: envelope.update(cache_format=99))
    with pytest.raises(CacheCorruptedError, match="format version"):
        cache.get(recorded_request, allow_expired=True)


def test_entry_filed_under_the_wrong_request_is_detected(cache, recorded_retrieval, recorded_request):
    other = PowerRequest(**{**recorded_request.model_dump(), "end": date(2020, 3, 30)})
    source = cache.put(recorded_retrieval)
    cache.path_for(other).write_bytes(source.read_bytes())
    with pytest.raises(CacheCorruptedError, match="does not belong"):
        cache.get(other, allow_expired=True)


def test_entry_whose_stored_request_was_edited_is_detected(cache, recorded_retrieval, recorded_request):
    path = cache.put(recorded_retrieval)
    _rewrite(path, lambda envelope: envelope["request"].update(latitude=10.0))
    with pytest.raises(CacheCorruptedError, match="different request"):
        cache.get(recorded_request, allow_expired=True)


# --- Expiry --------------------------------------------------------------------------


def test_expired_entry_is_treated_as_absent_unless_explicitly_allowed(cache, recorded_retrieval, recorded_request):
    cache.put(recorded_retrieval)
    stored_at = recorded_retrieval.retrieved_at
    assert cache.get(recorded_request, now=stored_at + timedelta(hours=23)) is not None
    assert cache.get(recorded_request, now=stored_at + timedelta(hours=25)) is None
    stale = cache.get(recorded_request, now=stored_at + timedelta(hours=25), allow_expired=True)
    assert stale is not None and cache.is_expired(stale, now=stored_at + timedelta(hours=25))


def test_expiry_is_configurable_and_can_be_disabled(tmp_path, recorded_retrieval, recorded_request):
    stored_at = recorded_retrieval.retrieved_at
    short = ResponseCache(tmp_path / "short", ttl=timedelta(minutes=1))
    short.put(recorded_retrieval)
    assert short.get(recorded_request, now=stored_at + timedelta(minutes=2)) is None

    forever = ResponseCache(tmp_path / "forever", ttl=None)
    forever.put(recorded_retrieval)
    assert forever.get(recorded_request, now=stored_at + timedelta(days=36500)) is not None


# --- Invalidation --------------------------------------------------------------------


def test_manual_invalidation_removes_one_entry(cache, recorded_retrieval, recorded_request):
    cache.put(recorded_retrieval)
    assert cache.invalidate(recorded_request) is True
    assert cache.get(recorded_request, allow_expired=True) is None
    assert cache.invalidate(recorded_request) is False


def test_clear_removes_cache_entries_and_nothing_else(cache, recorded_retrieval):
    cache.put(recorded_retrieval)
    keep = cache.directory / "README.md"
    keep.write_text("not a cache entry", encoding="utf-8")
    assert cache.clear() == 1
    assert keep.exists()
    assert ResponseCache(cache.directory / "missing").clear() == 0


def test_read_only_store_cannot_be_changed(tmp_path, recorded_retrieval, recorded_request):
    writable = ResponseCache(tmp_path / "demo")
    writable.put(recorded_retrieval)
    bundled = ResponseCache(tmp_path / "demo", origin=DataOrigin.BUNDLED, read_only=True)
    assert bundled.get(recorded_request).origin is DataOrigin.BUNDLED
    for change in (
        lambda: bundled.put(recorded_retrieval),
        lambda: bundled.invalidate(recorded_request),
        bundled.clear,
    ):
        with pytest.raises(CacheReadOnlyError):
            change()
    assert bundled.contains(recorded_request)


# --- Path safety ---------------------------------------------------------------------


def test_paths_stay_inside_the_cache_folder(cache, recorded_request):
    path = cache.path_for(recorded_request)
    assert path.parent == cache.directory.resolve()
    assert path.suffix == ".json" and len(path.stem) == 64


@pytest.mark.parametrize("bad_key", ["../../etc/passwd", "a" * 63, "A" * 64, "g" * 64, "", "abc/def"])
def test_unsafe_keys_are_refused(bad_key, cache, recorded_request, monkeypatch):
    monkeypatch.setattr(PowerRequest, "cache_key", lambda self: bad_key)
    with pytest.raises(ValueError, match="invalid cache key"):
        cache.path_for(recorded_request)
