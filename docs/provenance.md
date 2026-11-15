# Provenance record

A running record of what was built, when, with what help and from which
external resources. It exists so that the submission's "Use of Super
Intelligence (SI)" and "References" fields can be filled in accurately, and so
that the project's originality can be shown if asked.

## Project facts

| | |
| --- | --- |
| Project | CropShift RESILIENCE |
| Event | NASA Space Apps Challenge 2026, 14–15 November 2026 |
| Local Event | Singapore |
| Challenge | Field Shift: Adapting Farms with NASA Data |
| Team | Solo participant |
| Repository started | 14 November 2026, from an empty folder |

## Work log

Times are Singapore time. Add a row for every phase.

| Date | Phase | What was done |
| --- | --- | --- |
| 14 Nov 2026, morning | A1 | Audited the empty working folder. Reviewed the official challenge page, Resources tab, Judging & Awards Guide, Project Submission Guide and Participant FAQs. Probed the NASA POWER API. Created the repository structure, typed configuration, scientific data contracts, placeholder modules, a minimal Streamlit page, 137 automated tests and the documentation in `docs/`. Committed as `e26bfd0`. |
| 14 Nov 2026, late morning | A2 | Read the Participant Terms & Conditions, NASA's data policy and the NASA POWER referencing guide and methodology pages (`compliance.md`). Built the NASA data layer: client, verified cache, three-level validation, dataset provenance, data service with offline mode, monthly aggregation and a command line. Chose and documented the pilot site. Retrieved the pilot dataset live from NASA POWER and saved it as bundled demo data. Added a data preview to the Streamlit page. Test suite grew to 362 tests (361 routine, 1 live). |
| 14 Nov 2026, afternoon, to 15 Nov 2026, 01:00 | A3 | Read FAO Irrigation and Drainage Paper 56 (Tables 11, 12, 19, 22, 23, 24), FAO Training Manual 3 (Tables 6 and 14), six Feedipedia datasheets, two FAO Conservation Agriculture pages, the FAO GIEWS brief for Kenya, and the abstracts of two journal articles whose details were confirmed against Crossref. Built the evidence registry and the agronomic knowledge base from those readings, rewrote the pilot site description with citations, and added a knowledge summary to the app. Test suite grew to 633 tests (632 routine, 1 live). |
| 15 Nov 2026, 08:35 to 09:30 | A4 | Requested all thirteen sources again and re-read every passage A4 calculates with, both abstracts (Europe PMC) and both Crossref records; read FAO-56 Chapter 8 Equations 82 and 83, the current FAO GIEWS brief and the ETCCDI index definitions; checked the pilot coordinates with one OpenStreetMap Nominatim request. Wrote the evidence audit and gate, soil inputs, pilot configuration and season windows, the historical scenario engine, the comparison engine with farmer priorities, and the uncertainty and explanation layer. Test suite grew to 803 tests (802 routine, 1 live). |
| 15 Nov 2026, 10:05 to 10:35 | A5 | Built the Streamlit application: six tabs, seven charts from the NASA record, the scenario explorer, the side-by-side rotation comparison, the soil form, farmer priorities, evidence and limitations panels and downloads, using the A4 engine for every result. Checked it in a browser, found and fixed a hot-reload defect. Test suite grew to 867 tests (866 routine, 1 live). |
| 15 Nov 2026, 10:54 to 11:15 | A8 | Independent validation: reproduced the baseline; re-read the source passages behind the comparisons; recalculated season totals, temperatures, terciles and soil equations from the raw NASA file by a separate path; walked all twelve demonstration steps by hand in a browser; tested offline mode with a tampered cache, reload, restart and hot reload; checked secrets, privacy and the 46 installed packages against the OSV vulnerability database; re-read the official Project Submission Guide. Fixed wording that said more than its evidence, a citation display defect, a stale-cache defect and chart contrast. Test suite grew to 906 tests (905 routine, 1 live). |
| 15 Nov 2026, 14:40 to 15:20 | A9 | Committed the A8 fixes (`aa5efdf`). Wrote the claims register, rewrote the README for judges, re-read the Project Submission Guide, captured real screenshots of the running app with a headless browser, built a seven-slide demo deck (a private claude.ai Slides artifact, using those screenshots), drafted the submission text, audited licences, attribution, Git history and personal data, and tested installation from a fresh clone. Updated the app's development-stage text and phase table (A8 complete, A6 and A7 deferred). Nothing was published, deployed or submitted. |

## State of the folder before work began

The working folder `CropShift` was created on 14 November 2026 and was empty.
It was not a Git repository. No credentials, configuration or tests existed.
No OpenAI, Manus, NASA or Earthdata environment variables were set in the
shell.

## Earlier practice project: not used

A separate practice project named "FarmLab-Practice" exists elsewhere on the
participant's computer, with files dated 5 to 11 November 2026, before the
hackathon began.

* It was checked for by listing file and folder **names only**.
* **No file in it was opened, read, copied or adapted.**
* Nothing in this repository derives from it.

Both projects use Streamlit with `src/`, `tests/` and `docs/` folders, which is
a common layout and was specified independently in the A1 brief.

The official FAQ states: "Teams are not allowed to begin working on the
challenges prior to the hackathon." Keeping the practice project entirely out
of this repository is the cautious course. Whether practice work on a related
theme needs to be mentioned to the Local Lead is the participant's call.

## Use of AI tools

The 2026 official materials call these tools "Super Intelligence (SI)".

| Tool | Used for | Not used for |
| --- | --- | --- |
| Claude Code (Anthropic), an AI coding assistant | Writing the code, tests and documentation in this repository under the participant's direction; reading the official challenge, legal and NASA documentation pages; running the NASA POWER requests; in A9, capturing screenshots of the running app, laying out the seven-slide demo deck and drafting the submission text; placing the participant's AI-generated background image on the slides and watermarking it (see below) | Generating video or audio; generating any scientific data or results. Every environmental value in the project was returned by NASA's service and is stored unmodified. The screenshots are captures of the app, not generated images. |

How the work was directed: the participant supplied a written brief for the
phase, including the product concept, architecture, scope and acceptance
criteria. The assistant carried it out, and the participant reviews and
approves each phase before the next begins.

Marking of AI-assisted material, as the Project Submission Guide requires for
code ("descriptive text and metadata"):

* every Python module states it in its opening docstring;
* this file and `README.md` state it;
* the app's footer states it.

AI-generated images: one painting, used twice. The app's page background and
the demo deck's background (`docs/presentation/CropShift_RESILIENCE_demo.pdf`)
are a painting of a wheat field under a swirling night sky, in the style of
Vincent van Gogh. The participant created it, in a wide and a tall version,
with an AI image-generation tool and supplied it on 15 November 2026; the
assistant placed it in the app (`static/theme/`) and on the slides and added
the labels. The landscape is imaginary, not the pilot site, and the image
contains no people. As the Project Submission Guide requires, every slide
shows a visible watermark ("AI-generated image (SI) · imaginary landscape, not
the pilot site") and every app page shows a credit saying the background is an
AI-generated image. The app's brushstroke ornaments (gold underlines, painted
dividers, the brushed frame and a canvas-grain tile) are simple SVG strokes
drawn by `scripts/make_theme_artwork.py`, which was written with AI
assistance. The project contains no AI-generated video or audio. No NASA logos
or mission identifiers are used.

The participant should complete the SI field of the submission form in their
own words, and add any other AI tools they used outside this repository.

## External resources

To be copied into the "References" field. Update whenever something is added.

### NASA data and resources

| Resource | Use so far | Link |
| --- | --- | --- |
| NASA POWER Daily API (v2.10.3) | **The project's data source.** Six parameters for the pilot site, 2001 to 2025, retrieved on 14 Nov 2026 and bundled in `data/demo/`. A 91-day response recorded as a test fixture. | https://power.larc.nasa.gov/ |
| MERRA-2 reanalysis (NASA GMAO) | Supplies temperature, precipitation and humidity through NASA POWER. | https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/ |
| CERES SYN1deg (NASA Langley) | Supplies solar irradiance through NASA POWER. | https://ceres.larc.nasa.gov/ |
| NASA POWER documentation: Daily API, Referencing Guide, Methodology | Consulted for parameters, limits, citation wording and data sources. | https://power.larc.nasa.gov/docs/ |
| NASA Earth science Data and Information Guidance | Consulted to confirm the data may be retrieved, stored and shared. | https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-information-guidance |
| GPM IMERG precipitation | Confirmed available through NASA POWER in A1. **Not used** in the project so far. | https://gpm.nasa.gov/data |

NASA requests made so far, all to the NASA POWER Daily API with no account or
key: six availability probes in A1 (responses not kept); the pilot dataset; the
91-day test fixture; and the ten-day live smoke test, run once on 14 Nov and
once on 15 Nov 2026. The A4 engine uses the bundled pilot response and makes no
request of its own.

### Official Space Apps pages consulted

Listed with addresses in `requirements_matrix.md`. Short passages are quoted
there to record requirements accurately.

### Software

All open source, installed from the Python Package Index. Versions are those
installed on 14 Nov 2026.

| Package | Version | Purpose | Licence |
| --- | --- | --- | --- |
| Python | 3.12.13 | Language | PSF |
| Streamlit | 1.67.0 | Web interface | Apache 2.0 |
| pandas | 3.1.1 | Tabular data | BSD 3-Clause |
| NumPy | 2.5.4 | Numerical arrays | BSD 3-Clause |
| Plotly | 6.9.0 | Charts | MIT |
| Pydantic | 2.14.3 | Typed data contracts | MIT |
| pydantic-settings | 2.16.3 | Typed configuration | MIT |
| HTTPX | 0.28.1 | HTTP requests (from A2) | BSD 3-Clause |
| pytest | 9.2.0 | Tests | MIT |
| uv | 0.11.32 | Environment and package installation | Apache 2.0 / MIT |

Licences were read from the installed packages' own metadata on 14 Nov 2026.
All 46 installed packages, including indirect ones, are under permissive
open-source licences; the breakdown is in `compliance.md`.

### Code, text and images from other projects

None. No code, text or image was copied from another project.

### Scientific references

* NASA POWER project. "The data was obtained from National Aeronautics and
  Space Administration (NASA) Langley Research Center's Prediction Of Worldwide
  Energy Resources (POWER) project funded through the NASA Earth Science
  Division." Data reference: "The data was obtained from the POWER Project's
  Daily v2.10.3 version on 2026/11/14."
* Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research
  and Applications, Version 2 (MERRA-2). *Journal of Climate*, 30(14),
  5419–5454. https://doi.org/10.1175/JCLI-D-16-0758.1

The thirteen sources behind the agronomic knowledge base, with full citations
ready for the References field, are listed in
[`evidence_registry.md`](evidence_registry.md). In brief:

* Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop
  evapotranspiration.* FAO Irrigation and Drainage Paper 56.
* Brouwer, C., & Heibloem, M. (1986). *Irrigation Water Management: Irrigation
  Water Needs.* FAO Training manual no. 3.
* Six Feedipedia datasheets (INRAE, CIRAD, AFZ and FAO, 2015 to 2017): common
  bean, cowpea forage, maize green forage, mung bean, pigeon pea forage,
  sorghum forage.
* Rao, M. R., & Mathuva, M. N. (2000). Legumes for improving maize yields and
  income in semi-arid Kenya. *Agriculture, Ecosystems & Environment*, 78(2),
  123–137. https://doi.org/10.1016/S0167-8809(99)00125-5
* Franke, A. C., van den Brand, G. J., Vanlauwe, B., & Giller, K. E. (2018).
  Sustainable intensification through rotations with grain legumes in
  Sub-Saharan Africa: A review. *Agriculture, Ecosystems & Environment*, 261,
  172–185. https://doi.org/10.1016/j.agee.2017.09.029
* FAO Conservation Agriculture pages on species diversification and soil
  organic cover (undated).
* FAO GIEWS Country Brief: Kenya (reference date 4 May 2026).

The pilot site description in `src/pilot_sites.py` cites the last and the Rao
and Mathuva article.

Added in A4:

* Expert Team on Climate Change Detection and Indices (ETCCDI). *Climate
  Change Indices: Definitions of the 27 core indices.*
  https://etccdi.pacificclimate.org/list_27_indices.shtml (undated web page,
  accessed 15 November 2026). Defines the wet-day, dry-spell, heavy-rain and
  frost-day counts used by the scenario engine.
* OpenStreetMap Nominatim reverse geocoding, one request on 15 November 2026,
  to confirm that the pilot coordinates lie in Machakos County. Data ©
  OpenStreetMap contributors, available under the Open Database Licence.
  https://nominatim.openstreetmap.org/
* FAO-56, Chapter 8, Equations 82 and 83 (total and readily available soil
  water), already registered as `fao-56`.
* Europe PMC (https://europepmc.org/) and Crossref (https://www.crossref.org/)
  were used to re-check the two journal articles; nothing was taken from them
  beyond the abstracts and citation details.

The audit outcome for every source is in
[`scientific_evidence_audit.md`](scientific_evidence_audit.md).

## Data in the repository

| File | What it is | Source |
| --- | --- | --- |
| `data/demo/4f87119a…6956.json` | The pilot dataset: NASA's original response, unmodified, with its request and retrieval time. 9,131 days, six parameters. | NASA POWER Daily API v2.10.3, retrieved 14 Nov 2026 02:57 UTC |
| `tests/fixtures/power_daily_katumani_2020q1.json` | A 91-day NASA response used by the tests, unmodified. | Same service, same time |

Both are real NASA responses. Each carries a SHA-256 fingerprint that the code
re-checks whenever the file is read. Nothing in the repository is synthetic
environmental data presented as real. Where tests need damaged or incomplete
data, they alter a copy in memory and say so; those values never leave the test.

The local cache in `data/cache/` is not part of the repository.

### Agronomic knowledge (added in A3)

| Files | What they are | Source |
| --- | --- | --- |
| `data/knowledge/*.json` | Crop characteristics, soil-water reference values, rotation relationships and constraints, each value with its source, locator and confidence | Read from the thirteen registered sources on 14 Nov 2026 |

Every value was read from the cited page or table. None comes from the AI
assistant's own knowledge, and none was estimated to fill a gap; gaps are
recorded as "not established". Where a source contained an error (three
inconsistent rows in FAO-56 Table 11, one scanning error in Table 19), the
value is kept as printed and the problem is declared.

No measured soil data and no results are stored.

### Evidence audit (added in A4)

| File | What it is | Source |
| --- | --- | --- |
| `data/knowledge/evidence_audit.json` | The 15 Nov 2026 re-check of every source, claim-level exceptions, the ETCCDI method source and the audit findings | Re-reading the sources listed above |

The demonstration soil profile in `src/soil_inputs.py` is invented, labelled
hypothetical everywhere it appears, and describes no real field.
