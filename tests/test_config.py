"""Configuration: safe defaults, disabled AI services, strict validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src import config
from tests.conftest import SETTING_NAMES

FAKE_KEY = "test-key-not-a-real-credential"


# --- Defaults ----------------------------------------------------------------


def test_defaults_are_safe(make_settings):
    settings = make_settings()
    assert settings.offline_demo_mode is False
    assert settings.enable_openai is False
    assert settings.enable_manus is False
    assert settings.nasa_request_timeout == 30.0
    assert settings.nasa_cache_directory == Path("data/cache")
    assert settings.database_path == Path("data/cropshift.db")
    assert settings.log_level == "INFO"
    assert settings.openai_api_key is None
    assert settings.manus_api_key is None


def test_external_ai_is_disabled_by_default(make_settings):
    settings = make_settings()
    assert settings.openai_ready is False
    assert settings.manus_ready is False
    assert settings.integration_status() == {
        "OpenAI explanations": "disabled",
        "Manus research reports": "disabled",
    }


def test_get_settings_returns_one_cached_object():
    assert config.get_settings() is config.get_settings()


# --- External AI services need both a switch and a key ------------------------


def test_key_alone_does_not_enable_a_service(monkeypatch, make_settings):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("MANUS_API_KEY", FAKE_KEY)
    settings = make_settings()
    assert settings.openai_ready is False
    assert settings.manus_ready is False


def test_switch_alone_does_not_enable_a_service(monkeypatch, make_settings):
    monkeypatch.setenv("ENABLE_OPENAI", "true")
    monkeypatch.setenv("ENABLE_MANUS", "true")
    settings = make_settings()
    assert settings.openai_ready is False
    assert settings.manus_ready is False
    assert "no key" in settings.integration_status()["OpenAI explanations"]


def test_switch_and_key_together_enable_a_service(monkeypatch, make_settings):
    monkeypatch.setenv("ENABLE_OPENAI", "true")
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    settings = make_settings()
    assert settings.openai_ready is True
    assert settings.manus_ready is False  # enabling one never enables the other


def test_blank_key_counts_as_no_key(make_settings):
    assert make_settings(enable_openai=True, openai_api_key="   ").openai_ready is False


def test_secrets_never_appear_in_text(monkeypatch, make_settings):
    monkeypatch.setenv("ENABLE_OPENAI", "true")
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    settings = make_settings()
    assert FAKE_KEY not in repr(settings)
    assert FAKE_KEY not in str(settings)
    assert FAKE_KEY not in " ".join(settings.integration_status().values())
    assert FAKE_KEY not in settings.model_dump_json()


# --- Reading values from the environment --------------------------------------


def test_environment_overrides_are_parsed(monkeypatch, make_settings):
    monkeypatch.setenv("OFFLINE_DEMO_MODE", "true")
    monkeypatch.setenv("NASA_REQUEST_TIMEOUT", "12.5")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", "custom/cache")
    settings = make_settings()
    assert settings.offline_demo_mode is True
    assert settings.nasa_request_timeout == 12.5
    assert settings.log_level == "DEBUG"
    assert settings.nasa_cache_directory == Path("custom/cache")


def test_empty_environment_values_fall_back_to_defaults(monkeypatch, make_settings):
    for name in SETTING_NAMES:
        monkeypatch.setenv(name, "")
    settings = make_settings()
    assert settings.enable_openai is False
    assert settings.nasa_request_timeout == 30.0
    assert settings.log_level == "INFO"
    assert settings.openai_api_key is None


def test_relative_paths_resolve_from_the_project_root(make_settings):
    settings = make_settings()
    assert settings.nasa_cache_path == config.PROJECT_ROOT / "data" / "cache"
    assert settings.database_file == config.PROJECT_ROOT / "data" / "cropshift.db"


def test_absolute_paths_are_kept(tmp_path, make_settings):
    settings = make_settings(nasa_cache_directory=tmp_path / "cache", database_path=tmp_path / "x.db")
    assert settings.nasa_cache_path == tmp_path / "cache"
    assert settings.database_file == tmp_path / "x.db"


def test_loading_settings_creates_no_files(tmp_path, make_settings):
    settings = make_settings(nasa_cache_directory=tmp_path / "cache", database_path=tmp_path / "x.db")
    assert not settings.nasa_cache_path.exists()
    assert not settings.database_file.exists()


# --- Invalid values fail loudly -----------------------------------------------


@pytest.mark.parametrize("timeout", ["0", "-5", "301", "soon"])
def test_invalid_timeout_is_rejected(monkeypatch, make_settings, timeout):
    monkeypatch.setenv("NASA_REQUEST_TIMEOUT", timeout)
    with pytest.raises(ValidationError):
        make_settings()


def test_unknown_log_level_is_rejected(monkeypatch, make_settings):
    monkeypatch.setenv("LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError):
        make_settings()


@pytest.mark.parametrize("name", ["OFFLINE_DEMO_MODE", "ENABLE_OPENAI", "ENABLE_MANUS"])
def test_ambiguous_switch_value_is_rejected(monkeypatch, make_settings, name):
    monkeypatch.setenv(name, "maybe")
    with pytest.raises(ValidationError):
        make_settings()


def test_settings_cannot_be_changed_after_loading(make_settings):
    settings = make_settings()
    with pytest.raises(ValidationError):
        settings.enable_openai = True


# --- Repository hygiene -------------------------------------------------------


def test_env_example_documents_every_setting_without_secrets():
    text = (config.PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assigned = dict(
        line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#")
    )
    assert set(assigned) == set(SETTING_NAMES)
    assert assigned["OPENAI_API_KEY"] == ""
    assert assigned["MANUS_API_KEY"] == ""
    assert assigned["ENABLE_OPENAI"] == "false"
    assert assigned["ENABLE_MANUS"] == "false"


def test_gitignore_excludes_env_files():
    lines = (config.PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in lines
    assert ".env.*" in lines
    assert "!.env.example" in lines
