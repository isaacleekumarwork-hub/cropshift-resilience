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


def test_only_foundation_modules_are_marked_as_working():
    working = {module.name for module in src.MODULES if module.implemented}
    assert working == {"config", "models"}


def test_phase_plan_is_consistent():
    codes = [phase.code for phase in src.PHASES]
    assert codes == [f"A{number}" for number in range(1, 10)]
    assert src.CURRENT_PHASE == "A1"
    assert {module.phase for module in src.MODULES} <= set(codes)
    started = [phase.code for phase in src.PHASES if phase.status != "not started"]
    assert started == ["A1"]


def test_optional_ai_libraries_are_not_imported_by_the_core():
    import sys

    for name in MODULE_NAMES:
        importlib.import_module(f"src.{name}")
    assert "openai" not in sys.modules
