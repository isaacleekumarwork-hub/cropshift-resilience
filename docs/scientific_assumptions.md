# Scientific assumptions and limits

This document records the positions the project has taken on what it will and
will not claim, the assumptions built into the data contracts (A1) and the data
layer (A2), and the questions later phases must answer before any agronomic
number reaches a user.

As of phase A3 the project retrieves, checks and describes NASA environmental
data, and holds a cited knowledge base of crop, soil and rotation facts. It
still performs no agronomic calculation: no crop is compared with the data.

## What is what in the current system

Everything the app shows falls into one of four groups, and they are never
mixed.

| Group | What it contains today | How it is labelled |
| --- | --- | --- |
| **1. NASA-provided environmental information** | Daily temperature, rainfall, sunshine and humidity from NASA POWER. Temperature, rainfall and humidity are *reanalysis*: a weather model constrained by observations. Sunshine is a *satellite-based estimate*. None of it is a direct measurement at the site. | By kind of evidence, with source, version and retrieval date |
| **2. Derived descriptive statistics** | Completeness counts; lowest, mean and highest values; monthly rainfall totals; monthly means; the average of each calendar month. Plain arithmetic on group 1. | "Descriptive only", with the method stated |
| **3. Assumptions** | That a point stands for its grid cell; that days are UTC days; the screening and completeness thresholds; the 180-day latency window; which months count as reported. The pilot site's farming background is uncited context. | Listed below and in `data_layer.md` |
| **4. Descriptive indicators (A4)** | Season rainfall totals and dry, typical and wet classes; frost days; rainfall against indicative crop water use; temperature against documented ranges; soil pH and root-zone water from user soil inputs; plant families and repetition in a sequence. Descriptions and comparisons only: no water balance, crop model or score. | Labelled derived; each with status, confidence, conditions and a six-part explanation (`rotation_comparison_methodology.md`) |
| **5. Agronomic knowledge (A3)** | Crop characteristics, soil reference values and rotation relationships read from published sources. Each is a statement by its source, about a species in general. | By source, locator and confidence; gaps listed as not established |

## Positions

1. **Exploration, not prescription.** CropShift compares options and shows
   tradeoffs. It does not tell a farmer what to plant.
2. **History, not forecast.** Scenarios are real past seasons. They show the
   range a farm has experienced, not what will happen next.
3. **No yield prediction.** Yield depends on variety, management, pests,
   nutrients and timing that this tool does not know.
4. **No input prescriptions.** No fertiliser, pesticide or irrigation amounts.
5. **Area, not field.** The weather data describes a grid cell tens of
   kilometres wide.
6. **Evidence or silence.** A crop characteristic without a published source is
   reported as a gap. It is never estimated to fill a table.
7. **Local review always.** Every result is marked as needing review by the
   farmer or a local expert.

## Kinds of evidence

The interface will show which of these each value is.

| Kind | Meaning | Example | Trust note |
| --- | --- | --- | --- |
| Satellite retrieval | Estimated from satellite measurements | GPM IMERG rainfall | An estimate with known errors, not a direct measurement |
| Reanalysis | A weather model constrained by observations | MERRA-2 temperature | Consistent and gap-free, but smoothed over a large area |
| Ground measurement | Measured at a station or in the field | A rain gauge | Accurate at the point, may not represent the area |
| Gridded map product | Interpolated or predicted map | A soil property map | Quality varies by location |
| User reported | Supplied by the farmer | Soil texture class | As reliable as the user's knowledge |
| Literature value | A published reference value | A crop's rooting depth | Typical, not specific to this variety or field |
| Derived | Calculated by a documented formula | Reference evapotranspiration | Inherits the errors of its inputs |
| Modeled | Output of CropShift's calculations | A water-stress indicator | The least certain; always shown with its method |
| Assumed | A default used when nothing better exists | A default soil depth | Stated openly wherever it is used |

## Assumptions built into the contracts

| # | Assumption | Consequence | Where enforced |
| --- | --- | --- | --- |
| C1 | Each variable has one canonical unit | Conversions happen once at ingestion and are recorded | Variable registry |
| C2 | Hard limits reject only the physically impossible | Unusual but possible values pass; plausibility screening is A2's job | Variable registry |
| C3 | Days are defined in UTC for all sources | Daily totals may differ slightly from local-day totals | `TimeStandard`, `ObservationSeries` |
| C4 | A point request stands for the grid cell that contains it | Values are area averages | `ProvenanceRecord.spatial_resolution` |
| C5 | Sand, silt and clay may sum to 100 % within 2 points | Allows for rounding in sources | `SoilInformation` |
| C6 | Field capacity exceeds the wilting point | Inconsistent soil entries are rejected | `SoilInformation` |
| C7 | A rotation is an ordered, repeating cycle with at least one crop | Fallow is allowed; a monoculture is a valid baseline | `CropRotation` |
| C8 | Dates up to one day ahead are tolerated | Avoids false errors across time zones | `EnvironmentalObservation`, `HistoricalScenario` |
| C9 | Priority weights are relative | They are rescaled to sum to 1 before use | `FarmerPriorityProfile` |

## Assumptions built into the data layer (A2)

| # | Assumption | Consequence | Where set |
| --- | --- | --- | --- |
| D1 | NASA's fill value in the response header marks missing data | Those days become explicit gaps | `data_validation.classify_value` |
| D2 | A trailing gap within 180 days of retrieval is data that has not arrived yet | Labelled "not yet available" rather than "missing at source" | `LATENCY_WINDOW_DAYS` |
| D3 | Values outside wide screening ranges are unusual but possible | Kept and flagged suspect, not removed | `PLAUSIBLE_RANGES` |
| D4 | A daily minimum above the mean, or a mean above the maximum, signals a problem | All three values that day are flagged suspect | `TEMPERATURE_ORDER_TOLERANCE` |
| D5 | A dataset with every variable at least 90 % complete is usable | Below that it is marked not accepted | `NASA_MIN_COMPLETENESS_PERCENT` |
| D6 | A monthly total needs every day of the month | A month with any gap has no reported rainfall total | `MONTHLY_TOTAL_MIN_COMPLETENESS_PERCENT` |
| D7 | A monthly mean is meaningful with at least 80 % of its days | Below that the month is not reported | `MONTHLY_MEAN_MIN_COMPLETENESS_PERCENT` |
| D8 | 2001 to 2025 is the reference period for the pilot site | "Typical", "dry" and "wet" will be relative to these 25 years | `pilot_sites.KATUMANI` |
| D9 | Finalised historical values do not change | Cached and bundled responses stay valid; the live test compares against a recording | Cache lifetime; `test_live_power.py` |

D2 to D7 are this project's own choices. They are stated openly, can be changed
in one place, and have not been validated against an agronomic standard.
Climate services commonly apply rules of this kind to monthly statistics;
aligning D6 and D7 with a published standard is a task for phase A8.

## Assumptions built into the knowledge base (A3)

| # | Assumption | Consequence | Where recorded |
| --- | --- | --- | --- |
| K1 | The FAO rows "Maize, Field (grain)", "Sorghum - grain" and "Beans, dry and Pulses" describe the crops a smallholder grows | Their values are used for maize, sorghum and common bean | Each crop's `assumptions` |
| K2 | The shared FAO row "Green Gram and Cowpeas" may stand for cowpea and for mung bean | Both crops carry the same coefficients, marked as shared | Each crop's `assumptions`; confidence notes |
| K3 | "Green gram" in the FAO handbook is mung bean | Supported: the Feedipedia datasheet lists green gram as a common name of *Vigna radiata* | Mung bean identity evidence |
| K4 | Maize is an annual | Inferred from its documented growing period; no source read states it | `life_cycle_basis`, labelled "inferred" |
| K5 | Group values for the initial crop coefficient (0.3 for cereals, 0.4 for legumes) apply to each member | Marked context-dependent; the source calls them approximations | Requirement limitations |
| K6 | The silty clay field-capacity figure printed "0-30" means 0.30 | Row marked provisional | Soil reference note |
| K7 | The pilot site lies in the "marginal bimodal rainfall southeastern" zone FAO describes | The seasonal timing cited for that zone is applied to the site | `PilotSite.context_assumptions` |
| K8 | A trial at the Machakos ICRAF station in 1989 to 1996 is relevant to the Katumani area today | Its findings are held as site-specific evidence, not predictions | `PilotSite.context_assumptions`; relationship scope |

None of these is hidden in a number. Each can be found in the data files.

### What the knowledge base deliberately does not assume

* That a legume always leaves nitrogen for the next crop.
* That legumes raise soil organic matter.
* That crops of the same family must be kept apart.
* That a crop's published temperature range is a hard limit.
* That rainfall equals the water available to a crop.
* That any value applies to a particular variety, farm or year.

## Limitations of the data layer

What the NASA data can establish, and what it cannot.

| Topic | Limitation | What follows |
| --- | --- | --- |
| **Grid cell versus farm** | Weather values are averages over a cell of ½° by ⅝° (roughly 55 km by 70 km near the equator) at the cell's average elevation; solar over 1°. The pilot cell averages 1,328 m, while land around Machakos ranges over hundreds of metres. | The data describes regional conditions. A farm on a slope, in a valley or at a different elevation can be warmer, cooler, wetter or drier. Never described as farm measurements. |
| **Reanalysis is modelled** | MERRA-2 is a weather model constrained by observations. Where ground stations are sparse, as in much of East Africa, the model has less to constrain it. Its precipitation is bias-corrected, but remains an estimate. | Rainfall amounts, and especially individual storms, can differ from what a local gauge recorded. |
| **Extremes are smoothed** | Averaging over a large cell lowers peaks. The highest daily rainfall in the pilot record is 50.6 mm; a single gauge in the same area would be expected to record heavier days. | Unsuitable for judging local flood or erosion events from single days. |
| **Historical, not future** | The record covers 2001 to 2025. | It shows the range experienced, not what will happen. A warming or drying trend would make that range an optimistic guide. No projection is made. |
| **Temporal resolution** | Daily values on UTC days. At the pilot site a UTC day runs from 03:00 to 03:00 local time. | Daily totals differ slightly from local-day totals. Sub-daily intensity, which drives erosion, is not available. |
| **Missing data** | The pilot record has no gaps. That is a property of reanalysis, which is gap-free by construction, and not evidence of accuracy. | Completeness must not be read as quality of measurement. |
| **Source-specific uncertainty** | NASA publishes validation of POWER against ground stations, but this project has not compared the pilot data with any local station. | The size of the error at the pilot site is unknown to this project. |
| **One rainfall source** | Only MERRA-2 rainfall is used so far. | There is no second opinion yet. Adding GPM IMERG would show how far two NASA estimates disagree. |
| **Recent months** | NASA fills the most recent months from near-real-time systems and replaces them later. | The pilot period ends in 2025 to avoid them. Requests that include them carry a caveat. |
| **No local soil measurements** | The data layer contains no soil information at all. | Soil comes from the user in a later phase; without it, water balance cannot be assessed. |
| **No crop-specific validation** | Nothing here has been checked against crop performance, yields or farmer experience. | The data layer makes no statement about any crop. |

Passing validation means a response is well formed, physically possible and
complete. It does not mean the values are accurate for a particular farm.

### Provisional variable definitions

The registry in `src/models.py` declares the environmental and soil variables
the recommended data sources supply. Nine definitions are marked
**provisional**: `surface_soil_moisture`, `reference_evapotranspiration` and
the seven crop parameters. They exist so the contracts can be tested; the final
list of crop parameters, with units and limits, is fixed in A3 alongside its
citations. Indicator variables are not declared at all until A4.

## Known limitations of the planned data

| Limitation | Effect | How it will be handled |
| --- | --- | --- |
| Weather grid of about 50 km | Local rainfall, slope and microclimate are invisible | Stated on every result; lowers confidence |
| MERRA-2 rainfall is model-based | Misses or smooths local storms | Compared against IMERG; disagreement is shown |
| IMERG has a delay of weeks to months | Recent seasons may be incomplete | Labelled "not yet available" |
| Soil wetness from POWER is modelled | Not a measurement of the user's soil | Labelled as modelled |
| Record of about 25 years for IMERG, 45 for MERRA-2 | "Dry" and "wet" are relative to that record only | Baseline period stated with each scenario |
| Past conditions may not represent the future climate | A warming trend can make the historical range optimistic | Stated as a limitation; no future projection is made |
| Literature values are typical values | A local variety may differ | Marked for local review |

## Open scientific questions

Each must be answered, with a citation where a published method exists, before
the corresponding phase ships.

| # | Question | Phase |
| --- | --- | --- |
| Q1 | How is a growing season defined for each pilot region? | **Answered for analysis in A4, not for sowing.** The FAO GIEWS windows (March to May, October to December) are used as fixed calendar analysis windows. No rule for the onset and end of a season in a given year was adopted, sowing dates remain unknown, and every result says so. |
| Q2 | How are seasons classed as dry, typical or wet (which variable, which thresholds)? | **Answered in A4.** NASA rainfall total over the window; terciles of the 25 complete seasons (8 dry, 9 typical, 8 wet), ties ordered by year; a project choice of method, documented in `historical_scenarios.md`. |
| Q3 | Which reference evapotranspiration method is used, given the variables retrieved? | **Deferred by the A4 brief.** No reference evapotranspiration is calculated; the four mappings that need it stay unavailable. |
| Q4 | Which published sources supply crop characteristics, and are they valid for each pilot region? | **Answered in A3**, with limits: FAO handbooks and Feedipedia datasheets supply general values; regional validity is established for three crops only, from one experiment. |
| Q5 | Which reference supplies typical soil water properties by texture class? | **Answered in A3:** FAO Irrigation and Drainage Paper 56, Table 19, for nine of the twelve classes. |
| Q6 | Which indicators can be calculated defensibly from these inputs, and what does each one not capture? | **Answered in A4:** eleven descriptive indicators, each with what it does not establish (`rotation_comparison_methodology.md`). |
| Q7 | How is confidence assigned from data completeness, source disagreement and missing parameters? | **Answered in A4** by a stated rule (`uncertainty.md`). Source disagreement does not arise yet: there is one rainfall source. |
| Q8 | How are priorities with no data (forage value, market suitability) presented without implying a score? | **Answered in A4:** they are listed with "Nothing is estimated" and what would be needed; no weights exist anywhere. Presentation in A5. |

### Assumptions added in A4

| # | Assumption | Where |
| --- | --- | --- |
| S1 | The FAO GIEWS calendar windows stand in for the growing seasons. Sowing dates are unknown. | `pilot_configuration.md` |
| S2 | When the study does not say which crop was grown in which season, each crop is shown against both windows. | `pilot_configuration.md` |
| S3 | Dry, typical and wet are terciles of 25 seasons; a project choice, not a cited standard. | `historical_scenarios.md` |
| S4 | ETCCDI index definitions, made for station records over a year, are applied within a window to a grid-cell average. | `historical_scenarios.md` |
| S5 | NASA's daily mean temperature is compared with source ranges whose temperature measure is unstated. | `rotation_comparison_methodology.md` |
| S6 | Soil values describe the whole root zone; published rooting depths are not limited by soil depth; the depletion fraction is unadjusted. | `soil_input_mapping.md` |
| S7 | Continuous maize is treated as the current practice because it was the experiment's baseline. | `pilot_configuration.md` |
| S8 | The confidence rule in `uncertainty.md` is this project's own. | `uncertainty.md` |

## What would falsify the approach

It is worth stating in advance what would show the tool to be misleading:

* If the two NASA rainfall estimates disagree so much for a region that the
  dry, typical and wet classes change depending on which is used, the scenario
  labels are not robust there and the region should not be supported.
* If the indicators rank rotations differently from well-documented local
  experience, the indicators need revision before the tool is shown to farmers.
* If results change materially when an assumed value is varied within its
  plausible range, that result must be reported as low confidence.

Checks of this kind belong to phase A8.
