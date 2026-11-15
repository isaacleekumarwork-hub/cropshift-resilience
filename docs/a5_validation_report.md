# Phase A5 validation report

Phase A5: the interactive Streamlit application. Completed on 15 November 2026,
10:05 to 10:35 Singapore time.

## Test results

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` before any A5 change | 802 passed, 1 skipped (as A4 reported) |
| `.venv/bin/python -m pytest` after A5 | **866 passed, 1 skipped**, 0 failed (867 collected) |
| `.venv/bin/python -m streamlit run app.py` | Starts at http://localhost:8501; checked in a browser |

The skipped test is the live NASA test, which runs only with `--run-live`. The
data layer did not change in A5, so it was not rerun; it passed in A4.

### New and changed tests

| File | Tests | Change |
| --- | --- | --- |
| `tests/test_interface_modules.py` | 26, new | Charts plot exactly the engine's values; colours are classes, not verdicts; interface state is typed and safe by default; the soil form refuses invalid input; export round-trips and carries limits |
| `tests/test_app.py` | 49 (was 12) | Rewritten for the six-tab application; see below |
| `tests/test_imports.py` | 48 (was 47) | A5 modules marked working; a module deferred on purpose must stay an empty placeholder and state why (new test) |

What happened to the twelve A4 app tests:

| A4 test | Now |
| --- | --- |
| Starts without errors | Kept |
| States its development stage (A4, "no rotation comparison") | Replaced by `test_app_states_its_stage_and_its_limits_honestly`: the comparison now exists by design; the stage (A5) and the banner's three limits are checked instead |
| Location, source, period, origin | Kept, plus the observation count and site status |
| Quality never overstated | Kept |
| Variables, first and last observations | Kept; tables are found by their columns instead of their position on the page |
| Citation and provenance | Kept |
| Monthly table | Kept; found by its month index |
| "Shows no agronomic results or charts" | Replaced: A5 adds charts and results on purpose. Its guarantee (no recommendation, predicted yield or suitability score) is kept and widened to 16 phrases in `test_no_overclaiming_phrase_appears` and `test_no_overclaiming_with_soil_and_priorities` |
| Knowledge base summary | Kept in `test_knowledge_base_summary_is_provisional_and_shows_its_gaps`; the sentence "No crop is compared with the NASA data yet" is no longer true and is no longer expected |
| AI services disabled | Kept |
| Offline data missing | Kept; now also checks that the climate explorer explains why it is empty and that no chart is drawn |
| Invalid configuration | Kept |

### Failures met during A5, all fixed

* Plotly box plots do not accept one colour per point: the distribution chart
  failed. It now draws points as a separate, deterministic layer.
* Two tables mixed numbers and text in one column, which the table component
  rejects: the source year ("undated") and the soil value ("loam"). Both columns
  are now text.
* An overclaiming test caught the app's own sentence "names no best rotation";
  it was reworded.
* The "measured soil" check caught the engine's advice "measured soil water
  properties … would improve confidence"; the check now allows that advice and
  nothing else.
* **Found in the browser:** after a code edit, Streamlit's hot reload left
  cached objects holding enums from old module copies; an identity comparison
  then failed in the unguarded sidebar and took the page down. Fixed by
  comparing by value and guarding the sidebar. See `a5_demo_walkthrough.md`.

## Demonstration walkthrough

All twelve steps pass in `test_demonstration_walkthrough`. In the browser,
steps 1, 3, 4, 5, 7 and 8 were done by hand, steps 2 and 6 were seen on screen,
and an invalid soil entry was refused as designed. Steps 9 to 12 were verified
by the automated test only. Details: `a5_demo_walkthrough.md`.

## Acceptance checklist

| Requirement | Result | Note |
| --- | --- | --- |
| A1-A4 baseline verified | Passed | 802 passed, 1 skipped before changes |
| Existing repository preserved | Passed | Engine unchanged except two value comparisons; no second app; no copied `src` |
| Streamlit app launches correctly | Passed | `.venv/bin/python -m streamlit run app.py` |
| No `src` import error | Passed | Browser run from the repository root with the project environment; the test runner loads `app.py` by its full path |
| Navigation implemented | Passed | Six tabs and a sidebar |
| Pilot overview implemented | Passed | |
| NASA historical rainfall charts work | Passed | Values equal the engine's (tested) |
| Temperature charts work | Passed | Each statistic labelled |
| Dry/typical/wet scenario selection works | Passed | |
| Three rotation strategies display | Passed | |
| Comparison indicators come from A4 | Passed | Rendered from `ComparisonReport` only |
| Tradeoffs come from A4 | Passed | Verbatim |
| Soil inputs validated | Passed | |
| Missing soil values handled | Passed | Unavailable with how to obtain |
| Hypothetical soil clearly labelled | Passed | "Illustrative soil profile — not measured at Katumani" |
| Farmer priorities work | Passed | |
| No arbitrary weights or ranking | Passed | |
| Evidence citations displayed | Passed | NASA, 13 sources with links, ETCCDI |
| Uncertainty explanations displayed | Passed | Six parts per result |
| Unsupported outcomes displayed | Passed | From the engine |
| No scientific overclaims | Passed | 16 phrases tested; review recorded in `a5_scientific_integrity.md` |
| Historical data provenance preserved | Passed | Citation, request, SHA-256 shown |
| Offline mode works | Passed | All app tests run offline |
| Caching behaves correctly | Passed | Report keyed by soil and priority order; priorities do not change results (tested) |
| Application errors handled gracefully | Passed | Guards on every tab and the sidebar; no stack trace in the browser |
| End-to-end walkthrough completed | Passed | See above for what was manual |
| New UI tests pass | Passed | |
| Existing regression tests pass | Passed | |
| Documentation updated | Passed | Five new A5 documents; README, architecture, plan, provenance, requirements updated |
| No paid external service activated | Passed | |
| No A6 or later phase started | Passed | |

## A6 readiness (not implemented)

What exists for an optional OpenAI explanation:

| Item | Where | State |
| --- | --- | --- |
| Switch | `Settings.enable_openai` (`ENABLE_OPENAI`) | Default `false` |
| Key | `Settings.openai_api_key` (`OPENAI_API_KEY`), a `SecretStr` never printed | Empty |
| Readiness | `Settings.openai_ready`: true only when the switch is on and a key is present | False |
| Status shown | `Settings.integration_status()`, displayed in the sidebar and About tab | "disabled" |
| Module | `src/openai_service.py` | Placeholder; imports no OpenAI library |
| Dependency | `requirements.txt` | `openai` deliberately not installed |

Safe integration points, if A6 is approved:

* **Input:** the finished report only, as text: `report_service.summary_markdown(report)`
  or `report.to_comparison_result()`. The service must never see raw data it
  could reinterpret, and must never feed anything back into the engine.
* **Output:** a separate, opt-in panel on the Rotation Comparison tab, labelled
  as AI-generated, below the engine's results, which stay unchanged. With the
  service off or failing, the page is exactly what it is today.
* **Tests to add:** no request without both switch and key; the engine's report
  is identical with the service on or off; the output is labelled; a failure
  shows a plain message.

Recommendation: given the time left, skip A6 and A7 and go to A8.
