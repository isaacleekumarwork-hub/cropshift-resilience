"""A5 helper modules: charts, interface state and export.

These run without Streamlit. Charts are checked against the engine's values:
every plotted number must be a number the A2 data or the A4 engine produced.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from src import report_service, ui_state, visualizations as viz
from src.comparison_engine import compare_strategies
from src.models import PriorityDimension, ScenarioCategory
from src.scenario_engine import build_scenarios
from src.season_config import pilot_configuration
from src.soil_inputs import SoilSourceClass

STAMP = datetime(2026, 11, 15, 2, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def scenarios(pilot_dataset):
    return build_scenarios(pilot_dataset, pilot_configuration().windows)


@pytest.fixture(scope="module")
def report(scenarios, kb, gate):
    return compare_strategies(scenarios=scenarios, kb=kb, gate=gate, config=pilot_configuration(), generated_at=STAMP)


# --- Charts ---------------------------------------------------------------------------


def test_seasonal_rainfall_chart_plots_the_engine_totals(scenarios):
    window = scenarios.window("long-rains")
    figure = viz.seasonal_rainfall_figure(window)
    plotted = {x: y for trace in figure.data for x, y in zip(trace.x, trace.y)}
    assert plotted == {item.season_year: item.rainfall_total_mm for item in window.classified()}
    assert "not a forecast" in figure.layout.title.text
    assert figure.layout.yaxis.title.text == "Rainfall over the window (mm)"


def test_seasonal_chart_colours_are_rainfall_classes_not_verdicts(scenarios):
    figure = viz.seasonal_rainfall_figure(scenarios.window("short-rains"), highlight=ScenarioCategory.DRY)
    colours = {trace.name.split(" ")[0]: trace.marker.color for trace in figure.data}
    assert colours == {"Dry": "#E69F00", "Typical": "#8C8C8C", "Wet": "#0072B2"}
    opacity = {trace.name.split(" ")[0]: trace.opacity for trace in figure.data}
    assert opacity["Dry"] == 1.0 and opacity["Wet"] < 1.0
    for colour in colours.values():
        assert colour.upper() not in ("#FF0000", "#00FF00", "#008000")


def test_distribution_chart_shows_every_season(scenarios):
    figure = viz.rainfall_distribution_figure(scenarios)
    points = [y for trace in figure.data if trace.type == "scatter" for y in trace.y]
    expected = [item.rainfall_total_mm for window in scenarios.windows for item in window.classified()]
    assert sorted(points) == sorted(expected) and len(points) == 50


def test_temperature_chart_names_each_statistic(scenarios):
    figure = viz.temperature_figure(scenarios.window("long-rains"))
    names = [trace.name for trace in figure.data]
    assert names == ["Highest daily maximum", "Mean of daily maximum", "Mean of daily mean", "Mean of daily minimum", "Lowest daily minimum"]
    mean = next(trace for trace in figure.data if trace.name == "Mean of daily mean")
    window = scenarios.window("long-rains")
    assert list(mean.y) == [item.mean_temperature_c for item in sorted(window.seasons, key=lambda s: s.season_year)]


def test_daily_chart_uses_the_nasa_daily_values(scenarios):
    season = scenarios.season("long-rains-2019")
    figure = viz.season_daily_figure(season)
    rain = figure.data[0]
    assert list(rain.y) == list(season.daily_precipitation_mm) and len(rain.y) == 92
    assert "not smoothed" in figure.layout.title.text


def test_water_use_chart_states_it_is_not_a_water_balance(report):
    result = report.strategy("continuous-maize").indicator("rainfall_vs_crop_water_use", window_id="long-rains")[0]
    figure = viz.water_use_figure(result, "Maize", "Long rains")
    assert "Not a water balance" in figure.layout.title.text
    shapes = [shape for shape in figure.layout.shapes]
    assert (shapes[0].y0, shapes[0].y1) == (500.0, 800.0)
    plotted = sorted(y for trace in figure.data for y in trace.y)
    assert plotted == sorted(item.value for item in result.season_findings)


def test_monthly_and_annual_charts(pilot_dataset, scenarios):
    from src.data_processing import monthly_climatology, monthly_summary

    climatology = monthly_climatology(monthly_summary(pilot_dataset))
    figure = viz.monthly_rainfall_figure(climatology, [(3, 5), (10, 12)])
    assert len(figure.data[0].y) == 12 and len(figure.layout.shapes) == 2
    annual = viz.annual_rainfall_figure(scenarios)
    assert list(annual.data[0].y) == [item.total_mm for item in scenarios.annual_rainfall if item.complete]


# --- Interface state ---------------------------------------------------------------------


WINDOWS = ["long-rains", "short-rains"]


def test_defaults_are_safe_and_empty():
    selections = ui_state.read_selections({}, window_ids=WINDOWS)
    assert selections.window_id == "long-rains" and selections.category is None
    assert selections.priorities == () and selections.soil is None and selections.soil_mode == ui_state.SOIL_MODE_NONE
    assert selections.priority_selection is None
    assert selections.cache_key() == ("no-soil", ())


def test_selections_are_typed_and_keep_the_farmers_order():
    state = {
        ui_state.WINDOW_KEY: "short-rains",
        ui_state.CATEGORY_KEY: "wet",
        ui_state.PRIORITIES_KEY: ["crop_diversity", "water_use"],
    }
    selections = ui_state.read_selections(state, window_ids=WINDOWS)
    assert selections.category is ScenarioCategory.WET
    assert selections.priorities == (PriorityDimension.CROP_DIVERSITY, PriorityDimension.WATER_USE)
    assert selections.priority_selection.dimensions[0] is PriorityDimension.CROP_DIVERSITY


def test_unknown_window_falls_back_to_the_first():
    assert ui_state.read_selections({ui_state.WINDOW_KEY: "monsoon"}, window_ids=WINDOWS).window_id == "long-rains"


def test_demonstration_mode_gives_the_hypothetical_profile():
    selections = ui_state.read_selections({ui_state.SOIL_MODE_KEY: ui_state.SOIL_MODE_DEMO}, window_ids=WINDOWS)
    assert selections.soil.hypothetical


def test_entered_mode_without_a_valid_profile_has_no_soil():
    selections = ui_state.read_selections({ui_state.SOIL_MODE_KEY: ui_state.SOIL_MODE_ENTERED}, window_ids=WINDOWS)
    assert selections.soil is None


def test_empty_soil_form_gives_no_profile_and_no_error():
    assert ui_state.soil_form_to_profile({}) == (None, [])


def test_soil_form_builds_a_profile_with_sources():
    profile, errors = ui_state.soil_form_to_profile(
        {
            "ph": 6.1, "ph_source": "lab_measured", "source_identifier": "Report 17",
            "water_basis": "fc_wp", "field_capacity": 0.30, "wilting_point": 0.15, "water_source": "user_reported",
            "drainage": "poorly_drained", "drainage_source": "user_reported",
            "depth_top_cm": 0.0, "depth_bottom_cm": 30.0, "collected_on": date(2026, 3, 1), "applies_to": "North field",
        }
    )
    assert errors == []
    assert profile.soil_ph.source_class is SoilSourceClass.LAB_MEASURED and profile.soil_ph.source_identifier == "Report 17"
    assert profile.field_capacity.value == 0.30 and profile.drainage.drainage_class.value == "poorly_drained"
    assert profile.label == "North field" and not profile.hypothetical


def test_soil_form_uses_only_the_chosen_water_option():
    profile, _ = ui_state.soil_form_to_profile(
        {"water_basis": "texture", "texture": "loam", "field_capacity": 0.3, "wilting_point": 0.1, "available_water_capacity": 80.0}
    )
    assert profile.texture.texture_class.value == "loam"
    assert profile.field_capacity is None and profile.available_water_capacity is None


@pytest.mark.parametrize(
    "values, message",
    [
        ({"water_basis": "fc_wp", "field_capacity": 0.1, "wilting_point": 0.2}, "greater than the wilting point"),
        ({"water_basis": "fc_wp", "field_capacity": 0.3}, "both field capacity and wilting point"),
        ({"water_basis": "awc"}, "available water capacity"),
        ({"water_basis": "texture"}, "Choose a texture class"),
        ({"ph": 6.0, "ph_source": "public_soil_dataset"}, "name the dataset"),
        ({"ph": 6.0, "depth_top_cm": 40.0, "depth_bottom_cm": 30.0}, "depth_bottom_cm"),
    ],
)
def test_invalid_soil_form_is_reported_and_gives_no_profile(values, message):
    profile, errors = ui_state.soil_form_to_profile(values)
    assert profile is None and errors
    assert message in " ".join(errors)


def test_interface_state_module_never_imports_streamlit():
    import inspect

    assert "import streamlit" not in inspect.getsource(ui_state)
    assert "import streamlit" not in inspect.getsource(viz)
    assert "import streamlit" not in inspect.getsource(report_service)


# --- Export -------------------------------------------------------------------------------


def test_report_json_round_trips(report):
    from src.comparison_engine import ComparisonReport

    restored = ComparisonReport.model_validate_json(report_service.report_json(report))
    assert restored.model_dump() == report.model_dump()


def test_comparison_record_is_the_a1_contract(report):
    data = json.loads(report_service.comparison_result_json(report))
    assert data["rotation_ids"] == ["continuous-maize", "maize-cowpea", "maize-pigeon-pea"]
    assert data["current_practice_rotation_id"] == "continuous-maize"


def test_summary_carries_results_limits_and_no_score(report):
    text = report_service.summary_markdown(report)
    assert "**No overall score.**" in text
    assert report.approval_note in text
    assert "Pigeon pea, long rains: not available." in text
    assert "## What CropShift does not estimate" in text
    for citation in report.dataset_citations:
        assert citation in text
    assert "None supplied. Soil indicators are unavailable." in text
    for phrase in ("best rotation", "we recommend", "most resilient"):
        assert phrase not in text.lower().replace("an overall resilience score or a 'best' rotation", "")


def test_summary_labels_hypothetical_soil(scenarios, kb, gate):
    from src.soil_inputs import demonstration_soil_profile

    soil_report = compare_strategies(
        scenarios=scenarios, kb=kb, gate=gate, config=pilot_configuration(), soil=demonstration_soil_profile(), generated_at=STAMP
    )
    assert "Illustrative soil profile, invented for demonstration" in report_service.summary_markdown(soil_report)
