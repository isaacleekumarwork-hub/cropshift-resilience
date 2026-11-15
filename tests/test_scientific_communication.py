"""A8: the wording the user reads, and the A5 hot-reload defect.

The A8 review found three places where a headline or explanation said more than
its evidence: the maize rainfall headline did not say it counted only a 92-day
window; the temperature headlines did not say the sources leave their
temperature measure undefined; and two explanations generalised the legume
benefit. These tests pin the corrected wording. The last tests reproduce the
A5 hot-reload defect: enum members from a freshly reloaded module must still
match objects cached before the reload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

import pytest

from src.comparison_engine import compare_strategies
from src.models import PriorityDimension, ScenarioCategory
from src.scenario_engine import build_scenarios
from src.season_config import pilot_configuration

STAMP = datetime(2026, 11, 15, 3, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def scenarios(pilot_dataset):
    return build_scenarios(pilot_dataset, pilot_configuration().windows)


@pytest.fixture(scope="module")
def report(scenarios, kb, gate):
    return compare_strategies(scenarios=scenarios, kb=kb, gate=gate, config=pilot_configuration(), generated_at=STAMP)


def test_rainfall_headline_names_its_window_and_denies_a_water_balance(report):
    for strategy in report.strategies:
        for result in strategy.indicator("rainfall_vs_crop_water_use"):
            if result.status.value != "unavailable":
                assert "(rain within the 92-day window only; not a water balance)" in result.headline


def test_temperature_headlines_say_the_measure_is_undefined(report):
    found = 0
    for strategy in report.strategies:
        for result in strategy.indicator("temperature_vs_documented_range"):
            if result.status.value != "unavailable":
                found += 1
                assert "the source does not say which temperature it means" in result.headline
                assert "not evidence of unsuitability" in result.headline
    assert found


def test_legume_tradeoff_is_balanced(report):
    note = next(item for item in report.tradeoffs if item.aspect == "Legumes and pest management")
    assert "Past study results, not predictions" in note.statement
    assert "weaker effects after cowpea" in note.statement
    assert "maize after pigeon pea only marginally more" in note.statement


def test_no_explanation_says_a_legume_benefit_is_usual(kb, report):
    for constraint in kb.constraints:
        assert "usually means lower" not in constraint.user_explanation
    text = report.model_dump_json(exclude={"unsupported_outcomes"}).lower()
    assert "usually means lower" not in text


def test_cereal_explanation_carries_the_pigeon_pea_exception(kb):
    constraint = next(item for item in kb.constraints if item.constraint_id == "continuous-cereal-without-legume")
    assert "on average" in constraint.user_explanation
    assert "pigeon pea gained little" in constraint.user_explanation


# --- The A5 hot-reload defect ----------------------------------------------------------------------


def _reloaded(enum_class):
    """A fresh enum class with the same members, as a module reload would create."""
    return StrEnum(enum_class.__name__, {member.name: member.value for member in enum_class})


def test_cached_knowledge_base_answers_for_a_reloaded_priority_enum(kb):
    fresh = _reloaded(PriorityDimension)
    assert fresh.WATER_USE is not PriorityDimension.WATER_USE
    assert kb.priority(fresh.WATER_USE).dimension is PriorityDimension.WATER_USE


def test_cached_scenarios_filter_by_a_reloaded_category_enum(scenarios):
    fresh = _reloaded(ScenarioCategory)
    window = scenarios.window("long-rains")
    assert len(window.by_category(fresh.DRY)) == 8
    assert window.by_category(fresh.DRY) == window.by_category(ScenarioCategory.DRY)


def test_explanations_name_sources_by_title_not_by_a_truncated_author(report, kb):
    titles = [source.title for source in kb.sources]
    for strategy in report.strategies:
        for result in strategy.indicators:
            text = result.explanation.data_and_evidence_used
            for fragment in ("Heuzé V,", "Brouwer, C,", "Allen, R,"):
                assert fragment not in text, text
            if result.evidence and result.indicator_id in (
                "rainfall_vs_crop_water_use", "temperature_vs_documented_range", "growing_period_vs_window",
                "annual_rainfall_vs_documented_range",
            ):
                assert any(title in text for title in titles), text
