# Phase A4 validation report

Phase A4: scientific evidence audit, soil integration, historical scenarios and
the crop-rotation comparison engine. Completed on 15 November 2026, 08:35 to
09:30 Singapore time.

## Test results

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` before any A4 change | 632 passed, 1 skipped |
| `.venv/bin/python -m pytest` after A4 | **802 passed, 1 skipped**, 0 failed |
| `.venv/bin/python -m pytest tests/test_live_power.py --run-live` | 1 passed |

The skipped test is the live NASA test, which runs only on request. 170 tests
are new:

| File | Tests | Covers |
| --- | --- | --- |
| `tests/test_evidence_audit.py` | 39 | Audit covers all 13 sources; both abstracts examined; matrix of 205 claims; every A4 numeric input re-checked; every route for an unsupported value refused |
| `tests/test_soil_inputs.py` | 33 | The three mappings; valid, invalid, missing and hypothetical soil; provenance; FAO-56 Eq. 82 and 83 by hand |
| `tests/test_scenario_engine.py` | 34 | Windows (including year-crossing); pilot configuration; season totals, counts and completeness; tercile classification and ties; the real 25-year record |
| `tests/test_comparison_engine.py` | 58 | Strategies, every indicator, constraints, no score, no fabricated outcome, priorities without weights, uncertainty and explanations, provenance, determinism, offline run |
| `tests/test_imports.py` | +6 | The six new modules import and are documented |

### Existing tests changed, and why

| Test | Change | Guarantee kept |
| --- | --- | --- |
| `test_rotation_constraints.py::test_the_only_hard_constraint_is_justified_and_declares_its_assumption` | Expected the A3 wording "would be this project's assumption"; now expects the ETCCDI definition | The constraint still states how frost is defined and that its agronomic source gives no temperature |
| `test_models.py::test_registry_can_be_filtered_by_domain` | Expected no indicator variables; A1 left them to A4, which declares three | The test now pins exactly those three, so no other indicator can appear unnoticed |
| `test_imports.py` (two tests) | Phase A4 and its six modules marked complete | The status table must still match the code |
| `test_app.py::test_app_states_its_development_stage_honestly` | "A3 of A9" to "A4 of A9" | The page must still say it shows no comparison and no recommendations |

### Failures met during A4, all fixed

* `test_models.py::test_registry_can_be_filtered_by_domain` failed when the new
  indicator variables were registered: the legitimate contract change above.
* `test_comparison_engine.py::test_no_overall_score_or_ranking` failed because
  it searched the whole report for "resilience score", which appears in the
  list of outcomes the tool *refuses* to compute. The test now excludes that
  list; the engine was right.

## Pilot results in brief

From the real NASA record, offline, with no soil information:

* Long rains (March to May): 25 complete seasons, 102 to 556 mm, median 209 mm.
  Short rains (October to December): 25 seasons, 110 to 490 mm, median 232 mm.
  No frost day in any season; the lowest daily minimum was about 12 °C.
* Rainfall within the window fell below the low end of maize's indicative
  seasonal water use (500 mm) in 24 of 25 long-rains seasons and 25 of 25
  short-rains seasons. Maize's documented growing period (125-180 days) is
  longer than either 92-day window, so rain outside the window and stored soil
  water are not counted: this is a first indication, not a water balance.
* Cowpea and pigeon pea water indicators are unavailable: no verified value
  exists. Pigeon pea's documented temperature range (20-40 °C) contained the
  daily mean on about 96 % of days; cowpea's (25-35 °C) on almost none, with
  the caveat that the source does not say which temperature it means.
* Continuous maize: one plant family, every step repeats the crop, no legume.
  The two rotations: two families, no repetition, one legume each, and a pest
  and disease consideration from the Machakos study.

The full tables are in `historical_scenarios.md` and
`rotation_comparison_methodology.md`.

## Acceptance checklist

| Criterion | Result | Note |
| --- | --- | --- |
| A1-A3 repository and test baseline reviewed | Passed | 632 passed, 1 skipped before any change |
| All thirteen scientific references audited | Passed | All reachable on 15 Nov; metadata confirmed |
| Both abstract-only sources assessed | Passed | Neither supports a numeric threshold; Franke full text found to be open access but not read; Rao full text restricted |
| Claims used by calculations verified or excluded | Passed | The gate admits numeric inputs only if re-checked in A4; 8 claims excluded |
| Evidence-gate tests pass | Passed | 39 audit tests plus gate tests in the engine suite |
| Three soil mappings implemented | Passed | pH, root-zone water (Eq. 82), readily available water (Eq. 83) |
| Soil validation and provenance work | Passed | |
| Missing soil inputs handled safely | Passed | Indicators unavailable with guidance; no default soil |
| Pilot location status explicitly recorded | Passed | PROVISIONAL in the configuration and every report |
| Planting-calendar assumptions documented | Passed | Unknown by default; hypothetical when chosen |
| Historical scenarios implemented | Passed | |
| Dry/typical/wet classification reproducible | Passed | Tested twice on the real record and with ties |
| Historical observations remain traceable | Passed | Dataset id, SHA-256, citations and real season ids carried through |
| Three candidate rotation strategies represented | Passed | All three are systems the Machakos study grew |
| Crop-environment comparisons implemented where supported | Passed | 11 indicators |
| Missing pigeon-pea water information remains unavailable | Passed | Also cowpea |
| Farmer priorities integrated without arbitrary weights | Passed | Order only; no weight field |
| Uncertainty and limitations exposed | Passed | Categories, confidence with reasons, six-part explanations |
| No unsupported resilience score generated | Passed | `overall_score` can only be empty |
| No fabricated yield, profit or soil-health outcomes | Passed | Eight unsupported outcomes listed with reasons |
| Offline comparison execution works | Passed | About one second, bundled data, network guard on |
| New tests pass | Passed | 170 |
| Existing regression tests pass | Passed | |
| Documentation updated | Passed | Seven new documents; nine updated |
| A5 interface contracts documented | Passed | Below |
| No paid external service activated | Passed | Only free public pages and APIs were read |
| No later phase started | Passed | The app page still shows no comparison |

## A5 interface

The engine has no Streamlit dependency. A5 should call one function and display
one object.

```python
from src.comparison_engine import PrioritySelection, run_pilot_comparison
from src.models import PriorityDimension
from src.soil_inputs import SoilProfileInput, SoilValueInput, demonstration_soil_profile
from src.season_config import CANDIDATE_STRATEGIES

report = run_pilot_comparison(
    settings=settings,                        # src.config.Settings; offline mode respected
    soil=SoilProfileInput(...) or None,       # or demonstration_soil_profile(), labelled hypothetical
    priorities=PrioritySelection(dimensions=(PriorityDimension.WATER_USE, ...)) or None,
    strategies=CANDIDATE_STRATEGIES,          # or strategies with .with_seasons(...)
)
```

For finer control (caching the scenarios across reruns): `load_knowledge_base()`,
`load_evidence_gate(kb)`, `pilot_configuration()`, `load_pilot_dataset(...)`,
`build_scenarios(dataset, config.windows)`, then `compare_strategies(...)`.

What A5 reads from `ComparisonReport`:

| Field | Use |
| --- | --- |
| `pilot_status`, `approval_note`, `limitations` | Banner: provisional site, hypothetical soil, no score |
| `scenarios` (`ScenarioOverview`) | Per window: boundaries, representative seasons, variability |
| `strategies[i].profile` | Sequence, families, documented study, assumptions |
| `strategies[i].indicators` (`IndicatorResult`) | `headline`, `status`, `uncertainty.confidence`, `values`, `category_summaries` (dry/typical/wet), `season_findings` (one per past season, for charts), `conditions`, `missing`, `information_layers`, `explanation` (six parts) |
| `strategies[i].constraints` | Findings with outcome and the farmer explanation |
| `strategies[i].background` | Cited context, marked abstract-only where it is |
| `strategies[i].completeness` | Supported, conditional and unavailable counts |
| `priorities` (`PriorityView`) | `indicator_order` for display order; sections with unsupported notes |
| `tradeoffs` | Side-by-side statements, no winner |
| `unsupported_outcomes` | What the tool does not estimate, and why |
| `soil` (`ResolvedSoil`) | What soil was used, its source class and verification, and what is missing |
| `dataset_citations`, `payload_sha256`, `knowledge_base_version`, `audit_version` | Sources and provenance panel |

`report.to_comparison_result()` gives the A1 `ComparisonResult` for export or
SQLite storage. The scenario set (`ScenarioSet`) also exposes every season's
daily values for charts.

## What remains open

* The pilot site needs the participant's approval (U5, C8).
* No reference evapotranspiration, wind speed or IMERG (deferred by the brief).
* No agronomist has reviewed the knowledge base or the indicators.
* Pigeon pea and cowpea lack water-use, growing-period and (pigeon pea)
  depletion-fraction evidence.
* The confidence rule and tercile method are this project's own choices.
