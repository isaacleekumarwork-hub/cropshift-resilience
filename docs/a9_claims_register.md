# Final claims register

Written on 15 November 2026 in phase A9. Every sentence in the README, the
slides, the submission text and anything said in a demonstration must fit one
of the three classes below. Each claim names the evidence behind it, so that
anyone can check it.

* **SAFE_TO_PRESENT**: true as stated, with the evidence named.
* **MUST_QUALIFY**: true only with the qualification attached. Never say the
  first half without the second.
* **MUST_NOT_CLAIM**: unsupported or false. Never state or imply it.

## SAFE_TO_PRESENT

| # | Claim | Evidence |
| --- | --- | --- |
| S1 | CropShift uses 25 years (2001 to 2025) of NASA POWER daily data for the provisional Katumani pilot area in Machakos County, Kenya: 9,131 days of rainfall, temperature (mean, maximum, minimum), humidity and sunshine. | `data/demo/` (NASA's unmodified response, SHA-256 checked on every read); `docs/data_sources.md`; A8 section D |
| S2 | The NASA record is 100 % complete for every variable over the period. | Quality report; `tests/test_independent_verification.py` |
| S3 | It compares three crop-rotation systems documented in published research: continuous maize, maize rotated with cowpea and maize rotated with pigeon pea, all grown in a 1989 to 1996 cropping-systems experiment at Machakos (Rao and Mathuva, 2000). | `data/knowledge/rotation_relationships.json`; `docs/pilot_configuration.md` |
| S4 | It compares historical rainfall and other supported indicators across 25 long-rains (March to May) and 25 short-rains (October to December) seasons. | `docs/historical_scenarios.md` |
| S5 | It groups those past seasons into dry, typical and wet thirds by their rainfall. | `src/scenario_engine.py`; A8 section D (recalculated independently) |
| S6 | Every value it shows carries its source and location in that source; values the evidence audit does not support are kept out of every calculation. | `docs/scientific_evidence_audit.md`; evidence gate tests |
| S7 | It shows missing evidence as "not available" with the reason, rather than estimating it (for example, no verified water need exists for cowpea or pigeon pea). | Engine output; A8 section F |
| S8 | It gives no overall score and no ranking. Results are shown side by side with their tradeoffs. | `overall_score` is always empty; tests in `tests/test_comparison_engine.py` |
| S9 | Its deterministic core works offline, from the bundled NASA data. | Offline tests; A8 browser check with a tampered cache |
| S10 | Farmers can enter their own soil information (pH, texture, water-holding values), each labelled by where it came from. | `src/soil_inputs.py`; Soil & Farm Inputs tab |
| S11 | Farmers can choose priorities. Priorities change the order of what is shown, never the results. | `PrioritySelection`; tests |
| S12 | Every result has a six-part explanation: what was compared, data used, assumptions, what it means, what it does not establish, and confidence. | `src/uncertainty.py` |
| S13 | In this record, rain that fell inside the 92-day window was below maize's indicative seasonal water use (500 to 800 mm) in 24 of 25 long-rains seasons and in all 25 short-rains seasons. | Engine output, 15 Nov 2026 |
| S14 | No frost (daily minimum below 0 °C) occurred in any of the 50 seasons; the lowest daily minimum was 11.74 °C. | Engine output |
| S15 | 905 automated tests pass, including 31 that recalculate the key numbers from the raw NASA file without the project's own code. | A8 section L; A9 test run |
| S16 | It was built during the hackathon by a solo participant with an AI coding assistant, under the participant's direction. | `docs/provenance.md` |

## MUST_QUALIFY

| # | Claim | Required qualification |
| --- | --- | --- |
| Q1 | The pilot site is Katumani, Machakos County. | **The site is provisional.** It has not been approved as final and is a demonstration area. |
| Q2 | Rainfall is compared with crop water use. | **Historical rainfall is not a complete water balance.** It leaves out evaporation, runoff, soil storage and irrigation, and counts only rain inside the window. |
| Q3 | Maize's indicative water use is 500 to 800 mm. | **This is a global FAO value** for the whole growing period. It may not match local varieties. |
| Q4 | Crops are evaluated in the long rains and short rains. | **The crop-specific planting calendar is unknown.** The windows are fixed analysis periods from FAO GIEWS, not sowing dates, and the study does not say which crop was grown in which season. |
| Q5 | Temperatures are compared with documented crop ranges. | **The sources do not say which temperature statistic** (daily mean, maximum or minimum) their ranges refer to. These results are not evidence of suitability or unsuitability. |
| Q6 | The values and calculations were checked. | **The project has not undergone independent agronomist or farmer validation.** The A8 checks were done by the same AI-assisted process that built it. |
| Q7 | Seasons are shown as dry, typical and wet. | **These are historical thirds (terciles), not forecasts.** They describe 2001 to 2025, not what will happen. |
| Q8 | NASA data describes the pilot area. | **It is an area average**, over grid cells roughly 55 km by 70 km (weather) and 110 km (sunshine), from a reanalysis, **not measurements from a farm**, and not compared with a local station. |
| Q9 | Legume rotations were associated with higher maize yields in published studies. | **Past study results, not predictions.** The review reports wide variation and weaker effects after cowpea; at Machakos, maize after pigeon pea gained little. |
| Q10 | The tool could support farmer decision-making. | **Potential only**, subject to local validation. It has not been used by farmers. |
| Q11 | The knowledge base is cited. | **Mostly secondary datasheets**; two journal articles were read as abstracts only; it is provisional. |

## MUST_NOT_CLAIM

| # | Forbidden claim | Why |
| --- | --- | --- |
| N1 | Predicted crop yield, yield gain or profitability | No crop model, prices or costs exist in the tool |
| N2 | Proven nitrogen or soil-health improvement | Not measured or modelled; the review finds no general soil organic matter effect |
| N3 | A best, recommended, optimal or most resilient rotation | No ranking or scoring method exists, by design |
| N4 | Verified farm-level suitability | Area-average data, a provisional site and unverified temperature measures |
| N5 | Independent scientific or agronomist endorsement, or "validated" | None has taken place |
| N6 | Farmer-tested, user-tested or proven effectiveness or impact | No farmer or external user has used it |
| N7 | Weather or seasonal forecasts | Historical record only |
| N8 | An overall resilience score | None exists, by design |
| N9 | Endorsement by NASA, or use of NASA branding | Independent project; no NASA logo is used |
| N10 | That judges can open a localhost address | Localhost is only on the participant's computer |
| N11 | That a public link, video or file exists before it has been created and checked | A9 rule |
| N12 | That AI was not used | AI-assisted development must be disclosed |

## Words to avoid

These words, used about CropShift's outputs, signal a forbidden claim:
"best", "recommended", "optimal" (except when quoting a source's range name),
"predicts", "forecast", "will yield", "increases yield", "proven", "validated",
"farmer-tested", "guarantees", "score", "suitable for your farm".

## Check of final materials

Every A9 document was searched for these words and read against the register.

| Material | Result |
| --- | --- |
| `README.md` | Checked; see the A9 report, section C |
| `docs/a9_submission_text.md` | Checked |
| Seven-slide deck (private claude.ai Slides artifact) | Checked |
| `docs/a9_release_report.md` | Checked |
| The application's own screens | Already enforced by tests since A5 (`tests/test_app.py`, `tests/test_scientific_communication.py`) |
