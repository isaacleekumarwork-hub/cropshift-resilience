"""Typed application configuration for CropShift RESILIENCE.

Settings come from environment variables, optionally supplied through a local
``.env`` file that Git ignores. Nothing here contacts a network or creates a
file: importing this module is free of side effects.

Safety rules enforced by this module:

* External AI services are **off by default** and stay inactive unless both
  their switch and their key are present.
* Secrets are held as ``SecretStr`` so they never appear in logs, error
  messages or the Streamlit page.
* Invalid values fail loudly at start-up instead of being silently replaced.

AI assistance: drafted with Claude Code (Anthropic) under the participant's
direction. See docs/provenance.md.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
"""Folder that contains ``app.py``; relative paths in settings start here."""

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

MAX_NASA_REQUEST_TIMEOUT_SECONDS = 300.0
MAX_NASA_RETRIES = 6

DEFAULT_NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
"""NASA POWER Daily API, single-point endpoint."""


class Settings(BaseSettings):
    """All runtime settings, validated once and then immutable."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # "KEY=" in .env means "use the default"
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # --- Run mode -----------------------------------------------------------
    offline_demo_mode: bool = Field(
        default=False,
        description="Use only bundled or cached data; make no network requests.",
    )

    # --- Optional external AI services (disabled unless explicitly enabled) --
    enable_openai: bool = Field(default=False, description="Allow OpenAI explanations (A6).")
    enable_manus: bool = Field(default=False, description="Allow Manus research reports (A7).")

    # --- NASA data retrieval --------------------------------------------------
    nasa_request_timeout: float = Field(
        default=30.0,
        gt=0,
        le=MAX_NASA_REQUEST_TIMEOUT_SECONDS,
        description="Seconds to wait for a NASA API response.",
    )
    nasa_cache_directory: Path = Field(
        default=Path("data/cache"),
        description="Folder for cached NASA responses.",
    )
    nasa_power_base_url: str = Field(
        default=DEFAULT_NASA_POWER_URL,
        description="NASA POWER Daily API point endpoint. Must use HTTPS.",
    )
    nasa_max_retries: int = Field(
        default=3,
        ge=0,
        le=MAX_NASA_RETRIES,
        description="Extra attempts after a rate limit, timeout or temporary server error.",
    )
    nasa_cache_ttl_hours: float = Field(
        default=720.0,
        gt=0,
        le=87600,
        description="Hours before a cached NASA response is fetched again.",
    )
    nasa_demo_directory: Path = Field(
        default=Path("data/demo"),
        description="Folder of bundled, real NASA responses for offline demonstrations.",
    )
    nasa_min_completeness_percent: float = Field(
        default=90.0,
        ge=0,
        le=100,
        description="A dataset is accepted only if every variable is at least this complete.",
    )

    # --- Local storage --------------------------------------------------------
    database_path: Path = Field(
        default=Path("data/cropshift.db"),
        description="SQLite file for saved comparisons.",
    )

    # --- Logging --------------------------------------------------------------
    log_level: LogLevel = Field(default="INFO", description="Python logging level.")

    # --- Future credentials (never hardcode; never commit) --------------------
    openai_api_key: SecretStr | None = Field(default=None, description="Used from phase A6.")
    manus_api_key: SecretStr | None = Field(default=None, description="Used from phase A7.")

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("nasa_power_base_url")
    @classmethod
    def _require_plain_https_endpoint(cls, value: str) -> str:
        parts = urlsplit(value.strip())
        if parts.scheme != "https":
            raise ValueError("the NASA endpoint must use https")
        if not parts.hostname:
            raise ValueError("the NASA endpoint needs a host name")
        if parts.username or parts.password:
            raise ValueError("the NASA endpoint must not contain credentials")
        if parts.query or parts.fragment:
            raise ValueError("the NASA endpoint must not contain a query string or fragment")
        return value.strip().rstrip("/")

    @field_validator("openai_api_key", "manus_api_key", mode="before")
    @classmethod
    def _blank_key_means_absent(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    # --- Derived, read-only views ---------------------------------------------
    @property
    def nasa_cache_path(self) -> Path:
        """Cache folder as an absolute path (the folder is not created here)."""
        return _resolve(self.nasa_cache_directory)

    @property
    def nasa_demo_path(self) -> Path:
        """Bundled demo-data folder as an absolute path."""
        return _resolve(self.nasa_demo_directory)

    @property
    def nasa_cache_ttl(self) -> timedelta:
        """Cache lifetime as a time span."""
        return timedelta(hours=self.nasa_cache_ttl_hours)

    @property
    def database_file(self) -> Path:
        """Database file as an absolute path (the file is not created here)."""
        return _resolve(self.database_path)

    @property
    def openai_ready(self) -> bool:
        """True only when OpenAI is switched on *and* a key is available."""
        return self.enable_openai and self.openai_api_key is not None

    @property
    def manus_ready(self) -> bool:
        """True only when Manus is switched on *and* a key is available."""
        return self.enable_manus and self.manus_api_key is not None

    def integration_status(self) -> dict[str, str]:
        """Describe each external service in words that are safe to display.

        The text never contains a key or any part of one.
        """
        return {
            "OpenAI explanations": _describe(self.enable_openai, self.openai_api_key),
            "Manus research reports": _describe(self.enable_manus, self.manus_api_key),
        }


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _describe(enabled: bool, key: SecretStr | None) -> str:
    if not enabled:
        return "disabled"
    if key is None:
        return "switched on but inactive (no key provided)"
    return "enabled"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use."""
    return Settings()


def configure_logging(settings: Settings | None = None) -> None:
    """Apply the configured log level to Python's root logger."""
    active = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, active.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(getattr(logging, active.log_level))
