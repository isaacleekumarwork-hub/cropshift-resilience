# Implementation plan

## The clock

The hackathon runs **14–15 November 2026**. Submission closes on **Sunday
15 November at 11:59 p.m. Singapore time**. Phase A1 finished on Saturday
morning, leaving about a day and a half for A2 to A9.

The time boxes below are a proposal, not a commitment. The rule that matters:
**a submitted, honest MVP beats an unfinished ambitious one.** If a phase
overruns, cut scope inside it rather than borrowing time from A8 and A9.

| Phase | Proposed window (Singapore time) | Can it be cut? |
| --- | --- | --- |
| A1 Foundation | Sat morning | Done |
| A2 NASA data ingestion | Sat late morning to early afternoon | No |
| A3 Agronomic knowledge base | Sat afternoon | No, but fewer crops and regions is acceptable |
| A4 Scenario and comparison engine | Sat evening | No, but fewer indicators is acceptable |
| A5 Streamlit interface | Sat night to Sun late morning | No |
| A6 OpenAI explanations | Sun midday, one hour at most | **Yes, optional** |
| A7 Manus reports | Sun midday, one hour at most | **Yes, optional** |
| A8 Final validation | Sun early afternoon | No |
| A9 Demonstration and submission | Sun mid-afternoon to early evening | No |
| Buffer | Sun evening | Keep at least three hours before the deadline |

Each phase starts only on the participant's explicit approval.

## Phases A1 to A9

### A1. Repository, requirements, architecture and foundation — complete

Delivered: repository audit, official requirements review, requirements
matrix, provisional MVP specification, repository structure, typed
configuration, scientific data contracts, NASA data source evaluation, minimal
Streamlit page, baseline tests, documentation.

### A2. NASA data ingestion

* Retrieve daily point data from the NASA POWER API in UTC for the MVP
  variables, including GPM IMERG rainfall.
* Cache raw responses; add offline demo mode with bundled real responses for
  the pilot regions.
* Convert fill values to explicit gaps; validate units and plausibility;
  attach provenance to every value.
* Summarise by growing season and rank past seasons to define dry, typical and
  wet historical scenarios.
* Resolve the open items in `data_sources.md`.

Done when: real NASA data for each pilot region loads live and offline, gaps
are explicit, and tests cover parsing, gap handling and season ranking using
saved responses.

### A3. Agronomic knowledge base

* Confirm the pilot regions and their crops.
* Build cited crop profiles; record every source.
* Define the current and alternative rotations for each region, with their
  calendars.
* Fix the reference source for soil water properties by texture class.

Done when: every parameter in the knowledge base has a citation, and missing
parameters are listed as gaps rather than filled.

### A4. Scenario and comparison engine

* Define indicators that the inputs can support and declare them in the
  variable registry.
* Calculate indicators for each rotation under each historical scenario.
* Produce an uncertainty statement for every result.
* Assemble the comparison with tradeoffs against the farmer's priorities and
  the five-part explanation for each rotation.

Done when: results are reproducible, every indicator documents its method and
limits, and tests cover the calculations with hand-checked cases.

### A5. Complete Streamlit interface

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
