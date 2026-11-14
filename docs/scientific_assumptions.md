# Scientific assumptions and limits

Phase A1 implements no scientific calculation. This document records the
assumptions already built into the data contracts, the positions the project
has taken on what it will and will not claim, and the questions later phases
must answer before any number reaches a user.

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
| Q1 | How is a growing season defined for each pilot region? | A2, A3 |
| Q2 | How are seasons classed as dry, typical or wet (which variable, which thresholds, which baseline years)? | A2 |
| Q3 | Which reference evapotranspiration method is used, given the variables POWER supplies? | A2 |
| Q4 | Which published sources supply crop characteristics, and are they valid for each pilot region? | A3 |
| Q5 | Which reference supplies typical soil water properties by texture class? | A3 |
| Q6 | Which indicators can be calculated defensibly from these inputs, and what does each one not capture? | A4 |
| Q7 | How is confidence assigned from data completeness, source disagreement and missing parameters? | A4 |
| Q8 | How are priorities with no data (forage value, market suitability) presented without implying a score? | A4, A5 |

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
