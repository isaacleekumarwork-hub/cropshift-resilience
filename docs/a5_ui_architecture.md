# Interface architecture (phase A5)

## Files

| File | Role | Imports Streamlit? |
| --- | --- | --- |
| `app.py` | The only page: loading, sidebar, six tabs, footer. Arranges and labels engine results; calculates nothing | Yes |
| `src/visualizations.py` | Plotly figures from engine objects; colour-blind-safe palette; caveats in every subtitle | No |
| `src/ui_state.py` | Widget values to typed engine inputs (`Selections`, `soil_form_to_profile`); session keys | No |
| `src/report_service.py` | Markdown summary, full JSON, A1 `ComparisonResult` JSON | No |
| `.streamlit/config.toml` | No telemetry; generic error messages in the browser (`showErrorDetails = "none"`); theme colour | — |

`src/persistence.py` stays a placeholder and is marked *deferred* in the build
status table: the A5 brief says not to store user inputs without an explicit
need, and the downloads cover keeping a result.

The scientific engine (`comparison_engine`, `scenario_engine`, `soil_inputs`,
`evidence_audit`, `uncertainty`) is unchanged and imports no Streamlit.

## Data flow on each run

```
settings ─┐
          ├─ _pilot_dataset (cache_resource, key: request, offline flag, folders, threshold, URL)
          ├─ _knowledge      (cache_resource: knowledge base + evidence gate)
          ├─ _scenarios      (cache_resource, key: dataset id + SHA-256)
          ├─ _climatology    (cache_resource, key: dataset id + SHA-256)
sidebar widgets ──> ui_state.read_selections(session_state) ──> Selections
          └─ _report         (cache_resource, max 32 entries,
                              key: dataset SHA-256, knowledge-base version, audit version,
                                   soil profile JSON, priority order)
tabs render from: dataset, scenarios, report, selections
```

* Immutable inputs are cached once per configuration; changing a widget never
  rebuilds them and never contacts NASA.
* The report cache key contains everything the report depends on and nothing
  it does not: the soil profile (as validated JSON) and the priority order. The
  season window and class are display filters only, so they are not in the key.
  Two users with different soil inputs never share a result.
* Measured on a laptop: first load about 3-5 seconds, later interactions about
  0.2-0.6 seconds (Streamlit's test runner).

## State

All session keys are named in `ui_state` (`season_window`, `season_category`,
`farmer_priorities`, `soil_mode`, `entered_soil_profile`, `soil_errors`, and the
`soil_form_*` widgets). The soil form is a Streamlit form: values are applied
together when *Use this soil information* is pressed. Its callback validates
them with `soil_form_to_profile`; a valid profile is stored in the session, an
invalid one is discarded and the reasons are shown. Changing the soil mode clears
earlier entries. Nothing is written to disk.

## Failure handling

| Failure | What the user sees |
| --- | --- |
| Invalid configuration | One error naming the settings (never their values); the app stops |
| NASA data missing or corrupted, or offline with no bundled data | Error in the Overview with what to do; Climate Explorer and Comparison say why they are empty; the knowledge base and evidence still show |
| Knowledge base cannot load | The comparison and evidence sections say so; the NASA sections still work |
| Invalid soil input | The reasons, and *Not applied*; the comparison runs without that soil |
| Comparison fails unexpectedly | A plain message; details go to the server log |
| Any section fails unexpectedly | `_guarded` shows "could not be shown", the other tabs still render, and the stack trace goes only to the server log |

## Accessibility and design choices

* Okabe-Ito colours: orange, grey and blue for dry, typical and wet (rainfall
  classes); blue, orange and grey text for supported, conditional and
  unavailable. No red or green verdict colours.
* Every chart has axis titles with units and a subtitle carrying its main
  caveat; every temperature line names its statistic.
* Status is always written in words, never shown by colour alone.
* Wide layout; columns stack on narrow screens.
