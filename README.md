# CropShift RESILIENCE

A crop-rotation decision-support tool built on NASA Earth data, for the
**NASA Space Apps Challenge 2026** challenge
[Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/).

> **Status: phase A5 of A9. The application works.** It lets a farmer explore
> 25 years of NASA climate data for one provisional pilot site and compare three
> crop rotations across 50 real dry, typical and wet past seasons, with their
> own soil information, cited crop evidence and their priorities. Results are
> shown side by side with their uncertainty and a six-part explanation each. It
> never scores, ranks or recommends a rotation, and it works offline.

## Mission

Farmers face shifting temperatures, less predictable rain and declining soil
health, and choosing a rotation that protects the field is hard. CropShift
RESILIENCE is being built to let a farmer compare their current rotation with
alternatives across **dry, typical and wet seasons from the historical
record**, using NASA Earth data, local soil information, cited crop
characteristics and their own priorities.

It aims to show tradeoffs and uncertainty honestly. It does not predict yields,
prescribe inputs or forecast weather, and it supports rather than replaces
farmer judgment and local agricultural expertise.

## What exists today

| Built | Not built yet |
| --- | --- |
| Typed, validated configuration with AI services off by default (A1) | Saving comparisons in a database (deferred: downloads instead) |
| Scientific data contracts with units, explicit gaps and provenance (A1) | Optional AI explanations and reports (A6, A7) |
| **NASA POWER client** with timeouts and bounded retries (A2) | Reference evapotranspiration and a soil water balance (deferred) |
| **Verified local cache** and **offline mode** with bundled real NASA data (A2) | |
| **Three-level validation**, a quality report and a provenance record for every dataset (A2) | |
| **Monthly totals and means** and a data preview in the app (A2) | |
| **Agronomic knowledge base**: six crops, thirteen sources, 205 cited claims (A3) | |
| **Evidence audit** of every source and an **evidence gate** before every calculation (A4) | |
| **Soil inputs** with provenance for pH and root-zone water (A4) | |
| **Historical scenarios**: 25 long-rains and 25 short-rains seasons ranked dry, typical and wet (A4) | |
| **Comparison engine**: 11 indicators, 14 constraints, tradeoffs, farmer priorities without weights (A4) | |
| **Interactive application**: climate explorer, rotation comparison, soil inputs, priorities, evidence, downloads (A5) | |
| 867 automated tests | |

### The comparison engine

Three strategies, all grown in a cropping-systems experiment at Machakos
(1989-1996): continuous maize, maize rotated with cowpea, and maize rotated with
pigeon pea. For each, the engine reports how past season rainfall compared with
the crop's indicative water use, how often temperatures fell inside documented
ranges, frost days, whether the growing period fits the rainy season, soil pH
and root-zone water when soil information is supplied, and plant-family
diversity. Every indicator says what it used, what it assumed, what it means and
what it does not establish. Where evidence is missing, as for the water needs of
cowpea and pigeon pea, the indicator is marked unavailable, never estimated.
It runs offline in about a second:

```python
from src.comparison_engine import run_pilot_comparison
report = run_pilot_comparison()
```

Details: [docs/rotation_comparison_methodology.md](docs/rotation_comparison_methodology.md).

### The knowledge base

Six crops in two families: maize and sorghum (Poaceae); common bean, cowpea,
pigeon pea and mung bean (Fabaceae). Every value cites the table or passage it
came from and carries a confidence level. Where the sources read say nothing,
the gap is recorded as "not established" and never filled. Main sources: two
FAO irrigation handbooks, six Feedipedia datasheets, a seven-year cropping
experiment at Machakos, and a review of legume rotations across sub-Saharan
Africa. It is **provisional** because the pilot site has not been approved, and
it makes no claim that any crop suits that site. Details in
[docs/agronomic_knowledge.md](docs/agronomic_knowledge.md).

### The pilot dataset

25 years of daily NASA data (2001 to 2025) for the Katumani area of Machakos
County, Kenya: temperature, rainfall, sunshine and humidity, 100 % complete,
retrieved from NASA on 14 November 2026 and bundled with the project. The
values are averages over NASA grid cells tens of kilometres wide. They are
**not measurements from an individual farm**.

## Quick start

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

With [uv](https://docs.astral.sh/uv/) instead:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

To reproduce the exact tested environment (46 packages, versions recorded on
15 November 2026), install from the lock file instead:

```bash
uv pip install --python .venv/bin/python -r requirements-lock.txt
```

Run these from the repository root, so that Python finds the `src` package.
The app opens at http://localhost:8501. On first start it requests the pilot
dataset from NASA (about a second) and caches it. Without a connection it falls
back to the bundled copy and says so.

To run with no network at all:

```bash
OFFLINE_DEMO_MODE=true .venv/bin/python -m streamlit run app.py
```

## Using the app

Six tabs: **Overview**, **Climate Explorer** (every past rainy season, dry,
typical and wet, day by day), **Rotation Comparison** (three rotations side by
side, with downloads), **Soil & Farm Inputs**, **Scientific Evidence** and
**About & Methodology**. The sidebar chooses the rainy season, the class of past
seasons to highlight, and the farmer's priorities. A two-minute demonstration
script and every control are described in
[docs/a5_application_guide.md](docs/a5_application_guide.md).

## Retrieving NASA data from the command line

The pilot dataset:

```bash
python -m src.data_service pilot
```

Any point and historical date range:

```bash
python -m src.data_service fetch --lat -1.58 --lon 37.24 --start 2020-01-01 --end 2020-12-31
```

Each prints where the data came from, the exact request, and the completeness
of every variable. Options, Python examples, the data dictionary, the quality
rules and troubleshooting are in [docs/data_layer.md](docs/data_layer.md).

## Configuration

Every setting is optional; the app starts with safe defaults and no `.env`
file. To change a setting, copy `.env.example` to `.env` and edit the copy.
The real `.env` is ignored by Git and must never be committed.

| Setting | Default | Meaning |
| --- | --- | --- |
| `OFFLINE_DEMO_MODE` | `false` | Use stored NASA data only; make no network requests |
| `ENABLE_OPENAI` | `false` | Allow optional OpenAI explanations (A6) |
| `ENABLE_MANUS` | `false` | Allow optional Manus reports (A7) |
| `NASA_POWER_BASE_URL` | NASA POWER daily point endpoint | Must be `https` |
| `NASA_REQUEST_TIMEOUT` | `30` | Seconds to wait for a NASA response |
| `NASA_MAX_RETRIES` | `3` | Extra attempts after a rate limit, timeout or temporary server error |
| `NASA_CACHE_DIRECTORY` | `data/cache` | Cache folder for NASA responses |
| `NASA_CACHE_TTL_HOURS` | `720` | Hours before a cached response is requested again |
| `NASA_DEMO_DIRECTORY` | `data/demo` | Bundled real NASA responses for offline use |
| `NASA_MIN_COMPLETENESS_PERCENT` | `90` | Minimum completeness for a dataset to be accepted |
| `DATABASE_PATH` | `data/cropshift.db` | SQLite file for saved comparisons (A5) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OPENAI_API_KEY`, `MANUS_API_KEY` | empty | Future credentials for paid services |

An AI service is active only when its switch is on and its key is present.
The scientific calculations never depend on either. NASA POWER needs no
account or key.

## Tests

```bash
python -m pytest
```

866 tests run without any network access: HTTP is simulated, and a guard makes
any real request fail the test. They cover configuration, every data contract,
request validation, retries and rate limits, malformed responses, the cache
(keys, corruption, expiry, atomic writes), missing and invalid values, units,
completeness, provenance, offline behaviour, monthly aggregation, the knowledge
base (every value against its source transcription, unsupported claims,
evidence rules, constraints, versioning, ordering), the evidence gate (every
route by which an unsupported value could enter a calculation), soil inputs,
season windows, dry/typical/wet classification on the real record, every
comparison indicator, priorities without weights, the absence of any score or
fabricated outcome, the app's navigation, charts, soil form, priorities and twelve-step demonstration journey, and that no screen overclaims.

One further test contacts the real NASA service and is skipped unless asked
for:

```bash
python -m pytest tests/test_live_power.py --run-live
```

It makes a single small request for ten days in 2020 and compares the answer
with a response recorded earlier.

## Repository layout

```
app.py                  Streamlit entry point
requirements.txt        Dependencies
.env.example            Documented settings (no secrets)
src/
  config.py             Typed settings                          (working)
  models.py             Scientific data contracts               (working)
  nasa_client.py        NASA POWER requests, retries            (working, A2)
  nasa_cache.py         Verified local cache; bundled data      (working, A2)
  pilot_sites.py        The documented pilot site               (working, A2)
  data_validation.py    Validation, observations, provenance    (working, A2)
  data_processing.py    Tables, monthly totals and means        (working, A2)
  data_service.py       Entry point and command line            (working, A2)
  crop_knowledge.py     Knowledge base loader and validation    (working, A3)
  evidence_audit.py     Evidence audit and evidence gate        (working, A4)
  soil_inputs.py        Soil inputs, provenance, FAO-56 Eq. 82-83 (working, A4)
  season_config.py      Pilot configuration, windows, strategies (working, A4)
  scenario_engine.py    Dry, typical and wet past seasons       (working, A4)
  comparison_engine.py  Indicators, constraints, priorities     (working, A4)
  uncertainty.py        Confidence and explanations             (working, A4)
  visualizations.py     Charts                                  (placeholder, A5)
  ui_state.py           Session state                           (placeholder, A5)
  persistence.py        SQLite storage                          (placeholder, A5)
  report_service.py     Comparison export                       (placeholder, A5)
  openai_service.py     Optional explanations                   (placeholder, A6)
  manus_service.py      Optional research reports               (placeholder, A7)
data/
  knowledge/            Cited crop, soil and rotation knowledge (JSON)
  demo/                 Bundled real NASA response for the pilot site
  cache/                Local cache (created on use; not in Git)
tests/                  Automated tests and a recorded NASA response
docs/                   Project documentation
```

## Documentation

| Document | Contents |
| --- | --- |
| [docs/a8_validation_report.md](docs/a8_validation_report.md) | Independent validation: science, NASA data, browser walkthrough, security, usability, submission readiness |
| [docs/a5_application_guide.md](docs/a5_application_guide.md) | Launching and using the app; demonstration script; known issues |
| [docs/a5_validation_report.md](docs/a5_validation_report.md) | A5 test results, walkthrough, acceptance checklist and A6 readiness |
| [docs/a5_ui_architecture.md](docs/a5_ui_architecture.md) | Interface files, caching, state and failure handling |
| [docs/a5_scientific_integrity.md](docs/a5_scientific_integrity.md) | How the interface avoids overclaiming, and the tests that enforce it |
| [docs/a5_demo_walkthrough.md](docs/a5_demo_walkthrough.md) | The twelve-step user journey and its results |
| [docs/a4_validation_report.md](docs/a4_validation_report.md) | A4 test results, acceptance checklist and the interfaces A5 will use |
| [docs/scientific_evidence_audit.md](docs/scientific_evidence_audit.md) | Audit of all thirteen sources and the claim-to-evidence matrix |
| [docs/rotation_comparison_methodology.md](docs/rotation_comparison_methodology.md) | Indicators, constraints, priorities, tradeoffs and the pilot results |
| [docs/historical_scenarios.md](docs/historical_scenarios.md) | Dry, typical and wet past seasons, with every season listed |
| [docs/soil_input_mapping.md](docs/soil_input_mapping.md) | Soil inputs, their validation and provenance |
| [docs/pilot_configuration.md](docs/pilot_configuration.md) | The provisional pilot site, season windows and strategies |
| [docs/uncertainty.md](docs/uncertainty.md) | Confidence rule, uncertainty categories and explanations |
| [docs/agronomic_knowledge.md](docs/agronomic_knowledge.md) | Crops, requirements, soil, rotation relationships, constraints, priorities, interfaces for A4 |
| [docs/evidence_registry.md](docs/evidence_registry.md) | Every agronomic source, how it was checked, and how much rests on it |
| [docs/data_layer.md](docs/data_layer.md) | Using the NASA data layer: commands, Python examples, data dictionary, quality rules, cache, offline mode, troubleshooting |
| [docs/data_sources.md](docs/data_sources.md) | What was verified about NASA POWER, the live retrieval, and the candidate evaluation |
| [docs/compliance.md](docs/compliance.md) | Terms & Conditions, licences, attribution and items needing a decision |
| [docs/scientific_assumptions.md](docs/scientific_assumptions.md) | Assumptions, limits of the data, and open scientific questions |
| [docs/architecture.md](docs/architecture.md) | Layers, data flow, module responsibilities, data contracts and decisions |
| [docs/requirements_matrix.md](docs/requirements_matrix.md) | Official requirements, recommendations and resources, kept apart from our own choices |
| [docs/mvp_specification.md](docs/mvp_specification.md) | The minimum viable product and its acceptance criteria (provisional) |
| [docs/implementation_plan.md](docs/implementation_plan.md) | Phases A1 to A9, future stages M1 to M9, schedule and risks |
| [docs/provenance.md](docs/provenance.md) | Work log, AI assistance, references and originality record |

## Known limitations

* **Descriptions, not models.** Indicators compare rainfall, temperature and
  soil with documented crop ranges. There is no water balance, no crop model and
  no reference evapotranspiration, so nothing predicts yield or irrigation need.
* **Missing crop evidence.** No verified water need exists for cowpea or pigeon
  pea, so their water indicators are unavailable.
* **Sowing dates unknown.** Fixed calendar windows stand in for the rainy
  seasons, and the study does not say which crop was grown in which season.
* **Provisional knowledge.** Climate and soil ranges come largely from
  secondary datasheets; FAO EcoCrop was not accessible. Several important
  values are missing for cowpea, mung bean and pigeon pea. No agronomist has
  reviewed it.
* **Thin local evidence.** Regional evidence is one experiment at Machakos,
  1989 to 1996, covering three of the six crops.
* **Area, not field.** The NASA weather data describes grid cells roughly
  55 km by 70 km; the solar data about 110 km.
* **Modelled, not measured.** Temperature, rainfall and humidity come from a
  reanalysis: a weather model constrained by observations. They have not been
  compared with any local station.
* **History, not forecast.** The record shows what happened from 2001 to 2025,
  not what will happen.
* **One site, one rainfall source.** One pilot site is supported, with rainfall
  from a single NASA product.
* **Passing validation is not proof of accuracy.** The checks confirm the data
  is well formed, physically possible and complete.
* The pilot site has not been approved.
* No open-source licence has been chosen yet (see `docs/compliance.md`).
* The interface is in English only.

## AI assistance

This project was built during the hackathon with an AI coding assistant
(Claude Code, by Anthropic) working under the participant's direction. The
code, tests and documentation were drafted with it. No AI-generated images,
video, audio or scientific data are included: every environmental value was
returned by NASA's service and is stored unmodified, and every agronomic value
was read from the published source it cites. Details are in
[docs/provenance.md](docs/provenance.md).

## Data and acknowledgements

The data was obtained from National Aeronautics and Space Administration
(NASA) Langley Research Center's Prediction Of Worldwide Energy Resources
(POWER) project funded through the NASA Earth Science Division. The data was
obtained from the POWER Project's Daily v2.10.3 version on 2026/11/14.

Meteorological values originate from NASA's MERRA-2 reanalysis and solar values
from NASA's CERES SYN1deg product, as distributed by NASA POWER. Full citations
are in [docs/data_sources.md](docs/data_sources.md).

This is an independent hackathon project. It is not endorsed by NASA.
