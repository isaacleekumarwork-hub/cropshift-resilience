# Minimum viable product specification

**Status: provisional.** Written in phase A1 on 14 November 2026 and awaiting
the participant's approval. Items marked *open* need a decision.

## Purpose

Let a farmer, or someone advising a farmer, compare their current crop rotation
with alternatives and see how each might hold up in dry, typical and wet
seasons taken from the historical record for their area, with the evidence,
tradeoffs and uncertainty in plain view.

## What the MVP is not

* Not a yield predictor.
* Not a source of fertiliser, pesticide or irrigation prescriptions.
* Not a weather forecast. Scenarios are real past seasons.
* Not field-specific. NASA weather data describes an area of roughly 50 km.
* Not a replacement for the farmer's judgment or local agricultural advice.

## Two kinds of information, always kept apart

| Kind | Examples | How it is shown |
| --- | --- | --- |
| **Environmental data** retrieved from NASA | Temperature, rainfall, sunshine, soil wetness | Labelled with its source and whether it is a satellite estimate or a model reanalysis |
| **Agronomic indicators** calculated by CropShift | Crop water demand compared with rainfall, share of the year the soil is bare | Labelled "modelled", with the method, the assumptions and an uncertainty statement |

Crop characteristics come from cited publications. Soil information comes from
the user. Anything assumed is labelled as an assumption.

## User journey and acceptance criteria

Each capability is done only when every criterion is met and covered by a test
or a documented manual check.

### 1. Select a supported pilot region

* The user chooses from a short list of supported regions.
* Each region shows its name, coordinates, typical cropping system and why it
  was chosen.
* A location outside the supported regions is not offered.

### 2. View available NASA environmental data

* For the selected region, the app shows daily series for temperature,
  rainfall, sunshine, humidity, wind and soil wetness.
* Every chart names its source, its unit, the period covered and the date the
  data was retrieved.
* Missing days appear as visible gaps with the reason, and are never drawn as
  zero or interpolated silently.
* Reanalysis and satellite-based values are labelled differently.
* In offline demo mode the same screen works from bundled data and says so.

### 3. Provide or select soil information

* The user picks a soil texture class and may add depth, organic matter and
  pH.
* Each value records whether the user supplied it or whether it is a cited
  reference value for that texture class.
* Unknown properties stay unknown and are listed as information gaps.
* Impossible entries (for example pH 15, or sand, silt and clay not adding up
  to 100 %) are refused with a clear message.

### 4. Choose crops and candidate rotations

* The user identifies their **current rotation** and at least **two
  alternatives** from the options supported for the region.
* Each crop shows its cited characteristics and the source of each one.
* A characteristic with no published source is shown as "not documented",
  never filled with an estimate.

### 5. Compare multi-season scenarios

* The comparison covers at least three rotations including the current one,
  across dry, typical and wet historical scenarios.
* Results are identical every time for the same inputs.
* The comparison works with OpenAI and Manus switched off.

### 6. Inspect environmental and agronomic indicators

* Each indicator shows its value, unit, how it was calculated and what it does
  and does not mean.
* Indicators are labelled as modelled. Environmental data is labelled by
  source. The two are visually distinct.

### 7. Explore dry, typical and wet historical conditions

* Each scenario names the actual years or seasons it represents and how they
  rank in the record.
* The method used to classify seasons is stated in one or two sentences.
* The word "forecast" does not appear except to say that this is not one.

### 8. Understand tradeoffs and uncertainty

* The user sets how much each priority matters to them, and the comparison
  reflects those weights.
* No rotation is declared "best" without showing what it gives up.
* For each rotation the app states why it is being considered, the supporting
  evidence, possible benefits, information gaps and risks that need local
  review.
* Every result carries a confidence level together with the reason for it.
* Priorities the tool has no data for (for example market suitability) are
  shown as "needs local information", not scored.

### 9. Review sources and assumptions

* One screen lists every data source with version, citation and link, and
  every assumption the calculations rely on.
* A short glossary explains terms such as evapotranspiration and reanalysis.

### 10. Export a comparison summary

* The user can download a summary containing the rotations, scenarios,
  indicators, tradeoffs, uncertainty, sources and the disclaimer.
* The export is produced without any AI service.

## Scope decisions

| Decision | MVP choice | Status |
| --- | --- | --- |
| NASA data | NASA POWER (MERRA-2 and CERES) plus GPM IMERG rainfall, both through the POWER API | Recommended, see `data_sources.md` |
| Time step | Daily data, summarised by growing season | Proposed |
| Number of pilot regions | Two or three | *Open* |
| Crops per region | Four to six, each with cited characteristics | *Open*, set in A3 |
| Soil input | User-selected texture class with optional details | Proposed |
| Languages | English | Fixed by submission rules |
| AI explanations | Optional, off by default, never part of the calculation | Fixed |

## Pilot regions

**Chosen in A2, awaiting approval:** the Katumani area of Machakos County,
Kenya (latitude -1.58, longitude 37.24), a semi-arid smallholder site matching
the second candidate below. Its NASA data for 2001 to 2025 has been retrieved
and verified. The choice is easy to change: the data layer accepts any
coordinates, and the site is defined in one place (`src/pilot_sites.py`).

The candidates as listed in A1 follow. A region is supported only if phase A3
finds enough published evidence for its crops.

| Candidate | Why it is a candidate |
| --- | --- |
| A rainfed grain region in the central United States | The official challenge resources include detailed United States soil and cropland data that could strengthen validation. |
| A semi-arid smallholder region in East Africa | Rainfall variability is the main risk, so the dry, typical and wet comparison is most meaningful there. |
| A rainfed region in Southeast Asia | Relevant to the Singapore Local Event and to the region's food security. |

## Priorities the farmer can weigh

The first six are named in the official challenge text. The last two are
CropShift additions.

| Priority | Can the MVP inform it? |
| --- | --- |
| Water use | Yes, from crop characteristics and NASA weather data |
| Nitrogen-fixing potential | Yes, from cited crop characteristics |
| Erosion reduction | Partly, from how long the soil is covered and rainfall intensity |
| Organic matter improvement | Partly, from cited crop characteristics; long-term change is not modelled |
| Forage value | No data source in the MVP; shown as needing local information |
| Market suitability | No data source in the MVP; shown as needing local information |
| Pest-cycle disruption | Partly, from the botanical families in the rotation |
| Resilience across dry and wet seasons | Yes, this is the core comparison |

## Definition of done for the MVP

* All ten capabilities meet their acceptance criteria.
* The automated tests pass.
* The app runs end to end in offline demo mode.
* Every number on screen can be traced to a source or a documented method.
* The submission requirements in `requirements_matrix.md` section A are met.
