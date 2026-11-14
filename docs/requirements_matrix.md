# Requirements matrix

Reviewed on 14 November 2026 (Singapore time), the first day of the hackathon.

This document separates what NASA Space Apps **requires**, what the challenge
**suggests**, and what **we chose** to build. Our own design decisions are never
presented as NASA requirements.

## Sources reviewed

| Ref | Page | URL |
| --- | --- | --- |
| S1 | Challenge: Details tab | https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/ |
| S2 | Challenge: Resources tab | https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources |
| S3 | Judging & Awards Guide (dated 13 Nov 2026) | https://www.spaceappschallenge.org/resources/judging-awards-guide/ |
| S4 | Project Submission Guide (dated 13 Nov 2026) | https://www.spaceappschallenge.org/resources/project-submission-guide/ |
| S5 | Participant FAQs (dated 13 Nov 2026) | https://www.spaceappschallenge.org/resources/participant-faqs/ |
| S6 | Awards | https://www.spaceappschallenge.org/awards/ |
| S7 | 2026 event page | https://www.spaceappschallenge.org/2026/ |

**Correction to the brief.** The address given in the A1 brief
(`.../2026/challenges/field-shift-adapting-farms-with-nasa-data/`) returns
"Page Not Found". The live challenge page is S1. The challenge title is
unchanged.

**Not reviewed.** The Participant Terms & Conditions and Privacy Policy are
linked from S5 but were not opened. The participant must read them before
submitting (see unresolved items).

**Terminology.** The 2026 official materials use "Super Intelligence (SI)" for
what is commonly called AI. This repository says "AI" and means the same thing.

Status key: **Verified** = wording confirmed on the official page ·
**Met** = satisfied by work already done · **Planned (Ax)** = scheduled for that
phase · **Participant** = an action only the participant can take.

---

## A. Mandatory official requirements

These decide whether the project is eligible for Global Judging and awards.

| ID | Requirement | Source | Official wording or summary | CropShift implementation | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | Respond to an official challenge | S3 | "Respond to one of the official NASA Space Apps Challenges." | Built for "Field Shift: Adapting Farms with NASA Data". | Must | Verified · Met |
| M2 | Address the challenge statement | S1 | "create a decision-support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions." | All four inputs are first-class data contracts (`src/models.py`). Retrieval, crop knowledge and comparison follow in A2 to A5. | Must | Verified · Planned (A2–A5) |
| M3 | Use at least one NASA data source | S4 | "To be eligible for a Global Award, you must use at least one NASA data or resource." | NASA POWER and GPM IMERG (see `data_sources.md`). | Must | Verified · Planned (A2) |
| M4 | Submit before the deadline | S3, S4 | Submission closes "Sunday, November 15 at 11:59 p.m." in the Local Event's time zone. Late saves are not judged. | Plan targets submission by Sunday evening with buffer (`implementation_plan.md`). | Must | Verified · Participant |
| M5 | Project demo within limits | S3, S4 | A slide deck of at most 7 slides including title and intro, or a video of at most 30 seconds. "Projects that exceed these limits will not be eligible for Global Judging." | Produced in A9. | Must | Verified · Planned (A9) |
| M6 | Public links, no login | S4 | Demo and final project links must be "publicly accessible" and "not require a password, permission, or registration". | Needs a public repository or hosted app. Publishing requires the participant's approval. | Must | Verified · Participant decision before A9 |
| M7 | Complete every required field | S3, S4 | Project Name, High-Level Summary, Demo link, Final Project link, Detailed Description, Use of SI, NASA Data, Partner Data and Other References. | Source text for each field is drafted in A9 from these docs. | Must | Verified · Planned (A9) |
| M8 | English | S3 | "Use English language on the project submission page and in any linked materials." | App, code and docs are in English. | Must | Verified · Met |
| M9 | Original work, all external resources listed | S3 | "all external resources including code, text and images (even if they are open source or freely available) used in the project are listed in the References field". No copyrighted material without permission. | `provenance.md` keeps the running reference list. | Must | Verified · Met so far |
| M10 | Disclose AI (SI) use | S4, S5 | "Each team's project submission must include a description of how SI tools were used". Code and data "must acknowledge SI generation in descriptive text and metadata". Images and videos need a visible watermark. No NASA branding in generated content. "SI should not be used to (come up with your idea of how to solve the challenge)." | Disclosure in `README.md`, `provenance.md`, every module docstring and the app footer. No AI-generated images. | Must | Verified · Met so far |
| M11 | No work before the hackathon | S5 | "Teams are not allowed to begin working on the challenges prior to the hackathon." | Repository started 14 Nov 2026 from an empty folder. Nothing copied from earlier work (see `provenance.md`). | Must | Verified · Met |
| M12 | Team rules | S3, S5 | All members registered for the same Local Event. Local Event teams need at least 1 person, at most 6. | Solo participant, Singapore Local Event. | Must | Verified · Participant |
| M13 | No likeness of minors | S4 | No "images, video, audio, or other likeness to persons under 18 years old". | No people are shown in the app or planned demo. | Must | Verified · Met |
| M14 | Agree to the terms | S3 | Two confirmation boxes at submission: terms and conditions, and original work. | Participant confirms at submission. | Must | Verified · Participant |
| M15 | China funding restriction review | S3 | "teams will undergo review for prohibited bilateral activity with China, or a Chinese-owned entity". NASA decides eligibility. | See unresolved item U3 regarding third-party services. | Must | Verified · Participant |

---

## B. Official recommendations

The challenge phrases all of these as "you may". None is mandatory, but each
one is a signal of what judges consider relevant.

### B1. Suggested capabilities

| ID | Recommendation | Source | Official wording or summary | CropShift implementation | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Compare three or more rotations | S1 | "You may compare at least three rotation strategies, including the existing rotation." | `ComparisonResult.follows_challenge_guidance` checks for three or more rotations including the current one. MVP default. | High | Contract Met · Planned (A4) |
| R2 | Explain each strategy | S1 | "explain why it was suggested, what evidence supports it, what benefits it may offer, where information gaps exist, and any risks that would need local review" | `RotationAssessment` has exactly these five parts: rationale, supporting evidence, potential benefits, information gaps, local-review risks. | High | Contract Met · Planned (A4) |
| R3 | Support, not replace, the farmer | S1 | "a supportive tool ... does not replace farmer judgment or local agricultural expertise." | Fixed disclaimer on every comparison and in the app. `requires_local_review` defaults to true. | High | Met |
| R4 | Analyse environmental patterns | S1 | "temperature, heat stress, rainfall, soil moisture, evaporation, frost risk, extreme precipitation, vegetation stress, and long-term water trends" | MVP: temperature, heat stress, rainfall, extreme rain, frost risk, soil wetness, evaporative demand. Vegetation stress and long-term water storage are stretch goals. | High | Planned (A2, A4) |
| R5 | Use farmer priorities | S1 | "water use, forage value, nitrogen-fixing potential, erosion reduction, organic matter improvement, or market suitability" | All six are `PriorityDimension` values. Forage value and market suitability have no data source in the MVP and will be reported as information gaps. | High | Contract Met · Planned (A4) |
| R6 | Highlight timing and opportunities | S1 | "times when fields are typically bare, seasons when current crops appear more vulnerable, or opportunities for rotations that could interrupt pest cycles, reduce water demand, improve infiltration, or add supplemental income" | Bare periods from rotation calendars (`RotationStep` months). Pest-cycle breaks from botanical family. Water demand from crop characteristics. | Medium | Planned (A3, A4) |
| R7 | Explain scientific terms | S1 | "evapotranspiration, soil moisture anomalies, vegetation indices (e.g., NDVI), frost risk, and water-balance indicators" | Plain-language glossary in the interface. | Medium | Planned (A5) |
| R8 | Satellite versus ground data | S1 | "Clarify how satellite observations differ from ground-based measurements" | `DataKind` labels each value as satellite retrieval, reanalysis, ground measurement and so on, and the label is shown beside the value. | Medium | Contract Met · Planned (A5) |
| R9 | Explain uncertainty | S1 | "Explain how the model interprets uncertainty and where local expertise would be needed to validate results." | `UncertaintyStatement` is required on every result and must give its basis and at least one limitation. | High | Contract Met · Planned (A4) |
| R10 | Harmonise resolutions | S1 | "harmonizing datasets with different spatial and temporal resolutions by downsampling, aggregating, or resampling" | One time standard (UTC) and daily resolution for all MVP inputs. `ObservationSeries` refuses to mix resolutions, sources or time standards. | Medium | Contract Met · Planned (A2) |
| R11 | Explain crop roles | S1 | "how nitrogen-fixing crops, cover crops, deep-rooting crops, or drought-tolerant crops contribute to long-term soil health" | Cited short explanations in the crop knowledge base. | Medium | Planned (A3) |
| R12 | Maps, timelines, sliders | S1 | "interactive maps ... timelines, overlays comparing datasets, or scenario sliders" | Timeline charts in the MVP. Maps are a stretch goal. No rainfall or temperature sliders: we compare real historical seasons instead of synthetic adjustments. | Low | Partly planned (A5) |
| R13 | Farmer-centred design | S1 | "easily interpretable for farmers who may have limited technical or geospatial experience ... input their own priorities or constraints, such as water availability, equipment limitations, or market preferences" | Plain language, few steps, priorities and free-text constraints captured in `FarmerPriorityProfile`. | High | Contract Met · Planned (A5) |
| R14 | Compare analytical approaches | S1 | "compare different SI or statistical approaches for identifying patterns" | Not planned. The MVP uses one transparent statistical method. | Low | Out of scope |

### B2. Official resources

All listed on S2. "Use" is our plan, not a NASA instruction.

| Resource | Provider | URL | Use in CropShift |
| --- | --- | --- | --- |
| NASA POWER | NASA | https://power.larc.nasa.gov/ | **MVP core** |
| GPM and IMERG | NASA | https://gpm.nasa.gov/data | **MVP core** (retrieved through NASA POWER) |
| SMAP | NASA | https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap | Stretch |
| Landsat | NASA / USGS | https://earthexplorer.usgs.gov/ | Not planned |
| MODIS / VIIRS | NASA | https://lpdaac.usgs.gov/products/ | Stretch (vegetation index for bare periods) |
| SRTM | NASA | https://www.earthdata.nasa.gov/data/instruments/srtm | Stretch (slope for erosion context) |
| ECOSTRESS | NASA | https://ecostress.jpl.nasa.gov/data | Not planned |
| NLDAS / GLDAS | NASA | https://www.earthdata.nasa.gov/ | Not planned |
| GEDI | NASA | https://gedi.umd.edu/data | Not planned |
| USDA Ag Data Commons | USDA | https://www.nal.usda.gov/services/agdatacommons | Not planned |
| Web Soil Survey | USDA NRCS | https://websoilsurvey.nrcs.usda.gov/app/ | Reference for users in the United States |
| SSURGO / STATSGO2 | USDA NRCS | https://www.nrcs.usda.gov/resources/data-and-reports/soils | Stretch (soil lookup for a United States pilot region) |
| Cropland Data Layer | USDA NASS | https://nassgeodata.gmu.edu/CropScape/ | Stretch (confirm existing rotations in the United States) |
| PRISM | Oregon State University | https://prism.oregonstate.edu/ | Not planned |
| NAIP | USDA | https://naip-usdaonline.hub.arcgis.com/ | Not planned |
| NLCD | USGS | https://www.usgs.gov/centers/eros/science/national-land-cover-database | Not planned |
| FAO GAEZ | FAO | https://gaez.fao.org/ | Candidate evidence source for crop suitability (A3) |
| CoCoRaHS | CoCoRaHS | https://www.cocorahs.org/Maps | Not planned |
| USGS NWIS | USGS | https://waterdata.usgs.gov/nwis | Not planned |
| USDA AMS Market News | USDA | https://www.ams.usda.gov/market-news | Not planned (market suitability stays an information gap) |
| USDA NASS QuickStats | USDA | https://quickstats.nass.usda.gov/ | Not planned |
| OpenET | OpenET | https://openetdata.org/ | Not planned |
| LANDFIRE | USFS | https://www.landfire.gov/ | Not planned |
| Copernicus Sentinel-2 | ESA (partner) | https://dataspace.copernicus.eu/ | Not planned |
| ERA5 | ECMWF (partner) | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview | Not planned |

The page also names GRACE and GRACE-FO in the challenge text (S1) as datasets
teams may explore. Not planned for the MVP.

### B3. Judging criteria

Every project is scored 1 to 5 on each criterion at every judging level (S3).

| Criterion | What a score of 5 needs (summary of S3) | How CropShift aims at it |
| --- | --- | --- |
| Impact | Addresses a significant problem; extensive reach. | Works for any location on Earth from free NASA data; designed for farmers without technical training. |
| Creativity | A novel approach or a meaningful improvement. | Stress-tests rotations against real dry, typical and wet seasons instead of giving one averaged answer. |
| Validity | Scientifically sound, feasible, usable. | Deterministic calculations, cited parameters, explicit uncertainty, tests, and no claims beyond the evidence. |
| Relevance | Directly addresses the challenge; NASA data is integral. | NASA data defines the scenarios that drive every comparison. |
| Presentation | Clear, engaging, well-structured story. | Demo and submission text prepared in A9. |

Galactic Impact, the target award, goes to "the project with the most potential
to improve life on Earth or in the universe" (S6). It is one of ten awards
decided at the final judging stage.

---

## C. Our proposed features

These are CropShift design decisions. NASA does not require them.

| ID | Feature | Why we chose it | Phase |
| --- | --- | --- | --- |
| P1 | Dry, typical and wet **historical** scenario comparison | Shows how a rotation behaves across the range of conditions a farm has actually experienced. Our main differentiator. | A2, A4 |
| P2 | Provenance on every value | Lets a user or reviewer trace any number to its source, version and transformations. | A1 (done) |
| P3 | Observed, reanalysis, literature, modeled and assumed values kept visibly distinct | Prevents calculated indicators from being mistaken for measurements. | A1 (done), A5 |
| P4 | Explicit missing-data handling | Gaps are shown as gaps, never filled silently. | A1 (done), A2 |
| P5 | Supported pilot regions | Keeps crop evidence credible by limiting scope to regions we can document. | A3 |
| P6 | Deterministic engine independent of AI services | Results are reproducible and the app works with every optional service switched off. | A4 |
| P7 | Offline demonstration mode | The demo cannot fail because of a network or API outage. | A2, A5 |
| P8 | Exportable comparison summary | A farmer can keep or share the result. | A5 |
| P9 | No yield predictions, input prescriptions or forecasts | These claims cannot be supported scientifically in a weekend. | All |

## D. Optional stretch goals

Attempt only if the MVP is finished and tested.

| ID | Stretch goal | Phase |
| --- | --- | --- |
| G1 | Plain-language explanations through the OpenAI Responses API, off by default | A6 |
| G2 | Asynchronous research reports through the Manus API, off by default | A7 |
| G3 | SMAP satellite soil moisture as an independent check on modelled soil wetness | After A5 |
| G4 | Map view of the pilot region and data grid cell | After A5 |
| G5 | Soil lookup from SSURGO for a United States pilot region | After A5 |
| G6 | Vegetation index time series (MODIS) to show observed bare periods | After A5 |
| G7 | Workflow automation (stages M1 to M9) | After the hackathon |

---

## Unresolved items

| ID | Item | Who | Needed by |
| --- | --- | --- | --- |
| U1 | Read the Participant Terms & Conditions and Privacy Policy. | Participant | Before submission |
| U2 | Decide how the final project will be made public (public code repository, hosted app, or both). Nothing is published without approval. | Participant | Before A9 |
| U3 | Check whether using the Manus service raises any question under the China funding restriction (M15). Its ownership and the rule's scope for third-party tools were **not** verified here. | Participant | Before A7 |
| U4 | Confirm the Singapore Local Event's own judging time, which S4 says may differ from the global deadline. | Participant | Today |
| U5 | Approve the provisional MVP specification and pilot regions. | Participant | Before A2 |
| U6 | The official page says "More resources may be added before the hackathon begins." The Resources tab was read once on 14 Nov 2026; re-check if time allows. | Either | Optional |
