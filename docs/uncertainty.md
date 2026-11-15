# Uncertainty, limitations and explanations (phase A4.7)

Code: `src/uncertainty.py`, used by `src/comparison_engine.py`. Everything is
deterministic: fixed rules and templates filled from structured data, so every
explanation is available offline and without OpenAI or Manus.

## Uncertainty categories

Every indicator lists the categories that apply, in
`UncertaintyStatement.categories` (a field added to the A1 contract in A4,
optional and backward compatible).

| Category | When it applies |
| --- | --- |
| `data_missing` | Information the indicator needs is missing (soil pH, a crop value) |
| `source_unverified` | Part of the evidence could not be verified against its source |
| `abstract_only_evidence` | Part of the evidence rests on a study abstract |
| `context_dependent_evidence` | The crop values hold under conditions the source describes, which may differ here (added to the required list) |
| `location_approximation` | NASA values describe grid cells tens of kilometres wide |
| `season_assumption` | Fixed calendar windows stand in for the growing season; sowing dates unknown |
| `soil_input_unverified` | Soil information is user-supplied, typical or hypothetical, and not verified |
| `model_limitation` | Reanalysis weather and a descriptive indicator, not a crop or water-balance model |
| `incomplete_observation_period` | Seasons or years were left out because data were missing |
| `unsupported_indicator` | The evidence needed does not exist in the tool |

## Confidence rule

Confidence is a word (not a probability) and always comes with its reasons.

| Starting point | Level |
| --- | --- |
| Structural facts from verified taxonomy and counting (families, legumes, repetition) | high |
| Descriptions of the NASA record | moderate (capped by location approximation and model limitation) |
| Any context-dependent or abstract-only evidence, unverified soil input or season assumption | capped at **low** |
| Unavailable or unsupported indicator | not assessed |

In the pilot comparison, sequence facts are *high*, everything that uses the
weather record or literature ranges is *low*, and unavailable indicators are
*not assessed*. That is the honest state of the evidence, not a defect of the
method.

## Six-part explanation

Every indicator, including every unavailable one, answers:

1. What was calculated or reported.
2. Which data and evidence were used.
3. Which assumptions were made.
4. What the result means.
5. What the result does not establish.
6. What additional information would improve confidence.

A test checks that all six parts are non-empty for every indicator of the pilot
comparison, with and without soil information.

## Keeping kinds of information apart

Each indicator lists its information layers:

| Layer | Example |
| --- | --- |
| `nasa_observation` | NASA POWER daily rainfall and temperature, unmodified |
| `descriptive_calculation` | Season totals, counts, shares of days, TAW and RAW |
| `literature_value` | A cited crop range or soil reference value |
| `user_soil_input` | The pH or soil water the user entered |
| `hypothetical_assumption` | The demonstration soil profile, or a user-chosen season sequence |
| `unavailable` | The indicator could not be calculated |

## Things the tool does not estimate

`UNSUPPORTED_OUTCOMES` lists eight, each with the reason and what would be
needed: crop yield; profit or economic return; nitrogen fixed or left for the
next crop; soil organic carbon change; irrigation requirement; pest or disease
incidence; soil erosion; and an overall resilience score or "best" rotation.

## Limitations of the uncertainty layer itself

* The confidence rule is this project's own; it has not been validated against
  outcomes.
* It describes the inputs' weaknesses. It does not quantify error: no interval
  is attached to any indicator, because no source gives the error of the crop
  ranges and the reanalysis has not been compared with a local station.
