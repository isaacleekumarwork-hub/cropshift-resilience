"""Module imports and honest build status.

These tests keep the status table in ``src/__init__.py`` truthful: every file
is listed, every listed file imports, and a module marked as a placeholder
really contains no implementation.
"""

from __future__ import annotations

import importlib
import inspect

import pytest

import src
from src.config import PROJECT_ROOT

MODULE_NAMES = [module.name for module in src.MODULES]


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_module_imports_and_is_documented(name):
    module = importlib.import_module(f"src.{name}")
    assert module.__doc__ and len(module.__doc__.strip()) > 40


def test_status_table_matches_the_files_on_disk():
    on_disk = {path.stem for path in (PROJECT_ROOT / "src").glob("*.py") if path.stem != "__init__"}
    assert on_disk == set(MODULE_NAMES)
    assert len(MODULE_NAMES) == len(set(MODULE_NAMES))


@pytest.mark.parametrize("module", [item for item in src.MODULES if not item.implemented], ids=lambda m: m.name)
def test_placeholders_contain_no_implementation(module):
    loaded = importlib.import_module(f"src.{module.name}")
    defined_here = [
        name
        for name, value in vars(loaded).items()
        if not name.startswith("_")
        and (inspect.isfunction(value) or inspect.isclass(value))
        and getattr(value, "__module__", None) == loaded.__name__
    ]
    assert defined_here == [], f"{module.name} is listed as a placeholder but defines {defined_here}"
    assert "Not implemented" in loaded.__doc__


def _defines_something(name: str) -> bool:
    loaded = importlib.import_module(f"src.{name}")
    return any(
        (inspect.isfunction(value) or inspect.isclass(value))
        and getattr(value, "__module__", None) == loaded.__name__
        for key, value in vars(loaded).items()
        if not key.startswith("_")
    )


@pytest.mark.parametrize("module", [item for item in src.MODULES if item.implemented], ids=lambda m: m.name)
def test_modules_marked_as_working_really_contain_code(module):
    assert _defines_something(module.name)
    assert "Not implemented" not in importlib.import_module(f"src.{module.name}").__doc__


def test_working_modules_belong_to_finished_phases_only():
    finished = {phase.code for phase in src.PHASES if phase.status == "complete"}
    for module in src.MODULES:
        if module.deferred:
            # Deliberately not built in its phase: it must still be an empty
            # placeholder (checked above), and the reason must be stated.
            assert not module.implemented and module.phase in finished and len(module.deferred) > 20, module.name
            continue
        assert module.implemented == (module.phase in finished), module.name


def test_only_the_persistence_module_is_deferred():
    assert [module.name for module in src.MODULES if module.deferred] == ["persistence"]


def test_data_and_knowledge_modules_are_working():
    working = {module.name for module in src.MODULES if module.implemented}
    assert working == {
        "config",
        "models",
        "nasa_client",
        "nasa_cache",
        "pilot_sites",
        "data_validation",
        "data_processing",
        "data_service",
        "crop_knowledge",
        "evidence_audit",
        "soil_inputs",
        "season_config",
        "scenario_engine",
        "comparison_engine",
        "uncertainty",
        "visualizations",
        "ui_state",
        "report_service",
    }


def test_phase_plan_is_consistent():
    codes = [phase.code for phase in src.PHASES]
    assert codes == [f"A{number}" for number in range(1, 10)]
    assert src.CURRENT_PHASE in codes
    assert {module.phase for module in src.MODULES} <= set(codes)
    # Every phase up to the current one is complete; nothing later has begun.
    current = codes.index(src.CURRENT_PHASE)
    for index, phase in enumerate(src.PHASES):
        assert phase.status == ("complete" if index <= current else "not started"), phase.code
    assert src.CURRENT_PHASE == "A5"


def test_optional_ai_libraries_are_not_imported_by_the_core():
    import sys

    for name in MODULE_NAMES:
        importlib.import_module(f"src.{name}")
    assert "openai" not in sys.modules
