"""The Streamlit application starts, works offline and tells the truth.

These tests run the real ``app.py`` in offline mode against the real NASA
response bundled in ``data/demo``, so they need no network. They cover the A2
data preview (now inside the Climate Explorer and Scientific Evidence tabs),
the A5 navigation and interactions, the twelve-step demonstration journey and
the scientific-integrity rules for every word on screen.
"""

from __future__ import annotations

import re

import pytest
from streamlit.testing.v1 import AppTest

import src
from src.config import PROJECT_ROOT

APP_FILE = str(PROJECT_ROOT / "app.py")

# Generous because the very first launch after installing packages is slow
# (the operating system checks the newly installed libraries once).
START_TIMEOUT_SECONDS = 120

TAB_NAMES = ["Overview", "Climate Explorer", "Rotation Comparison", "Soil & Farm Inputs", "Scientific Evidence", "About & Methodology"]


@pytest.fixture(autouse=True)
def offline_with_bundled_data(monkeypatch, tmp_path):
    """Offline mode, an empty private cache, and the project's bundled data."""
    monkeypatch.setenv("OFFLINE_DEMO_MODE", "true")
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", str(tmp_path / "cache"))


def run_app() -> AppTest:
    return AppTest.from_file(APP_FILE, default_timeout=START_TIMEOUT_SECONDS).run()


def all_text(app: AppTest) -> str:
    groups = (
        app.markdown, app.caption, app.warning, app.subheader, app.info, app.success, app.error, app.code,
        app.header, app.title, app.metric,
    )
    parts = []
    for group in groups:
        for element in group:
            value = getattr(element, "value", "")
            label = getattr(element, "label", "")
            parts.append(f"{label} {value}")
    return " ".join(parts)


def frame_with(app: AppTest, column: str):
    """The first dataframe that has a given column."""
    for element in app.dataframe:
        if column in element.value.columns:
            return element.value
    raise AssertionError(f"no table with column {column!r}")


@pytest.fixture(scope="module")
def app_default(tmp_path_factory):
    """One default run shared by read-only tests (the module fixture sets the environment itself)."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("OFFLINE_DEMO_MODE", "true")
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", str(tmp_path_factory.mktemp("cache")))
    app = AppTest.from_file(APP_FILE, default_timeout=START_TIMEOUT_SECONDS).run()
    yield app
    monkeypatch.undo()


# --- Launch and navigation -----------------------------------------------------------


def test_app_starts_without_errors(app_default):
    assert not app_default.exception
    assert not app_default.error
    assert app_default.title[0].value == src.PROJECT_NAME


def test_navigation_has_the_six_sections(app_default):
    assert [tab.label for tab in app_default.tabs] == TAB_NAMES


def test_app_states_its_stage_and_its_limits_honestly(app_default):
    text = all_text(app_default)
    assert "Development stage A9 of A9" in text
    assert "internal validation" in text
    banner = app_default.warning[0].value
    assert "has not approved this pilot site" in banner
    assert "past seasons, not forecasts" in banner
    assert "No rotation is scored, ranked or recommended" in banner


def test_app_reports_ai_services_as_disabled_by_default(app_default):
    text = all_text(app_default)
    assert "**OpenAI explanations:** disabled" in text
    assert "**Manus research reports:** disabled" in text
    assert "does not predict yields" in text


# --- Overview and the A2 data preview ------------------------------------------------------


def test_overview_shows_location_source_period_and_origin(app_default):
    text = all_text(app_default)
    assert "Katumani area, Machakos County, Kenya" in text
    assert "latitude -1.58, longitude 37.24" in text
    assert "NASA POWER Daily API v2.10.3" in text
    assert "01 January 2001 to 31 December 2025 (9,131 days, UTC days)" in text
    assert "54,786 daily values of 6 variables" in text
    assert "Offline mode is on." in text
    assert "real NASA response bundled with the project" in text  # cache/network status
    assert "14 November 2026" in text  # when NASA supplied it
    assert "Site status: provisional" in text


def test_overview_metrics_come_from_the_scenario_engine(app_default, pilot_dataset):
    from src.scenario_engine import build_scenarios
    from src.season_config import PILOT_WINDOWS

    scenarios = build_scenarios(pilot_dataset, PILOT_WINDOWS)
    metrics = {item.label: item.value for item in app_default.metric}
    assert metrics["Past rainy seasons"] == "50"
    assert metrics["Long rains: median rainfall"] == f"{scenarios.window('long-rains').rainfall_median_mm:.0f} mm" == "209 mm"
    assert metrics["Short rains: median rainfall"] == f"{scenarios.window('short-rains').rainfall_median_mm:.0f} mm" == "232 mm"


def test_quality_is_shown_and_never_overstated(app_default):
    text = all_text(app_default)
    assert "Accepted." in app_default.success[0].value and "100% of days" in app_default.success[0].value
    assert "do not show that the values are accurate for a particular farm" in text
    assert "not measurements from an individual farm" in text
    assert "No quality warnings or errors" in text


def test_variables_and_first_and_last_observations_are_shown(app_default):
    quality = frame_with(app_default, "NASA parameter")
    assert list(quality["NASA parameter"]) == ["ALLSKY_SFC_SW_DWN", "PRECTOTCORR", "RH2M", "T2M", "T2M_MAX", "T2M_MIN"]
    assert set(quality["Valid days"]) == {9131} and set(quality["Missing days"]) == {0}
    assert "NASA reanalysis (weather model constrained by observations)" in set(quality["Kind of evidence"])
    first, last = [frame.value for frame in app_default.dataframe if "Rainfall (mm/day)" in frame.value.columns]
    assert list(first.index) == ["2001-01-01", "2001-01-02", "2001-01-03", "2001-01-04", "2001-01-05"]
    assert list(last.index)[-1] == "2025-12-31" and len(last) == 5
    assert "Mean temperature (degC)" in first.columns


def test_monthly_table_is_descriptive_and_explains_its_method(app_default):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = next(frame.value for frame in app_default.dataframe if list(frame.value.index) == months)
    assert "Rainfall (mm)" in monthly.columns  # a monthly total, not a daily rate
    text = all_text(app_default)
    assert "Rainfall is the monthly total" in text and "never estimated" in text


def test_citation_and_provenance_are_shown(app_default):
    text = all_text(app_default)
    assert "Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project" in text
    assert "POWER Project's Daily v2.10.3 version on 2026/11/14" in text
    assert "https://power.larc.nasa.gov/api/temporal/daily/point?" in text
    assert "1c2ed230e2661199ac278e4ac68b179c4b5750284091c094745de4a920e0edaf" in text
    assert "not endorsed by NASA" in text
    assert "it is not a forecast" in text


# --- Climate Explorer ---------------------------------------------------------------------


def test_climate_charts_render(app_default):
    # Monthly rainfall, seasonal rainfall, one season day by day, distribution,
    # annual rainfall, temperature, and the maize water-use chart.
    assert len(app_default.get("plotly_chart")) == 7


def test_scenario_table_lists_every_past_season_of_the_window(app_default):
    seasons = frame_with(app_default, "Rank (1 = driest)")
    assert len(seasons) == 25
    assert list(seasons["Rank (1 = driest)"]) == list(range(1, 26))
    assert seasons["Rainfall (mm)"].min() == pytest.approx(102.1, abs=0.1)
    assert seasons["Rainfall (mm)"].max() == pytest.approx(556.1, abs=0.1)
    assert (seasons["Complete (%)"] == 100).all()


def test_selecting_dry_short_rains_filters_to_real_past_seasons():
    app = run_app()
    app.sidebar.radio(key="season_window").set_value("short-rains")
    app.sidebar.radio(key="season_category").set_value("dry").run()
    assert not app.exception
    seasons = frame_with(app, "Rank (1 = driest)")
    assert len(seasons) == 8 and set(seasons["Class"]) == {"dry"}
    assert list(seasons["Season"])[0] == "Short rains 2005"
    detail = app.selectbox(key="season_detail_short-rains_dry")
    assert detail.value == "short-rains-2008"  # the representative (median) dry season
    text = all_text(app)
    assert "In the 8 dry short rains seasons" in text


# --- Rotation Comparison ---------------------------------------------------------------------


def test_three_strategies_are_shown_side_by_side(app_default):
    text = all_text(app_default)
    for name in ("Continuous maize", "Maize rotated with cowpea", "Maize rotated with pigeon pea"):
        assert f"### {name}" in text
    assert "What changes between these strategies?" in text
    assert "Where evidence is missing the comparison is incomplete, not favourable." in text


def test_missing_indicators_remain_visible(app_default):
    text = all_text(app_default)
    assert "Pigeon pea, long rains: not available. No verified seasonal water-use value exists for pigeon pea." in text
    assert "Cowpea, long rains: not available." in text
    assert "Maize: not available. No soil pH was supplied." in text
    assert "Unavailable" in text


def test_conditional_results_show_their_conditions(app_default):
    text = all_text(app_default)
    assert "Condition: The crop figure is water use (evapotranspiration)" in text
    assert "not directly comparable without a water balance" in text


def test_every_result_offers_the_six_part_explanation(app_default):
    text = all_text(app_default)
    for part in (
        "What it measures:", "What data it uses:", "What assumptions apply:", "What the result means:",
        "What it does not prove:", "What would improve confidence:",
    ):
        assert part in text
    expanders = [item.label for item in app_default.expander]
    assert expanders.count("How to read this result") >= 30


def test_downloads_are_offered(app_default):
    labels = [item.label for item in app_default.get("download_button")]
    assert labels == ["Summary (Markdown)", "Full report (JSON)", "Comparison record (JSON)"]


# --- Priorities -------------------------------------------------------------------------


def test_priorities_reorder_and_flag_missing_evidence_without_weights():
    app = run_app()
    app.sidebar.multiselect(key="farmer_priorities").set_value(["water_use", "market_suitability"]).run()
    assert not app.exception
    text = all_text(app)
    assert "Your priorities" in text
    assert "**1. Water conservation**" in text and "**2. Market and economic considerations**" in text
    assert "Nothing is estimated" in text and "prices" in text
    assert "Priorities have no weights" in text
    assert "★" in text


def test_priorities_do_not_change_the_results():
    plain = run_app()
    plain_headlines = sorted(item.value for item in plain.markdown if item.value.startswith("Maize, long rains"))
    chosen = run_app()
    chosen.sidebar.multiselect(key="farmer_priorities").set_value(["crop_diversity"]).run()
    chosen_headlines = sorted(item.value for item in chosen.markdown if item.value.startswith("Maize, long rains"))
    assert plain_headlines == chosen_headlines and plain_headlines


# --- Soil inputs -------------------------------------------------------------------------


def test_soil_defaults_to_none_and_says_so(app_default):
    assert app_default.radio(key="soil_mode").value == "none"
    assert "No soil information. Soil results stay unavailable" in all_text(app_default)


def test_demonstration_soil_is_labelled_illustrative_everywhere():
    app = run_app()
    app.radio(key="soil_mode").set_value("demonstration").run()
    assert not app.exception
    text = all_text(app)
    assert "Illustrative soil profile — not measured at Katumani." in text
    assert "hypothetical demonstration soil" in text  # in the soil result headlines
    soil = frame_with(app, "Stated source")
    assert set(soil["Verification"]) == {"hypothetical"}
    assert "An illustrative soil profile is in use" in text


def submit_soil(app: AppTest, **values) -> AppTest:
    app.radio(key="soil_mode").set_value("entered").run()
    for key, value in values.items():
        widget = app.get_by_key(f"soil_form_{key}")
        widget.set_value(value)
    submit = next(button for button in app.button if button.label == "Use this soil information")
    submit.click().run()
    return app


def test_entered_soil_changes_only_soil_results_and_keeps_provenance():
    app = submit_soil(run_app(), ph=5.2, ph_source="lab_measured", water_basis="texture", texture="loam")
    assert not app.exception
    text = all_text(app)
    assert "Your soil information is applied" in text
    assert "Maize: soil pH 5.2 is inside the tolerated range of 4.3 to 8.7." in text
    assert "Maize: the root zone (1 to 1.7 m) could hold about 130 to 306 mm of plant-available water." in text
    soil = frame_with(app, "Stated source")
    assert "lab measured" in set(soil["Stated source"]) and set(soil["Verification"]) == {"not verified"}
    # Weather results are untouched by soil.
    assert "Maize, long rains: season rainfall was below the indicative water use of 500 to 800 mm in 24 of 25" in text


def test_invalid_soil_input_is_rejected_and_not_applied():
    app = submit_soil(run_app(), water_basis="fc_wp", field_capacity=0.10, wilting_point=0.20)
    assert not app.exception
    errors = " ".join(item.value for item in app.error)
    assert "Not applied" in errors and "field capacity must be greater than the wilting point" in errors
    assert "Maize: not available. Soil water information is missing." in all_text(app)


def test_incomplete_soil_water_choice_is_explained():
    app = submit_soil(run_app(), water_basis="texture")
    assert "Choose a texture class" in " ".join(item.value for item in app.error)


# --- Scientific evidence and integrity -----------------------------------------------------------


def test_knowledge_base_summary_is_provisional_and_shows_its_gaps(app_default):
    crops = frame_with(app_default, "Not established")
    assert list(crops["Crop"]) == [
        "Common bean (dry)", "Cowpea", "Maize", "Mung bean (green gram)", "Pigeon pea", "Sorghum (grain)"
    ]
    assert set(crops["Family"]) == {"Fabaceae", "Poaceae"}
    assert set(crops["Record status"]) == {"provisional", "incomplete"}
    assert (crops["Not established"] > 0).all()  # gaps are visible for every crop
    text = all_text(app_default)
    assert "the pilot site has not been approved" in text
    assert "1 hard" in text and "1 recorded as unsupported" in text
    assert "None was filled with an estimate" in text


def test_evidence_panel_shows_versions_audit_sources_and_limits(app_default):
    text = all_text(app_default)
    assert "Agronomic knowledge base (provisional)" in text
    assert "13 sources and 205 cited claims" in text
    assert "Of 205 cited claims: 97 verified as stated, 78 verified under stated conditions, 22 resting on an abstract" in text
    sources = frame_with(app_default, "Access")
    assert len(sources) == 13
    for heading in ("Maize rainfall comparison.", "Cowpea temperature comparison.", "Pigeon pea water information.",
                    "Historical scenarios.", "Pilot status."):
        assert heading in text
    assert "does not prove that cowpea is unsuitable" in text


def test_unsupported_outcomes_come_from_the_engine(app_default):
    from src.uncertainty import UNSUPPORTED_OUTCOMES

    text = all_text(app_default)
    assert "What CropShift does not estimate" in text
    for item in UNSUPPORTED_OUTCOMES:
        assert f"**{item.outcome}.**" in text


FORBIDDEN = (
    "best rotation", "best overall", "most resilient", "highest yield", "most profitable", "safest",
    "recommended rotation", "we recommend", "recommended winner", "resilience score", "suitability score",
    "predicted yield", "will be dry", "will be wet", "forecast shows", "measured at katumani",
)


@pytest.mark.parametrize("phrase", FORBIDDEN)
def test_no_overclaiming_phrase_appears(app_default, phrase):
    text = all_text(app_default).lower()
    # Phrases that deny a claim ("not measured at Katumani", "no ... recommended") are allowed.
    cleaned = text.replace("not measured at katumani", "").replace("an overall resilience score or a 'best' rotation", "")
    assert phrase not in cleaned


def test_no_overclaiming_with_soil_and_priorities():
    app = run_app()
    app.radio(key="soil_mode").set_value("demonstration")
    app.sidebar.multiselect(key="farmer_priorities").set_value(["climate_resilience", "water_use"]).run()
    text = all_text(app).lower().replace("not measured at katumani", "").replace("an overall resilience score or a 'best' rotation", "")
    for phrase in FORBIDDEN:
        assert phrase not in text, phrase
    # Hypothetical soil is never called measured. ("Measured soil water properties"
    # appears only as advice on what would improve confidence.)
    advice = "measured soil water properties and a daily water balance"
    assert not re.search(r"(?<!not )measured soil", text.replace(advice, ""))
    assert "invented" in text


# --- Failure handling ------------------------------------------------------------------------


def test_app_fails_clearly_when_offline_data_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("NASA_DEMO_DIRECTORY", str(tmp_path / "empty-demo"))
    app = run_app()
    assert not app.exception
    assert "NASA data could not be loaded" in app.error[0].value
    assert "Offline mode is on" in app.error[0].value
    text = all_text(app)
    assert "Nothing is shown in its place" in text
    assert "The climate explorer needs the NASA pilot dataset" in text
    assert len(app.get("plotly_chart")) == 0 and len(app.success) == 0
    assert "13 sources and 205 cited claims" in text  # the knowledge base still works


def test_app_stops_cleanly_when_configuration_is_invalid(monkeypatch):
    monkeypatch.setenv("NASA_REQUEST_TIMEOUT", "-1")
    app = run_app()
    assert not app.exception
    assert "NASA_REQUEST_TIMEOUT" in app.error[0].value
    assert len(app.dataframe) == 0  # nothing else is rendered


def test_public_page_hides_error_details():
    import tomllib

    config = tomllib.loads((PROJECT_ROOT / ".streamlit" / "config.toml").read_text())
    assert config["client"]["showErrorDetails"] == "none"


# --- The twelve-step demonstration journey ------------------------------------------------------


def test_demonstration_walkthrough():
    app = run_app()  # 1. open
    assert not app.exception
    text = all_text(app)
    assert "Katumani area, Machakos County, Kenya" in text  # 2. pilot
    assert len(app.get("plotly_chart")) >= 5  # 3. NASA rainfall charts
    app.sidebar.radio(key="season_category").set_value("dry").run()  # 4. a dry scenario
    assert len(frame_with(app, "Rank (1 = driest)")) == 8
    text = all_text(app)
    assert "### Maize rotated with pigeon pea" in text  # 5. three rotations
    assert "In the 8 dry long rains seasons: rainfall below the range in 8" in text
    assert "What changes between these strategies?" in text  # 6. tradeoffs
    app = submit_soil(app, ph=6.0, water_basis="awc", available_water_capacity=150.0)  # 7. valid soil
    text = all_text(app)
    assert "Pigeon pea: the root zone (2 m) could hold about 300 mm" in text  # 8. soil results change
    app.sidebar.multiselect(key="farmer_priorities").set_value(["water_use"]).run()  # 9. a priority
    text = all_text(app)
    assert "**1. Water conservation**" in text
    assert "What it does not prove:" in text  # 10. explanations
    assert "POWER Project's Daily v2.10.3" in text and "Pilot status." in text  # 11. citations and limits
    assert [tab.label for tab in app.tabs][0] == "Overview" and not app.exception  # 12. overview still there
