"""Local file cache for NASA POWER responses.

Responsibility
    Store each verified response once, find it again from the request alone,
    and refuse to return anything that is damaged or does not match.

How it works
    * One JSON file per request, named by the request's SHA-256 cache key.
      The key covers the dataset, coordinates, date range, parameters,
      community and time standard.
    * Files are written to a temporary name and then renamed, so a crash can
      never leave a half-written entry.
    * Reading re-checks the file: format version, key, stored request and the
      fingerprint of the original response. A mismatch is reported as
      corruption, never repaired or guessed around.
    * Entries older than the configured lifetime are treated as absent unless
      the caller explicitly accepts expired data (offline mode does).

The same class reads the bundled demonstration data, in read-only mode.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.models import DataOrigin
from src.nasa_client import NasaDataError, PowerRequest, PowerRetrieval

logger = logging.getLogger(__name__)

CACHE_FORMAT = 1
_KEY_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FIELDS = (
    "cache_format",
    "key",
    "request",
    "url",
    "status_code",
    "retrieved_at",
    "attempts",
    "payload_sha256",
    "payload",
)


class CacheCorruptedError(NasaDataError):
    """A cache file exists but cannot be trusted."""


class CacheReadOnlyError(NasaDataError):
    """An attempt was made to change a read-only store such as the demo data."""


class ResponseCache:
    """A folder of verified NASA POWER responses."""

    def __init__(
        self,
        directory: Path,
        *,
        ttl: timedelta | None = None,
        origin: DataOrigin = DataOrigin.CACHE,
        read_only: bool = False,
    ) -> None:
        self.directory = Path(directory)
        self.ttl = ttl
        self.origin = origin
        self.read_only = read_only

    # --- Locating entries ------------------------------------------------------

    def path_for(self, request: PowerRequest) -> Path:
        """File that holds, or would hold, the response to this request."""
        key = request.cache_key()
        if not _KEY_PATTERN.fullmatch(key):  # defensive: keys are always SHA-256 hex
            raise ValueError("refusing to build a path from an invalid cache key")
        base = self.directory.resolve()
        path = (base / f"{key}.json").resolve()
        if path.parent != base:
            raise ValueError("refusing to build a path outside the cache folder")
        return path

    def contains(self, request: PowerRequest) -> bool:
        return self.path_for(request).is_file()

    # --- Reading ---------------------------------------------------------------

    def get(
        self,
        request: PowerRequest,
        *,
        allow_expired: bool = False,
        now: datetime | None = None,
    ) -> PowerRetrieval | None:
        """Return the stored response, or ``None`` if absent or expired.

        Raises ``CacheCorruptedError`` if a file exists but fails verification.
        """
        path = self.path_for(request)
        if not path.is_file():
            return None
        retrieval = self._read(path, request)
        if not allow_expired and self.is_expired(retrieval, now=now):
            logger.info("Cache entry %s has expired", path.name)
            return None
        return retrieval

    def is_expired(self, retrieval: PowerRetrieval, *, now: datetime | None = None) -> bool:
        """True when the entry is older than the configured lifetime."""
        if self.ttl is None:
            return False
        current = now or datetime.now(timezone.utc)
        return current - retrieval.retrieved_at > self.ttl

    def _read(self, path: Path, request: PowerRequest) -> PowerRetrieval:
        try:
            envelope: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CacheCorruptedError(
                f"cache file {path.name} cannot be read as JSON ({type(error).__name__})"
            ) from None
        if not isinstance(envelope, dict):
            raise CacheCorruptedError(f"cache file {path.name} is not a JSON object")
        missing = [name for name in _REQUIRED_FIELDS if name not in envelope]
        if missing:
            raise CacheCorruptedError(f"cache file {path.name} lacks {', '.join(missing)}")
        if envelope["cache_format"] != CACHE_FORMAT:
            raise CacheCorruptedError(f"cache file {path.name} has an unknown format version")
        if envelope["key"] != request.cache_key() or path.stem != envelope["key"]:
            raise CacheCorruptedError(f"cache file {path.name} does not belong to this request")
        try:
            retrieval = PowerRetrieval(
                request=envelope["request"],
                url=envelope["url"],
                status_code=envelope["status_code"],
                retrieved_at=envelope["retrieved_at"],
                attempts=envelope["attempts"],
                payload=envelope["payload"],
                payload_sha256=envelope["payload_sha256"],
                origin=self.origin,
            )
        except ValidationError as error:
            reason = error.errors()[0]["msg"] if error.errors() else "invalid content"
            raise CacheCorruptedError(f"cache file {path.name} failed verification: {reason}") from None
        if retrieval.request != request:
            raise CacheCorruptedError(f"cache file {path.name} stores a different request")
        return retrieval

    # --- Writing ---------------------------------------------------------------

    def put(self, retrieval: PowerRetrieval) -> Path:
        """Store a response atomically and return the file's path."""
        self._require_writable()
        path = self.path_for(retrieval.request)
        self.directory.mkdir(parents=True, exist_ok=True)
        envelope = {
            "cache_format": CACHE_FORMAT,
            "key": retrieval.request.cache_key(),
            "note": "Original NASA POWER response, stored unmodified in 'payload'.",
            "request": retrieval.request.model_dump(mode="json"),
            "url": retrieval.url,
            "status_code": retrieval.status_code,
            "retrieved_at": retrieval.retrieved_at.isoformat(),
            "attempts": retrieval.attempts,
            "payload_sha256": retrieval.payload_sha256,
            "payload": retrieval.payload,
        }
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.directory, prefix=".writing-", suffix=".tmp", delete=False
        )
        temporary = Path(handle.name)
        try:
            with handle:
                json.dump(envelope, handle, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return path

    def invalidate(self, request: PowerRequest) -> bool:
        """Delete the entry for one request. Returns True if a file was removed."""
        self._require_writable()
        path = self.path_for(request)
        if path.is_file():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Delete every cache entry in the folder. Returns the number removed."""
        self._require_writable()
        if not self.directory.is_dir():
            return 0
        removed = 0
        for path in self.directory.glob("*.json"):
            if _KEY_PATTERN.fullmatch(path.stem):
                path.unlink()
                removed += 1
        return removed

    def _require_writable(self) -> None:
        if self.read_only:
            raise CacheReadOnlyError("this data store is read-only")
