# Using the CropShift RESILIENCE application (phase A5)

## Launch

From the repository root, with the project's own environment:

```bash
.venv/bin/python -m streamlit run app.py
```

The app opens at http://localhost:8501. Running it this way uses the project's
Python 3.12 environment and finds the `src` package from the repository root;
no copy of `src` is needed anywhere. To run with no network at all:

```bash
OFFLINE_DEMO_MODE=true .venv/bin/python -m streamlit run app.py
```

Setting up the environment from scratch is described in the README (Python
3.11 or newer; `uv venv --python 3.12 .venv` then
`uv pip install --python .venv/bin/python -r requirements.txt`). No new
dependency was added in A5.

## Layout

A banner at the top repeats the three rules that apply to everything: the pilot
site is provisional, dry/typical/wet seasons are past seasons and not
forecasts, and no rotation is scored, ranked or recommended.

The **sidebar** holds the choices that change what is shown:

| Control | Effect |
| --- | --- |
| Rainy season | Long rains (March-May) or short rains (October-December). Every season chart, table and comparison card follows it |
| Past seasons to highlight | All, dry, typical or wet. Charts dim the other classes; comparison cards add a sentence for the chosen class |
| Farmer priorities | Choose one or more, in order. Brings the related results forward, marks them ★ and lists what is missing. No weights |
| Status | Pilot status, where the NASA data came from, offline mode, AI services (both disabled) |

The six tabs:

| Tab | What it shows |
| --- | --- |
| **Overview** | The pilot site and its provisional status, the NASA dataset (source, period, 54,786 daily values, completeness, where it was read from), headline facts about the record, the two rainy seasons in the monthly average, how to use the app |
| **Climate Explorer** | Season rainfall of every past season with dry and wet boundaries; the scenario explorer (table of seasons and one season day by day); spread of season rainfall; annual rainfall; season temperature statistics; classification method; limits; data quality and the raw record |
| **Rotation Comparison** | Your priorities (if chosen); *What changes between these strategies?*; one card per strategy; results side by side under environmental exposure, agronomic characteristics and soil compatibility; rotation considerations; scientific confidence; downloads |
| **Soil & Farm Inputs** | No soil (default), your own soil, or the illustrative profile; the soil actually used, with its stated source and verification; what is still missing and how to get it |
| **Scientific Evidence** | Key limitations; what CropShift does not estimate; NASA citation, request and fingerprint; the knowledge base; the evidence audit and all thirteen sources with links |
| **About & Methodology** | Development stage, method in brief, the indicator catalogue, build status, settings, AI assistance |

## Reading a result

Every result card shows its status, its confidence and one headline:

* **Supported**: verified facts and the NASA record; no conditions.
* **Conditional**: rests on context-dependent evidence; the main condition is
  shown under the headline, all conditions in *How to read this result*.
* **Unavailable**: the evidence or input does not exist; the reason is shown.
  An unavailable result is never treated as good or bad.

*How to read this result* opens the six-part explanation from the engine (what
it measures, what data it uses, what assumptions apply, what the result means,
what it does not prove, what would improve confidence), followed by the
conditions, what is missing, the evidence used with its citation and audit
status, and the reason for the confidence level.

## Soil

| Mode | What happens |
| --- | --- |
| No soil information (default) | Soil results are unavailable with the reason; everything else is calculated |
| Enter my soil information | A form for soil pH, soil water (texture class, or field capacity and wilting point, or available water capacity) and drainage, each with where it comes from. Empty fields stay empty. Press *Use this soil information*; invalid values are refused with the reason and not applied |
| Illustrative soil profile | pH 6.5, loam, well drained, invented for demonstration and labelled "not measured at Katumani" everywhere |

The comparison is recalculated by the A4 engine whenever the soil applied
changes. Nothing entered is written to disk. Switching soil mode discards
earlier entries.

## Downloads

On the Rotation Comparison tab: a Markdown summary, the full report as JSON,
and the comparison in the A1 `ComparisonResult` format. They are produced on
request in the browser session; nothing is stored by CropShift.

## Offline behaviour

With `OFFLINE_DEMO_MODE=true` the app reads the local cache, then the verified
NASA response bundled in `data/demo/`, and never contacts NASA. Without it, the
app uses a cached response if one is less than 30 days old (the default) and
requests NASA only otherwise. Changing a priority, a soil value or a season
selection never triggers a NASA request: the data, the knowledge base and the
scenarios are loaded once and cached.

## Demonstration in two minutes

1. Overview: the site, the provisional banner, 50 past seasons.
2. Sidebar: choose *Dry seasons*. Climate Explorer: the eight driest long-rains
   seasons, the representative season day by day.
3. Rotation Comparison: *What changes between these strategies?*, then the
   rainfall cards: "In the 8 dry long rains seasons: rainfall below the range in
   8" for maize, and *Unavailable* for pigeon pea, with the reason.
4. Soil & Farm Inputs: *Illustrative soil profile*. Back in the comparison, the
   soil cards now carry values, each labelled hypothetical.
5. Sidebar: priority *Water conservation*: the related results move forward
   and are starred; add *Market and economic considerations* to show an honest
   "Nothing is estimated".
6. Scientific Evidence: the limitations and *What CropShift does not estimate*.

The full twelve-step walkthrough and its results are in
`a5_demo_walkthrough.md`.

## Known issues

* The pilot site has not been approved by the participant.
* Each indicator card is repeated for maize in all three strategies, because
  maize is in all three; the tradeoff note says so.
* Results are long on a phone screen; the columns stack vertically.
* Wet-day counts in a grid-cell average are high for a semi-arid area; the
  scenario limits say so.
