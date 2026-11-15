# Implementation plan

## The clock

The hackathon runs **14–15 November 2026**. Submission closes on **Sunday
15 November at 11:59 p.m. Singapore time**. Phase A1 finished on Saturday
morning, leaving about a day and a half for A2 to A9.

**Status at 15:10 on Sunday 15 November:** A1 to A5 and A8 are complete; A6 and A7 are deferred until after submission (see `a8_validation_report.md`, section N). A9 preparation is done: claims register, README, screenshots, a seven-slide deck and the submission text. Publishing, the licence and the final submission wait for the participant's approval (see `a9_release_report.md`). About 8.8 hours remain before the 23:59 deadline.

The time boxes below are a proposal, not a commitment. The rule that matters:
**a submitted, honest MVP beats an unfinished ambitious one.** If a phase
overruns, cut scope inside it rather than borrowing time from A8 and A9.

| Phase | Proposed window (Singapore time) | Can it be cut? |
| --- | --- | --- |
| A1 Foundation | Sat morning | Done |
| A2 NASA data ingestion | Sat late morning | Done |
| A3 Agronomic knowledge base | Sat afternoon to Sun 01:00 | Done |
| A4 Scenario and comparison engine | Sun morning | Done |
| A5 Streamlit interface | Sun morning | Done |
| A6 OpenAI explanations | Only if A5 finishes early | **Yes, optional; recommend skipping** |
| A7 Manus reports | Only if A5 finishes early | **Yes, optional; recommend skipping** |
| A8 Final validation | Sun late morning | Done |
| A9 Demonstration and submission | Sun early evening (revised) | No |
| Buffer | Sun evening | Keep at least three hours before the deadline |

Each phase starts only on the participant's explicit approval.

## Phases A1 to A9

### A1. Repository, requirements, architecture and foundation — complete

Delivered: repository audit, official requirements review, requirements
matrix, provisional MVP specification, repository structure, typed
configuration, scientific data contracts, NASA data source evaluation, minimal
Streamlit page, baseline tests, documentation.

### A2. NASA data ingestion, validation, provenance and caching — complete

Delivered: compliance review; NASA POWER client with bounded retries; verified
file cache; three-level validation; typed observations; dataset provenance with
NASA's requested citations; offline mode with bundled real data; monthly totals
and means; a command line; a data preview in the app; one documented pilot site
verified with a live retrieval; 225 new tests.

Changed from the A1 plan:

* **GPM IMERG was not added.** The A2 brief asked for one source first. It is
  ready to add and needs a decision.
* **Seasons were not ranked into dry, typical and wet.** That needs a cited
  definition of the growing seasons, which is A3's work, so it moves to A4
  with the scenario engine.
* **One pilot site, not two or three.** The brief asked for one.

### A3. Evidence-based agronomic knowledge base — complete

Delivered: an evidence registry of thirteen sources, each with how it was read
and its limits; six crop profiles with 64 sourced requirements, 57 sourced
statements and 30 recorded gaps; growth-stage examples; soil-water reference
values for nine texture classes; fifteen rotation relationships; fourteen
stored constraints; four cropping systems from the Machakos experiment; ten
farmer-priority definitions; eleven interface contracts for A4; the pilot site
description rewritten with citations; 271 new tests.

Changed from the plan below:

* **Rotations were not defined with calendars.** The one source that names
  rotations for the area gives no seasons or cycle lengths, so the systems are
  recorded with those details listed as missing. A4 must obtain them.
* **Pilot regions were not confirmed.** The site still awaits approval.
* **The growing seasons** are described from FAO (long rains March to May,
  short rains October to December), but a rule for when a season starts and
  ends in a given year is left to A4.

Original plan:

* Cite or remove the pilot site's farming background (`compliance.md`, C6).
* Define the pilot site's growing seasons from a cited source. The NASA record
  shows two wetter periods centred on April and November.
* Confirm the pilot regions and their crops.
* Build cited crop profiles; record every source.
* Define the current and alternative rotations for each region, with their
  calendars.
* Fix the reference source for soil water properties by texture class.

Done when: every parameter in the knowledge base has a citation, and missing
parameters are listed as gaps rather than filled.

### A4. Scenario and comparison engine — complete

Delivered: an evidence audit of all thirteen sources with a claim-to-evidence
matrix and an evidence gate; soil inputs with provenance for the three soil
mappings; a provisional pilot configuration with cited season windows; a
historical scenario engine (25 seasons per window, dry, typical and wet
terciles); a comparison engine with eleven indicators, fourteen evaluated
constraints, tradeoffs and farmer priorities without weights; uncertainty
statements and six-part explanations for every indicator; 170 new tests. Details
in `a4_validation_report.md`.

Changed from the plan below, as the A4 brief directed:

* **No season onset and end rule.** The cited FAO windows are used as fixed
  analysis windows; sowing dates stay unknown, and every result says so.
* **No wind speed, IMERG or reference evapotranspiration.** Deferred by the
  brief; the four mappings that need them stay unavailable.
* **The pilot site is used provisionally**, not approved.

Original plan:

* Confirm the pilot site, and the rotations to compare, with the participant.
  The knowledge base offers continuous maize, maize rotated with cowpea and
  maize rotated with pigeon pea as documented systems; pigeon pea has no
  water-use data.
* Adopt and cite a rule for the start and end of a rainy season.
* Rank past seasons into dry, typical and wet from the validated NASA record,
  using the season definitions from A3.
* Decide whether to add wind speed (needed for the standard reference
  evapotranspiration method) and GPM IMERG rainfall.
* Define indicators that the inputs can support and declare them in the
  variable registry.
* Calculate indicators for each rotation under each historical scenario.
* Produce an uncertainty statement for every result.
* Assemble the comparison with tradeoffs against the farmer's priorities and
  the five-part explanation for each rotation.

Done when: results are reproducible, every indicator documents its method and
limits, and tests cover the calculations with hand-checked cases.

### A5. Complete Streamlit interface — complete

Delivered: six-tab application (Overview, Climate Explorer, Rotation
Comparison, Soil & Farm Inputs, Scientific Evidence, About & Methodology);
seven charts from real NASA data; scenario explorer; side-by-side comparison of
the three strategies with every A4 indicator, constraint and tradeoff; soil
form with validation and provenance; farmer priorities without weights;
evidence and limitations panels; downloads; offline operation; 64 new tests.
SQLite persistence was deferred. Details in `a5_validation_report.md`.

Original plan:

* Build the ten-step user journey from `mvp_specification.md`.
* Accessible charts, a sources and assumptions screen, a glossary.
* Export of the comparison summary; optional saving in SQLite.

Done when: a first-time user can complete a comparison without help, online
and offline.

### A6. Optional OpenAI explanations

Plain-language restatement of a finished comparison through the OpenAI
Responses API. Off by default, clearly labelled, never an input to any
calculation. Requires the participant's key and approval because it is a paid
service.

### A7. Optional Manus research reports

Asynchronous background reports through the Manus API. Off by default, clearly
labelled, never an input to any calculation. Requires the participant's key
and approval. See unresolved item U3 in `requirements_matrix.md` first.

### A8. Final validation

* Full test run; a manual walk-through of every acceptance criterion.
* Sensitivity checks listed in `scientific_assumptions.md`.
* Security review: no secrets in the repository or its history.
* Check every on-screen number against its source.
* Check every item in section A of `requirements_matrix.md`.

### A9. Demonstration and submission

* A demo of at most 7 slides, or a video of at most 30 seconds.
* Text for every field of the submission form, including the AI disclosure,
  the NASA data used and the full reference list.
* Make the project publicly accessible (needs the participant's approval).
* Submit with time to spare, then verify the public links in a private
  browser window.

## Future migration stages M1 to M9

**Provisional outline.** The definitions of M1 to M9 were not supplied to
phase A1. The outline below is a reasonable reading of "migration to full
automation" and should be replaced with the agreed definitions when available.
None of it is implemented, and none of it is planned for the hackathon.

| Stage | Outline |
| --- | --- |
| M1 | Expose the engine through a small HTTP interface so workflows can call it |
| M2 | Scheduled refresh of NASA data and cache |
| M3 | Automated data-quality monitoring and alerts |
| M4 | Workflow orchestration with n8n or Zapier around comparison requests |
| M5 | Automated delivery of comparison summaries (for example by email or messaging) |
| M6 | AI explanation as a guarded workflow step |
| M7 | Asynchronous research reports as a workflow step |
| M8 | Multi-user storage and access control |
| M9 | Deployment, monitoring and operations |

The architectural seams that make this migration cheap are described in
`architecture.md`.

## Risks

| Risk | Kind | Likelihood | Response |
| --- | --- | --- | --- |
| Nine phases in under two days, solo | Time | High | Time boxes above; A6 and A7 are optional; cut scope inside phases |
| Crop evidence takes longer to find and cite than expected | Scientific | High | Fewer crops and regions; report gaps honestly |
| Indicators overstate what the inputs support | Scientific | Medium | Keep indicators simple and documented; uncertainty on every result |
| NASA POWER is slow or unavailable during the demo | Technical | Medium | Offline demo mode with bundled real responses |
| IMERG and MERRA-2 disagree on which seasons were dry or wet | Scientific | Medium | Show the disagreement; lower confidence; drop a region if labels are not robust |
| No public link at submission | Eligibility | Medium | Decide the publishing route early on Sunday |
| Earlier practice work mistaken for prior challenge work | Eligibility | Low | Nothing was copied; see `provenance.md` |
| Optional services introduce cost or an eligibility question | Eligibility | Low | Off by default; approval required; check U3 first |
| Secrets committed by accident | Security | Low | `.env` is ignored by Git; tests check this; review in A8 |
