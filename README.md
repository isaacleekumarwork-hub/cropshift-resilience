# CropShift RESILIENCE

A crop-rotation decision-support tool built on NASA Earth data, for the
**NASA Space Apps Challenge 2026** challenge
[Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/).

> **Status: phase A1 of A9, foundation only.** No scientific analysis is
> implemented yet. The app shows no NASA observations and no results.

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

| Built in A1 | Not built yet |
| --- | --- |
| Typed, validated configuration with AI services off by default | NASA data retrieval (A2) |
| Scientific data contracts with units, explicit gaps and provenance | Crop knowledge base (A3) |
| A minimal Streamlit page that reports the build status | Scenario and comparison engine (A4) |
| 137 automated tests | The full interface and export (A5) |
| Requirements, architecture, data-source and assumption documents | Optional AI explanations and reports (A6, A7) |

## Quick start

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

With [uv](https://docs.astral.sh/uv/) instead:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/streamlit run app.py
```

The app opens at http://localhost:8501.

## Configuration

Every setting is optional; the app starts with safe defaults and no `.env`
file. To change a setting, copy `.env.example` to `.env` and edit the copy.
The real `.env` is ignored by Git and must never be committed.

| Setting | Default | Meaning |
| --- | --- | --- |
| `OFFLINE_DEMO_MODE` | `false` | Use bundled or cached data only |
| `ENABLE_OPENAI` | `false` | Allow optional OpenAI explanations (A6) |
| `ENABLE_MANUS` | `false` | Allow optional Manus reports (A7) |
| `NASA_REQUEST_TIMEOUT` | `30` | Seconds to wait for a NASA response |
| `NASA_CACHE_DIRECTORY` | `data/cache` | Cache folder for NASA responses |
| `DATABASE_PATH` | `data/cropshift.db` | SQLite file for saved comparisons |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OPENAI_API_KEY`, `MANUS_API_KEY` | empty | Future credentials for paid services |

An AI service is active only when its switch is on and its key is present.
The scientific calculations never depend on either.

## Tests

```bash
python -m pytest
```

The tests cover configuration defaults and validation, disabled AI services,
every data contract (required fields, invalid values, gaps, units), module
imports, and that the app starts and reports its status truthfully. They need
no network access.

## Repository layout

```
app.py                  Streamlit entry point
requirements.txt        Dependencies
.env.example            Documented settings (no secrets)
src/
  config.py             Typed settings                        (working)
  models.py             Scientific data contracts             (working)
  nasa_client.py        NASA data retrieval                   (placeholder, A2)
  data_validation.py    Gap and quality handling              (placeholder, A2)
  data_processing.py    Seasonal summaries and ranking        (placeholder, A2)
  crop_knowledge.py     Cited crop profiles and rotations     (placeholder, A3)
  scenario_engine.py    Rotation-by-scenario indicators       (placeholder, A4)
  comparison_engine.py  Tradeoffs against priorities          (placeholder, A4)
  uncertainty.py        Confidence and limitations            (placeholder, A4)
  visualizations.py     Charts                                (placeholder, A5)
  ui_state.py           Session state                         (placeholder, A5)
  persistence.py        SQLite storage                        (placeholder, A5)
  report_service.py     Comparison export                     (placeholder, A5)
  openai_service.py     Optional explanations                 (placeholder, A6)
  manus_service.py      Optional research reports             (placeholder, A7)
tests/                  Automated tests
docs/                   Project documentation
```

## Documentation

| Document | Contents |
| --- | --- |
| [docs/requirements_matrix.md](docs/requirements_matrix.md) | Official requirements, recommendations and resources, kept apart from our own choices |
| [docs/mvp_specification.md](docs/mvp_specification.md) | The minimum viable product and its acceptance criteria (provisional) |
| [docs/architecture.md](docs/architecture.md) | Layers, data flow, module responsibilities and data contracts |
| [docs/data_sources.md](docs/data_sources.md) | NASA data source evaluation and recommendation |
| [docs/scientific_assumptions.md](docs/scientific_assumptions.md) | Assumptions, limits and open scientific questions |
| [docs/implementation_plan.md](docs/implementation_plan.md) | Phases A1 to A9, future stages M1 to M9, schedule and risks |
| [docs/provenance.md](docs/provenance.md) | Work log, AI assistance, references and originality record |

## Known limitations

* Nothing scientific works yet. This is a foundation.
* The pilot regions, crops and indicators are not decided.
* The planned NASA weather data describes an area of roughly 50 km, not a
  single field.
* Nine of the registered variable definitions are provisional until later
  phases confirm them.
* The interface is in English only.

## AI assistance

This project was built during the hackathon with an AI coding assistant
(Claude Code, by Anthropic) working under the participant's direction. The
code, tests and documentation were drafted with it. No AI-generated images,
video, audio or scientific data are included. Details are in
[docs/provenance.md](docs/provenance.md).

## Data and acknowledgements

Planned data sources are NASA POWER (NASA Langley Research Center) and GPM
IMERG (NASA Goddard Space Flight Center). Citations are in
[docs/data_sources.md](docs/data_sources.md). This project is not endorsed by
NASA.
