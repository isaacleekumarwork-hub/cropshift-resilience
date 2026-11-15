# Rotation comparison methodology (phases A4.5 and A4.6)

Code: `src/comparison_engine.py`. Tests: `tests/test_comparison_engine.py`.

The engine sets candidate crop sequences side by side against real past seasons
from the NASA record, the user's soil information and cited crop evidence. It
then presents the result through the farmer's priorities. It is deterministic:
the same inputs and timestamp always give the same report, and no AI service is
involved.

## What it deliberately does not do

* **No overall score and no ranking.** The indicators measure unlike things
  (rainfall against water use, plant families, soil pH), and no defensible method
  exists here to weigh one against another. The report has an `overall_score`
  field that can only be empty. Strategies are shown side by side, with
  tradeoff notes that name no winner.
* **No predictions.** No yield, profit, nitrogen fixed or left in the soil, soil
  carbon change, irrigation requirement, pest or disease incidence, or erosion.
  `UNSUPPORTED_OUTCOMES` in `src/uncertainty.py` says for each why it is not
  estimated and what would be needed.
* **No unchecked evidence.** Every literature value passes the evidence gate
  (`docs/scientific_evidence_audit.md`). A refused value makes its indicator
  unavailable; nothing is borrowed from another crop or filled in.

## How a strategy is assessed

For each strategy (`assess_strategy`):

1. The crop sequence is checked against the knowledge base; an unknown crop is
   rejected, and a strategy claiming a documented system must use its crops.
2. Each crop is evaluated against every season window it may occupy: both
   windows when the season is unknown (the default), or the user's hypothetical
   choice.
3. Seasonal indicators are computed for every classified past season (25 per
   window), then summarised by category: dry, typical and wet.
4. Soil indicators are computed from the resolved soil information, if any.
5. Sequence indicators are computed from the crops and their families.
6. Every stored A3 constraint that applies to the crops is evaluated within its
   evidence scope (below).
7. Cited background is attached: what the Machakos study reported for the system
   and what the review of legume rotations reports. Background explains; it never
   enters a calculation.

## Indicators

| Indicator | What it says | Available for |
| --- | --- | --- |
| Season rainfall against indicative crop water use | For each past season: below, within or above the crop's indicative seasonal water use (FAO Training Manual 3, Table 14) | Maize, sorghum, common bean. **Not** cowpea, pigeon pea or mung bean: no verified value exists |
| Daily temperature against a documented range | Share of days whose NASA daily mean was inside each admitted range, and how often the season mean lay outside it | Every crop except sorghum, whose two values apply to growth stages with unknown dates |
| Frost days | Days with daily minimum below 0 °C (ETCCDI FD) in each past season | Every window |
| Growing period against the window | Documented growing period minus the 92-day window | Maize, sorghum, common bean |
| Annual rainfall against a documented range | Complete years below, inside and above each admitted annual range | Every crop except sorghum (its sentence is ambiguous) |
| Soil pH against documented ranges | Inside, below or above each admitted range | Every crop except cowpea, when the user gives a pH |
| Water held in the root zone | FAO-56 Eq. 82 from rooting depth and the soil's available water | Every crop, when the user gives soil water or a texture class |
| Water the crop can use before stress | FAO-56 Eq. 83 with the depletion fraction | Every crop except pigeon pea, when soil water is given |
| Crops and plant families | Distinct crops and botanical families | Every sequence |
| Legume in the sequence | Count of nitrogen-fixing crops, from cited statements | Every sequence |
| Same crop or family in succession | Steps of the repeating cycle that keep the crop or family | Every sequence |

Each result has a status:

* **supported**: built on verified facts and the NASA record, shown without conditions;
* **conditional**: built on context-dependent evidence, and the conditions are shown beside it (the contract refuses a conditional result without conditions);
* **unavailable**: not calculated, with what is missing (the contract refuses an unavailable result that carries values).

The catalogue as defined in code:

| Indicator | Scope | Unit | A3 mapping | Priorities it informs | Method |
| --- | --- | --- | --- | --- | --- |
| `rainfall_vs_crop_water_use` | seasonal | mm | seasonal-water-need-to-seasonal-rainfall | water_use, climate_resilience | For every classified season: below, within or above the documented water-use range (FAO TM3). |
| `temperature_vs_documented_range` | seasonal | % | temperature-requirement-to-air-temperature | climate_resilience | For every classified season: days with NASA daily mean temperature inside the range, as a percentage. |
| `frost_days` | seasonal | count |  | climate_resilience | Count per classified season. |
| `growing_period_vs_window` | window | day | growing-period-to-season-length | water_use, climate_resilience | Documented total growing period (FAO TM3) minus the window length. |
| `annual_rainfall_vs_documented_range` | annual | count | annual-rainfall-requirement-to-precipitation | climate_resilience, water_use | Count of years below, inside and above each documented annual-rainfall range. |
| `soil_ph_vs_documented_range` | soil | pH | soil-ph-requirement-to-soil-ph |  | Inside, below or above each admitted range. |
| `root_zone_available_water` | soil | mm | rooting-depth-to-soil-water | water_use, climate_resilience | TAW = 1000 (θFC − θWP) Zr, as a range from the ranges of its inputs. |
| `readily_available_water` | soil | mm | depletion-fraction-to-soil-water | water_use, climate_resilience | RAW = p TAW, with the depletion fraction p from FAO-56 Table 22. |
| `crop_family_diversity` | sequence | count |  | crop_diversity, pest_cycle_disruption | Count of distinct crops and of distinct families. |
| `legume_in_sequence` | sequence | count |  | nitrogen_fixation, organic_matter, crop_diversity | Count of nitrogen-fixing crops, from cited crop statements. |
| `crop_repetition` | sequence | count |  | pest_cycle_disruption, crop_diversity | Count over the repeating cycle, including the step from the last slot back to the first. |

### Critical water limitation

Pigeon pea has no verified water requirement, growing period or depletion
fraction, and cowpea has no seasonal water need or growing period. Their water
indicators are **unavailable** in every window. No value is borrowed from
another legume, and rainfall is not used as a substitute. The tradeoff note says
that where evidence is missing "the comparison is incomplete, not favourable".

### Rainfall is not a water balance

The rainfall indicator compares rainfall within a fixed window with crop water
use (evapotranspiration) under the source's standard conditions. The two are not
directly comparable without a water balance: runoff, evaporation from bare soil,
soil storage, rain outside the window and irrigation all intervene. Every result
displays this condition. It is a first indication of how often past seasons fell
short of what the crop typically uses, not an irrigation requirement.

## Constraints

Every A3 constraint that applies to a strategy's crops is evaluated, and only
within its evidence scope:

| Constraint | Severity | How A4 evaluates it |
| --- | --- | --- |
| `frost-kills-maize` | hard | Triggered if any past season in the window had a frost day (ETCCDI FD) |
| `frost-sensitive-crops` | advisory | The same, for sorghum, pigeon pea and common bean |
| `cold-stops-common-bean-growth` | context-dependent | Days with daily mean below 10 °C across past seasons |
| `growing-period-longer-than-season` | advisory | Documented shortest growing period longer than the window |
| `seasonal-water-need-above-rainfall` | context-dependent | Past seasons with rainfall below the low end of water use |
| `soil-ph-outside-documented-range` | context-dependent | User pH outside an admitted range; not evaluated without a pH |
| `temperature-outside-documented-range` | context-dependent | Past seasons whose mean lay outside an admitted range |
| `waterlogging-sensitive-crop-on-wet-soil` | advisory | Triggered by a poorly drained field; not evaluated without drainage. Whether a season was wet enough to waterlog a field cannot be told from rainfall totals |
| `drought-at-flowering-maize` | context-dependent | **Not evaluated**: flowering dates are unknown because sowing dates are unknown |
| `continuous-cereal-without-legume` | advisory | A sequence with cereals and no legume |
| `legume-needs-pest-management` | advisory | Cowpea or pigeon pea in the sequence (site-specific finding at Machakos) |
| `perennial-in-seasonal-rotation` | context-dependent | Pigeon pea in a slot of a seasonal sequence |
| `same-crop-in-succession` | advisory | A step of the cycle that repeats the crop |
| `same-family-in-succession` | unsupported | **Never applied**: the gate refuses its only evidence, so the outcome is "not applied" |

Outcomes are `triggered`, `not triggered`, `not evaluated` (information missing)
or `not applied` (unsupported rule). Triggered findings are listed as risks for
local review; none of them becomes a score.

## Farmer priorities

`PrioritySelection` holds the priorities a farmer chose, **in the farmer's own
order, with no weights**: the model has no weight field and rejects duplicates.
The A1 `FarmerPriorityProfile`, which does carry weights, is not used.

A selected priority:

* moves its indicators to the front of `PriorityView.indicator_order`, in the
  farmer's order;
* gets a section with the A3 definition of why it matters, how much evidence is
  available, and for each strategy the relevant results and what is missing;
* changes presentation only: the strategy results are identical with or without
  priorities (tested);
* if the tool holds no evidence for it, says so and estimates nothing.

| Priority | Indicators it brings forward |
| --- | --- |
| Water conservation (`water_use`) | `rainfall_vs_crop_water_use`, `growing_period_vs_window`, `annual_rainfall_vs_documented_range`, `root_zone_available_water`, `readily_available_water` |
| Nitrogen-fixing potential (`nitrogen_fixation`) | `legume_in_sequence` |
| Erosion reduction (`erosion_reduction`) | none: evidence not available |
| Organic matter improvement (`organic_matter`) | `legume_in_sequence` |
| Forage value (`forage_value`) | none: evidence not available |
| Market and economic considerations (`market_suitability`) | none: evidence not available |
| Pest and disease cycle disruption (`pest_cycle_disruption`) | `crop_family_diversity`, `crop_repetition` |
| Resilience across dry and wet seasons (`climate_resilience`) | `rainfall_vs_crop_water_use`, `temperature_vs_documented_range`, `frost_days`, `growing_period_vs_window`, `annual_rainfall_vs_documented_range`, `root_zone_available_water`, `readily_available_water` |
| Crop diversity (`crop_diversity`) | `crop_family_diversity`, `legume_in_sequence`, `crop_repetition` |
| Operational simplicity (`operational_simplicity`) | none: evidence not available |

Priorities with no indicator (erosion reduction, forage value, market and
economic considerations, operational simplicity) report: "CropShift holds no
evidence that can assess ... Nothing is estimated for it", followed by what
would be needed. For market and economic considerations it adds that no prices,
costs or market information are held, and that a profitability figure in one
study abstract is not used because the abstract gives no prices or method.

## Tradeoffs

`build_tradeoffs` writes plain, side-by-side statements on plant-family
diversity, water-use evidence, legumes and pest management, and what all
strategies share (maize is in all three, so its weather comparisons are
identical and the strategies differ only in the other slots). None names a
winner.

## Output for A5

`ComparisonReport` holds the site and its provisional status, the dataset
fingerprint and citations, the knowledge-base and audit versions, a scenario
overview per window, the resolved soil, one `StrategyAssessment` per strategy
(profile, indicators, constraint findings, background, evidence completeness,
information gaps, risks for local review), the priority view, the tradeoffs, the
unsupported outcomes and the limitations. `to_comparison_result()` exports the
same comparison in the A1 `ComparisonResult` contract: three strategies, the
current practice, the six representative seasons, and one rotation assessment
per strategy.

## Sample results: the pilot comparison

_Generated from the code and data on 15 November 2026 by a script; do not edit by hand._

No soil information supplied (the default), all three candidate strategies, both rainy seasons.

### Continuous maize

Indicators: 5 supported, 8 conditional, 3 unavailable. Families: Poaceae.

| Indicator | Status | Confidence | Result |
| --- | --- | --- | --- |
| Season rainfall against indicative crop water use | conditional | low | Maize, long rains: season rainfall was below the indicative water use of 500 to 800 mm in 24 of 25 past seasons, within it in 1 and above it in 0 (rain within the 92-day window only; not a water balance). |
| Daily temperature against a documented range | conditional | low | Maize, long rains: on a median 26.1 % of days the daily mean temperature was inside the optimal range of 18 to 21 °C; the season mean lay outside it in 24 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | conditional | low | Maize, long rains: the documented growing period (125 to 180 days) is longer than the 92-day window by 33 to 88 days. |
| Season rainfall against indicative crop water use | conditional | low | Maize, short rains: season rainfall was below the indicative water use of 500 to 800 mm in 25 of 25 past seasons, within it in 0 and above it in 0 (rain within the 92-day window only; not a water balance). |
| Daily temperature against a documented range | conditional | low | Maize, short rains: on a median 23.9 % of days the daily mean temperature was inside the optimal range of 18 to 21 °C; the season mean lay outside it in 21 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | conditional | low | Maize, short rains: the documented growing period (125 to 180 days) is longer than the 92-day window by 33 to 88 days. |
| Frost days in the season | supported | low | Long rains: frost days (daily minimum below 0 °C) occurred in 0 of 25 past seasons; the lowest daily minimum recorded was 11.74 °C. |
| Frost days in the season | supported | low | Short rains: frost days (daily minimum below 0 °C) occurred in 0 of 25 past seasons; the lowest daily minimum recorded was 11.82 °C. |
| Annual rainfall against a documented range | conditional | low | Maize: annual rainfall was inside the optimal range of at least 750 mm a year in 6 of 25 years, below it in 19 and above it in 0. |
| Annual rainfall against a documented range | conditional | low | Maize: annual rainfall was inside the tolerated range of 230 to 4100 mm a year in 25 of 25 years, below it in 0 and above it in 0. |
| Soil pH against documented ranges | unavailable | not_assessed | Maize: not available. No soil pH was supplied. |
| Water held in the root zone | unavailable | not_assessed | Maize: not available. Soil water information is missing. |
| Water the crop can use before stress | unavailable | not_assessed | Maize: not available. Soil water information is missing. |
| Crops and plant families in the sequence | supported | high | Continuous maize: 1 crop from 1 plant family (Poaceae). |
| Legume in the sequence | supported | high | Continuous maize: includes no nitrogen-fixing legume. |
| Same crop or family in succession | supported | high | Continuous maize: of the 1 step in one cycle, 1 keeps the same crop and 1 keeps the same plant family. |

Constraint findings:

* `continuous-cereal-without-legume` (advisory): **triggered**. The sequence has cereals and no legume.
* `drought-at-flowering-maize` (context_dependent): **not evaluated**. Maize: flowering dates are unknown because sowing dates are not known. The longest dry spell of each past season is shown in the scenario data.
* `frost-kills-maize` (hard): **not triggered**. Maize, long rains: frost days in 0 of 25 past seasons in the NASA record.
* `frost-kills-maize` (hard): **not triggered**. Maize, short rains: frost days in 0 of 25 past seasons in the NASA record.
* `growing-period-longer-than-season` (advisory): **triggered**. Maize, long rains: documented growing period 125 to 180 days against a 92-day window.
* `growing-period-longer-than-season` (advisory): **triggered**. Maize, short rains: documented growing period 125 to 180 days against a 92-day window.
* `same-crop-in-succession` (advisory): **triggered**. 1 of 1 steps in the cycle repeat the same crop.
* `same-family-in-succession` (unsupported): **not applied**. Not applied: no source read supports this rule, so it does not affect the comparison.
* `seasonal-water-need-above-rainfall` (context_dependent): **triggered**. Maize, long rains: season rainfall below the low end of indicative water use (500 mm) in 24 of 25 past seasons.
* `seasonal-water-need-above-rainfall` (context_dependent): **triggered**. Maize, short rains: season rainfall below the low end of indicative water use (500 mm) in 25 of 25 past seasons.
* `soil-ph-outside-documented-range` (context_dependent): **not evaluated**. Maize: no soil pH was supplied.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Maize, long rains: the season mean temperature lay outside at least one documented range in 24 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Maize, short rains: the season mean temperature lay outside at least one documented range in 21 of 25 past seasons.
* `waterlogging-sensitive-crop-on-wet-soil` (advisory): **not evaluated**. Maize: soil drainage was not supplied. Whether a season was wet enough to waterlog the field cannot be told from rainfall totals.

Background (explains, never calculates):

* System 1 of the Machakos experiment: continuous sole maize. It is the system against which the others were compared. Reported outcome: The comparison baseline. The abstract gives no yield for it. (abstract only: `rao-mathuva-2000`)
* Across 199 observations in sub-Saharan Africa, a cereal grown after a grain legume yielded on average 0.49 t/ha more grain than the same cereal grown continuously, an increase of 41 %. The effect is highly significant, but its variability is large. (abstract only: `franke-2018`)
* Applying nitrogen fertiliser to the cereal reduces the benefit of a preceding legume, but at 60-120 kg N/ha the response still equalled 0.32 t/ha, or 59 % of the response with no nitrogen applied. The review concludes that effects other than nitrogen are important. (abstract only: `franke-2018`)

### Maize rotated with cowpea

Indicators: 5 supported, 11 conditional, 10 unavailable. Families: Fabaceae, Poaceae.

| Indicator | Status | Confidence | Result |
| --- | --- | --- | --- |
| Season rainfall against indicative crop water use | conditional | low | Maize, long rains: season rainfall was below the indicative water use of 500 to 800 mm in 24 of 25 past seasons, within it in 1 and above it in 0 (rain within the 92-day window only; not a water balance). |
| Daily temperature against a documented range | conditional | low | Maize, long rains: on a median 26.1 % of days the daily mean temperature was inside the optimal range of 18 to 21 °C; the season mean lay outside it in 24 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | conditional | low | Maize, long rains: the documented growing period (125 to 180 days) is longer than the 92-day window by 33 to 88 days. |
| Season rainfall against indicative crop water use | conditional | low | Maize, short rains: season rainfall was below the indicative water use of 500 to 800 mm in 25 of 25 past seasons, within it in 0 and above it in 0 (rain within the 92-day window only; not a water balance). |
| Daily temperature against a documented range | conditional | low | Maize, short rains: on a median 23.9 % of days the daily mean temperature was inside the optimal range of 18 to 21 °C; the season mean lay outside it in 21 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | conditional | low | Maize, short rains: the documented growing period (125 to 180 days) is longer than the 92-day window by 33 to 88 days. |
| Season rainfall against indicative crop water use | unavailable | not_assessed | Cowpea, long rains: not available. No verified seasonal water-use value exists for cowpea. |
| Daily temperature against a documented range | conditional | low | Cowpea, long rains: on a median 0 % of days the daily mean temperature was inside the suitable range of 25 to 35 °C; the season mean lay outside it in 25 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | unavailable | not_assessed | Cowpea, long rains: not available. The sources read give no growing period in days for cowpea. |
| Season rainfall against indicative crop water use | unavailable | not_assessed | Cowpea, short rains: not available. No verified seasonal water-use value exists for cowpea. |
| Daily temperature against a documented range | conditional | low | Cowpea, short rains: on a median 0 % of days the daily mean temperature was inside the suitable range of 25 to 35 °C; the season mean lay outside it in 25 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | unavailable | not_assessed | Cowpea, short rains: not available. The sources read give no growing period in days for cowpea. |
| Frost days in the season | supported | low | Long rains: frost days (daily minimum below 0 °C) occurred in 0 of 25 past seasons; the lowest daily minimum recorded was 11.74 °C. |
| Frost days in the season | supported | low | Short rains: frost days (daily minimum below 0 °C) occurred in 0 of 25 past seasons; the lowest daily minimum recorded was 11.82 °C. |
| Annual rainfall against a documented range | conditional | low | Maize: annual rainfall was inside the optimal range of at least 750 mm a year in 6 of 25 years, below it in 19 and above it in 0. |
| Annual rainfall against a documented range | conditional | low | Maize: annual rainfall was inside the tolerated range of 230 to 4100 mm a year in 25 of 25 years, below it in 0 and above it in 0. |
| Soil pH against documented ranges | unavailable | not_assessed | Maize: not available. No soil pH was supplied. |
| Water held in the root zone | unavailable | not_assessed | Maize: not available. Soil water information is missing. |
| Water the crop can use before stress | unavailable | not_assessed | Maize: not available. Soil water information is missing. |
| Annual rainfall against a documented range | conditional | low | Cowpea: annual rainfall was inside the suitable range of 750 to 1100 mm a year in 6 of 25 years, below it in 19 and above it in 0. |
| Soil pH against documented ranges | unavailable | not_assessed | Cowpea: not available. No soil pH was supplied. |
| Water held in the root zone | unavailable | not_assessed | Cowpea: not available. Soil water information is missing. |
| Water the crop can use before stress | unavailable | not_assessed | Cowpea: not available. Soil water information is missing. |
| Crops and plant families in the sequence | supported | high | Maize rotated with cowpea: 2 crops from 2 plant families (Fabaceae, Poaceae). |
| Legume in the sequence | supported | high | Maize rotated with cowpea: includes 1 nitrogen-fixing legume (cowpea). |
| Same crop or family in succession | supported | high | Maize rotated with cowpea: of the 2 steps in one cycle, 0 keep the same crop and 0 keep the same plant family. |

Constraint findings:

* `continuous-cereal-without-legume` (advisory): **not triggered**. The sequence includes a legume.
* `drought-at-flowering-maize` (context_dependent): **not evaluated**. Maize: flowering dates are unknown because sowing dates are not known. The longest dry spell of each past season is shown in the scenario data.
* `frost-kills-maize` (hard): **not triggered**. Maize, long rains: frost days in 0 of 25 past seasons in the NASA record.
* `frost-kills-maize` (hard): **not triggered**. Maize, short rains: frost days in 0 of 25 past seasons in the NASA record.
* `growing-period-longer-than-season` (advisory): **triggered**. Maize, long rains: documented growing period 125 to 180 days against a 92-day window.
* `growing-period-longer-than-season` (advisory): **triggered**. Maize, short rains: documented growing period 125 to 180 days against a 92-day window.
* `legume-needs-pest-management` (advisory): **triggered**. Cowpea is in the sequence; at Machakos it was affected by pests and diseases.
* `same-crop-in-succession` (advisory): **not triggered**. 0 of 2 steps in the cycle repeat the same crop.
* `same-family-in-succession` (unsupported): **not applied**. Not applied: no source read supports this rule, so it does not affect the comparison.
* `seasonal-water-need-above-rainfall` (context_dependent): **triggered**. Maize, long rains: season rainfall below the low end of indicative water use (500 mm) in 24 of 25 past seasons.
* `seasonal-water-need-above-rainfall` (context_dependent): **triggered**. Maize, short rains: season rainfall below the low end of indicative water use (500 mm) in 25 of 25 past seasons.
* `soil-ph-outside-documented-range` (context_dependent): **not evaluated**. Maize: no soil pH was supplied.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Maize, long rains: the season mean temperature lay outside at least one documented range in 24 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Maize, short rains: the season mean temperature lay outside at least one documented range in 21 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Cowpea, long rains: the season mean temperature lay outside at least one documented range in 25 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Cowpea, short rains: the season mean temperature lay outside at least one documented range in 25 of 25 past seasons.
* `waterlogging-sensitive-crop-on-wet-soil` (advisory): **not evaluated**. Maize: soil drainage was not supplied. Whether a season was wet enough to waterlog the field cannot be told from rainfall totals.
* `waterlogging-sensitive-crop-on-wet-soil` (advisory): **not evaluated**. Cowpea: soil drainage was not supplied. Whether a season was wet enough to waterlog the field cannot be told from rainfall totals.

Background (explains, never calculates):

* System 2 of the Machakos experiment: maize rotated with a short-duration legume, cowpea, described as a maize-cowpea sequential system. Reported outcome: 17 % higher maize yields than continuous sole maize. Cowpea was affected by pests and diseases. (abstract only: `rao-mathuva-2000`)
* Across 199 observations in sub-Saharan Africa, a cereal grown after a grain legume yielded on average 0.49 t/ha more grain than the same cereal grown continuously, an increase of 41 %. The effect is highly significant, but its variability is large. (abstract only: `franke-2018`)
* Applying nitrogen fertiliser to the cereal reduces the benefit of a preceding legume, but at 60-120 kg N/ha the response still equalled 0.32 t/ha, or 59 % of the response with no nitrogen applied. The review concludes that effects other than nitrogen are important. (abstract only: `franke-2018`)
* Beneficial impacts of grain legumes on soil organic matter can occur if legumes contribute to greater overall cropping productivity, but studies generally report no such impacts. (abstract only: `franke-2018`)

### Maize rotated with pigeon pea

Indicators: 5 supported, 12 conditional, 10 unavailable. Families: Fabaceae, Poaceae.

| Indicator | Status | Confidence | Result |
| --- | --- | --- | --- |
| Season rainfall against indicative crop water use | conditional | low | Maize, long rains: season rainfall was below the indicative water use of 500 to 800 mm in 24 of 25 past seasons, within it in 1 and above it in 0 (rain within the 92-day window only; not a water balance). |
| Daily temperature against a documented range | conditional | low | Maize, long rains: on a median 26.1 % of days the daily mean temperature was inside the optimal range of 18 to 21 °C; the season mean lay outside it in 24 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | conditional | low | Maize, long rains: the documented growing period (125 to 180 days) is longer than the 92-day window by 33 to 88 days. |
| Season rainfall against indicative crop water use | conditional | low | Maize, short rains: season rainfall was below the indicative water use of 500 to 800 mm in 25 of 25 past seasons, within it in 0 and above it in 0 (rain within the 92-day window only; not a water balance). |
| Daily temperature against a documented range | conditional | low | Maize, short rains: on a median 23.9 % of days the daily mean temperature was inside the optimal range of 18 to 21 °C; the season mean lay outside it in 21 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | conditional | low | Maize, short rains: the documented growing period (125 to 180 days) is longer than the 92-day window by 33 to 88 days. |
| Season rainfall against indicative crop water use | unavailable | not_assessed | Pigeon pea, long rains: not available. No verified seasonal water-use value exists for pigeon pea. |
| Daily temperature against a documented range | conditional | low | Pigeon pea, long rains: on a median 95.7 % of days the daily mean temperature was inside the suitable range of 20 to 40 °C; the season mean lay outside it in 0 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | unavailable | not_assessed | Pigeon pea, long rains: not available. The sources read give no growing period in days for pigeon pea. |
| Season rainfall against indicative crop water use | unavailable | not_assessed | Pigeon pea, short rains: not available. No verified seasonal water-use value exists for pigeon pea. |
| Daily temperature against a documented range | conditional | low | Pigeon pea, short rains: on a median 96.7 % of days the daily mean temperature was inside the suitable range of 20 to 40 °C; the season mean lay outside it in 0 of 25 seasons (the source does not say which temperature it means, so this is not evidence of unsuitability). |
| Growing period against the season window | unavailable | not_assessed | Pigeon pea, short rains: not available. The sources read give no growing period in days for pigeon pea. |
| Frost days in the season | supported | low | Long rains: frost days (daily minimum below 0 °C) occurred in 0 of 25 past seasons; the lowest daily minimum recorded was 11.74 °C. |
| Frost days in the season | supported | low | Short rains: frost days (daily minimum below 0 °C) occurred in 0 of 25 past seasons; the lowest daily minimum recorded was 11.82 °C. |
| Annual rainfall against a documented range | conditional | low | Maize: annual rainfall was inside the optimal range of at least 750 mm a year in 6 of 25 years, below it in 19 and above it in 0. |
| Annual rainfall against a documented range | conditional | low | Maize: annual rainfall was inside the tolerated range of 230 to 4100 mm a year in 25 of 25 years, below it in 0 and above it in 0. |
| Soil pH against documented ranges | unavailable | not_assessed | Maize: not available. No soil pH was supplied. |
| Water held in the root zone | unavailable | not_assessed | Maize: not available. Soil water information is missing. |
| Water the crop can use before stress | unavailable | not_assessed | Maize: not available. Soil water information is missing. |
| Annual rainfall against a documented range | conditional | low | Pigeon pea: annual rainfall was inside the optimal range of at least 625 mm a year in 14 of 25 years, below it in 11 and above it in 0. |
| Annual rainfall against a documented range | conditional | low | Pigeon pea: annual rainfall was inside the tolerated range of at least 250 mm a year in 25 of 25 years, below it in 0 and above it in 0. |
| Soil pH against documented ranges | unavailable | not_assessed | Pigeon pea: not available. No soil pH was supplied. |
| Water held in the root zone | unavailable | not_assessed | Pigeon pea: not available. Soil water information is missing. |
| Water the crop can use before stress | unavailable | not_assessed | Pigeon pea: not available. Soil water information is missing. |
| Crops and plant families in the sequence | supported | high | Maize rotated with pigeon pea: 2 crops from 2 plant families (Fabaceae, Poaceae). |
| Legume in the sequence | supported | high | Maize rotated with pigeon pea: includes 1 nitrogen-fixing legume (pigeon pea). |
| Same crop or family in succession | supported | high | Maize rotated with pigeon pea: of the 2 steps in one cycle, 0 keep the same crop and 0 keep the same plant family. |

Constraint findings:

* `continuous-cereal-without-legume` (advisory): **not triggered**. The sequence includes a legume.
* `drought-at-flowering-maize` (context_dependent): **not evaluated**. Maize: flowering dates are unknown because sowing dates are not known. The longest dry spell of each past season is shown in the scenario data.
* `frost-kills-maize` (hard): **not triggered**. Maize, long rains: frost days in 0 of 25 past seasons in the NASA record.
* `frost-kills-maize` (hard): **not triggered**. Maize, short rains: frost days in 0 of 25 past seasons in the NASA record.
* `frost-sensitive-crops` (advisory): **not triggered**. Pigeon pea, long rains: frost days in 0 of 25 past seasons in the NASA record.
* `frost-sensitive-crops` (advisory): **not triggered**. Pigeon pea, short rains: frost days in 0 of 25 past seasons in the NASA record.
* `growing-period-longer-than-season` (advisory): **triggered**. Maize, long rains: documented growing period 125 to 180 days against a 92-day window.
* `growing-period-longer-than-season` (advisory): **triggered**. Maize, short rains: documented growing period 125 to 180 days against a 92-day window.
* `legume-needs-pest-management` (advisory): **triggered**. Pigeon pea is in the sequence; at Machakos it was affected by pests and diseases.
* `perennial-in-seasonal-rotation` (context_dependent): **triggered**. Pigeon pea is a short-lived perennial placed in a slot of a seasonal sequence; one slot may span more than one season.
* `same-crop-in-succession` (advisory): **not triggered**. 0 of 2 steps in the cycle repeat the same crop.
* `same-family-in-succession` (unsupported): **not applied**. Not applied: no source read supports this rule, so it does not affect the comparison.
* `seasonal-water-need-above-rainfall` (context_dependent): **triggered**. Maize, long rains: season rainfall below the low end of indicative water use (500 mm) in 24 of 25 past seasons.
* `seasonal-water-need-above-rainfall` (context_dependent): **triggered**. Maize, short rains: season rainfall below the low end of indicative water use (500 mm) in 25 of 25 past seasons.
* `soil-ph-outside-documented-range` (context_dependent): **not evaluated**. Maize: no soil pH was supplied.
* `soil-ph-outside-documented-range` (context_dependent): **not evaluated**. Pigeon pea: no soil pH was supplied.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Maize, long rains: the season mean temperature lay outside at least one documented range in 24 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **triggered**. Maize, short rains: the season mean temperature lay outside at least one documented range in 21 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **not triggered**. Pigeon pea, long rains: the season mean temperature lay outside at least one documented range in 0 of 25 past seasons.
* `temperature-outside-documented-range` (context_dependent): **not triggered**. Pigeon pea, short rains: the season mean temperature lay outside at least one documented range in 0 of 25 past seasons.
* `waterlogging-sensitive-crop-on-wet-soil` (advisory): **not evaluated**. Maize: soil drainage was not supplied. Whether a season was wet enough to waterlog the field cannot be told from rainfall totals.
* `waterlogging-sensitive-crop-on-wet-soil` (advisory): **not evaluated**. Pigeon pea: soil drainage was not supplied. Whether a season was wet enough to waterlog the field cannot be told from rainfall totals.

Background (explains, never calculates):

* System 3 of the Machakos experiment: maize rotated with a long-duration legume, pigeon pea. Reported outcome: Maize yielded only marginally better than continuous sole maize. Pigeon pea was affected by pests and diseases. (abstract only: `rao-mathuva-2000`)
* Across 199 observations in sub-Saharan Africa, a cereal grown after a grain legume yielded on average 0.49 t/ha more grain than the same cereal grown continuously, an increase of 41 %. The effect is highly significant, but its variability is large. (abstract only: `franke-2018`)
* Applying nitrogen fertiliser to the cereal reduces the benefit of a preceding legume, but at 60-120 kg N/ha the response still equalled 0.32 t/ha, or 59 % of the response with no nitrogen applied. The review concludes that effects other than nitrogen are important. (abstract only: `franke-2018`)
* A legume that fixes nitrogen does not necessarily leave it in the field. Pigeon pea is reported to fix 40-97 kg N/ha/year in Africa, with 88 % used for the formation of pods and seeds. Common bean is described as less efficient in fixing nitrogen than other legumes. (verified conditional: `feedipedia-pigeon-pea-forage`)
* Beneficial impacts of grain legumes on soil organic matter can occur if legumes contribute to greater overall cropping productivity, but studies generally report no such impacts. (abstract only: `franke-2018`)

### Tradeoffs, side by side

* **Plant-family diversity.** Continuous maize: 1 family; Maize rotated with cowpea: 2 families; Maize rotated with pigeon pea: 2 families. More families means a more varied sequence; on its own it does not measure soil health.
* **Water-use evidence.** Continuous maize: indicative water use is documented for every crop; Maize rotated with cowpea: no verified water use for cowpea; Maize rotated with pigeon pea: no verified water use for pigeon pea. Where evidence is missing the comparison is incomplete, not favourable.
* **Legumes and pest management.** Continuous maize: no legume; Maize rotated with cowpea: cowpea; Maize rotated with pigeon pea: pigeon pea. Past study results, not predictions: a review abstract reports higher average cereal yields after grain legumes in sub-Saharan Africa, with large variation and weaker effects after cowpea than after soybean or groundnut. At Machakos, maize after cowpea yielded about 17 % more than continuous maize, maize after pigeon pea only marginally more, and both legumes were affected by pests and diseases.
* **What is the same.** Every strategy contains maize; its weather comparisons are identical across strategies. The strategies differ in what is grown in the other slots.

### With the hypothetical demonstration soil

The same comparison with `demonstration_soil_profile()`: invented values (pH 6.5, loam, well drained) that describe no real field.

| Strategy | Indicator | Result |
| --- | --- | --- |
| Continuous maize | Soil pH against documented ranges | Maize: soil pH 6.5 (hypothetical demonstration soil) is inside the tolerated range of 4.3 to 8.7. |
| Continuous maize | Water held in the root zone | Maize: the root zone (1 to 1.7 m) could hold about 130 to 306 mm of plant-available water. Hypothetical demonstration soil. |
| Continuous maize | Water the crop can use before stress | Maize: about 71.5 to 168.3 mm of that water can be used before stress begins (depletion fraction 0.55). Hypothetical demonstration soil. |
| Maize rotated with cowpea | Soil pH against documented ranges | Maize: soil pH 6.5 (hypothetical demonstration soil) is inside the tolerated range of 4.3 to 8.7. |
| Maize rotated with cowpea | Water held in the root zone | Maize: the root zone (1 to 1.7 m) could hold about 130 to 306 mm of plant-available water. Hypothetical demonstration soil. |
| Maize rotated with cowpea | Water the crop can use before stress | Maize: about 71.5 to 168.3 mm of that water can be used before stress begins (depletion fraction 0.55). Hypothetical demonstration soil. |
| Maize rotated with cowpea | Soil pH against documented ranges | Cowpea: not available. No documented pH range is held for cowpea. |
| Maize rotated with cowpea | Water held in the root zone | Cowpea: the root zone (0.6 to 1 m) could hold about 78 to 180 mm of plant-available water. Hypothetical demonstration soil. |
| Maize rotated with cowpea | Water the crop can use before stress | Cowpea: about 35.1 to 81 mm of that water can be used before stress begins (depletion fraction 0.45). Hypothetical demonstration soil. |
| Maize rotated with pigeon pea | Soil pH against documented ranges | Maize: soil pH 6.5 (hypothetical demonstration soil) is inside the tolerated range of 4.3 to 8.7. |
| Maize rotated with pigeon pea | Water held in the root zone | Maize: the root zone (1 to 1.7 m) could hold about 130 to 306 mm of plant-available water. Hypothetical demonstration soil. |
| Maize rotated with pigeon pea | Water the crop can use before stress | Maize: about 71.5 to 168.3 mm of that water can be used before stress begins (depletion fraction 0.55). Hypothetical demonstration soil. |
| Maize rotated with pigeon pea | Soil pH against documented ranges | Pigeon pea: soil pH 6.5 (hypothetical demonstration soil) is inside the optimal range of 5 to 7. |
| Maize rotated with pigeon pea | Water held in the root zone | Pigeon pea: the root zone (2 m) could hold about 260 to 360 mm of plant-available water. Hypothetical demonstration soil. |
| Maize rotated with pigeon pea | Water the crop can use before stress | Pigeon pea: not available. No documented depletion fraction is held for pigeon pea. |
