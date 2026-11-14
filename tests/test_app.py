"""The Streamlit foundation page starts and tells the truth about its state."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

import src
from src.config import PROJECT_ROOT

APP_FILE = str(PROJECT_ROOT / "app.py")


# Generous because the very first launch after installing packages is slow
# (the operating system checks the newly installed libraries once).
START_TIMEOUT_SECONDS = 120


def run_app() -> AppTest:
    return AppTest.from_file(APP_FILE, default_timeout=START_TIMEOUT_SECONDS).run()


def all_text(app: AppTest) -> str:
    parts = [element.value for element in (*app.markdown, *app.caption, *app.warning, *app.subheader)]
    return " ".join(str(part) for part in parts)


def test_app_starts_without_errors():
    app = run_app()
    assert not app.exception
    assert not app.error
    assert app.title[0].value == src.PROJECT_NAME


def test_app_states_its_development_stage_honestly():
    app = run_app()
    warning = app.warning[0].value
    assert "A1 of A9" in warning
    assert "not implemented" in warning
    assert "no NASA observations" in warning
    assert "not built yet" in all_text(app)


def test_app_shows_no_data_or_results():
    app = run_app()
    assert len(app.metric) == 0
    assert len(app.get("plotly_chart")) == 0
    # The only tables are the build-status and module tables.
    assert len(app.dataframe) == 2


def test_app_reports_ai_services_as_disabled_by_default():
    text = all_text(run_app())
    assert "**OpenAI explanations:** disabled" in text
    assert "**Manus research reports:** disabled" in text
    assert "does not predict yields" in text


def test_app_stops_cleanly_when_configuration_is_invalid(monkeypatch):
    monkeypatch.setenv("NASA_REQUEST_TIMEOUT", "-1")
    app = run_app()
    assert not app.exception
    assert "NASA_REQUEST_TIMEOUT" in app.error[0].value
    assert len(app.dataframe) == 0  # nothing else is rendered
