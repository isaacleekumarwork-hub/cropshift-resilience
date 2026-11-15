# NASA data sources

First assessed in phase A1 and updated in phase A2 on 14 November 2026, when
the first source was integrated and verified with a live retrieval.

## Agronomic and soil sources (phase A3)

The crop, soil and rotation knowledge added in A3 comes from thirteen sources,
none of them NASA products. Each is described, with how it was checked and its
limits, in [`evidence_registry.md`](evidence_registry.md).

| Source | Used for |
| --- | --- |
| FAO Irrigation and Drainage Paper 56 (Allen and others, 1998) | Crop coefficients, plant height, rooting depth, depletion fraction, yield response, growth-stage examples, salt tolerance, soil-water characteristics by texture class |
| FAO Irrigation Water Management Training Manual 3 (Brouwer and Heibloem, 1986) | Indicative growing periods, seasonal crop water needs, drought-sensitivity classes |
| Six Feedipedia datasheets (INRAE, CIRAD, AFZ and FAO; 2015 to 2017) | Scientific names and families; temperature, annual rainfall and soil pH ranges; drainage, waterlogging, drought and frost statements; nitrogen fixation |
| Rao and Mathuva (2000), *Agriculture, Ecosystems & Environment* | The legume and maize cropping-systems experiment at Machakos (abstract read) |
| Franke and others (2018), *Agriculture, Ecosystems & Environment* | Systematic review of grain-legume rotations in sub-Saharan Africa (abstract read) |
| FAO Conservation Agriculture pages on species diversification and soil cover | General principles of rotation and soil cover |
| FAO GIEWS Country Brief for Kenya (reference date 4 May 2026) | Timing of the long and short rains, cited by the pilot site description |

Not accessible on 14 November 2026: **FAO EcoCrop** (redirected to a sign-in)
and the **FAO Land and Water crop information pages** (page not found). No
unofficial copy of either was used.

How crop characteristics line up with the NASA variables below is set out in
the "Interfaces for phase A4" section of
[`agronomic_knowledge.md`](agronomic_knowledge.md).

## Status after phase A2

| Source | Status |
| --- | --- |
| **NASA POWER Daily API** (MERRA-2 meteorology, CERES solar) | **Integrated, tested and verified live.** Six parameters. |
| GPM IMERG rainfall (through NASA POWER) | Not integrated. Held back deliberately; see below. |
| SMAP soil moisture | Not integrated. Stretch goal. |

How to use the integrated source, its data dictionary and its quality rules
are in [`data_layer.md`](data_layer.md). Licensing and attribution are in
[`compliance.md`](compliance.md).

### What was verified in A2

| Fact | Evidence |
| --- | --- |
| Endpoint and request format | Official documentation, and a live request returning HTTP 200 |
| Parameter names and units for the agroclimatology community: `T2M`, `T2M_MAX`, `T2M_MIN` in C; `PRECTOTCORR` in mm/day; `ALLSKY_SFC_SW_DWN` in MJ/m^2/day; `RH2M` in % | Live parameter catalogue and the response's own metadata. The pipeline refuses any other unit. |
| Meteorology comes from MERRA-2 on a ½° latitude by ⅝° longitude grid, from 1 January 1981 | NASA POWER methodology documentation |
| Solar comes from GEWEX SRB (1984 to 2000), CERES SYN1deg Edition 4.2 (from 1 January 2001) and FLASHFlux (most recent months), on a 1° grid | NASA POWER methodology documentation |
| The most recent months come from GEOS-IT and FLASHFlux and are later replaced; NASA recommends ending trend analysis two months before the present | NASA POWER methodology documentation |
| Values are grid-cell averages at the cell's average elevation | NASA POWER methodology documentation |
| Daily maximum and minimum temperature come from the day's 24 hourly values | NASA POWER methodology documentation |
| At most 20 parameters per point request; UTC or local solar time, defaulting to local solar time | Official API documentation |
| NASA POWER asks for one request per grid cell and may block repeated requests | Official API documentation |

### Live retrieval of the pilot dataset

| | |
| --- | --- |
| When | 14 November 2026, 02:57 UTC |
| Request | `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN%2CPRECTOTCORR%2CRH2M%2CT2M%2CT2M_MAX%2CT2M_MIN&community=AG&longitude=37.2400&latitude=-1.5800&start=20010101&end=20251231&format=JSON&time-standard=UTC` |
| Result | HTTP 200 on the first attempt, in about 1.2 seconds |
| Service | POWER Daily API v2.10.3; upstream products MERRA2 and SYN1DEG |
| Coverage | 1 January 2001 to 31 December 2025: 9,131 days, six parameters, 54,786 values |
| Completeness | 100 % for every parameter; no fill values, no warnings |
| Grid-cell elevation reported | 1,327.62 m |
| Response fingerprint (SHA-256) | `1c2ed230e2661199ac278e4ac68b179c4b5750284091c094745de4a920e0edaf` |

| Variable | Lowest | Mean | Highest |
| --- | --- | --- | --- |
| Precipitation (mm/day) | 0.00 | 1.78 | 50.56 |
| Mean temperature (degC) | 16.69 | 21.20 | 26.20 |
| Daily maximum temperature (degC) | 20.84 | 28.73 | 35.24 |
| Daily minimum temperature (degC) | 9.98 | 15.44 | 19.43 |
| Solar irradiance (MJ/m^2/day) | 4.82 | 20.31 | 29.08 |
| Relative humidity (%) | 31.27 | 68.10 | 91.82 |

The record averages about 651 mm of rain a year, with two wetter periods
centred on April (121 mm on average) and November (116 mm), and a dry stretch
from June to September. These are descriptive statistics of NASA's gridded
estimate, not measurements at Katumani.

### Why GPM IMERG was not added in A2

A1 recommended adding IMERG rainfall as a second opinion, and confirmed it is
available through the same API. The A2 brief asked for one reliable source to
be working and tested before any other is introduced, so IMERG was left out.
The pipeline is ready for it: it would be one more row in the parameter table
in `src/nasa_client.py`, and every request already uses UTC, which IMERG
requires. Adding it needs a decision, because it changes how uncertainty in
rainfall is presented.

---

The rest of this document is the A1 candidate evaluation, kept for reference.
Facts marked **[recall]** below that concern NASA POWER have since been
confirmed as listed above.

## How to read this document

Every fact is marked with how we know it:

* **[probe]** confirmed by a small live request made during this assessment
  (logged in the last section)
* **[official]** stated on the official challenge Resources page
* **[search]** found in a web search result on 14 Nov 2026, not opened at the
  primary source
* **[recall]** general knowledge of the dataset that was **not** re-checked
  today and must be confirmed in A2 before it is shown to users

## Recommendation

**Use NASA POWER as the single access point, drawing two NASA data streams
from it:**

1. **MERRA-2 meteorology and CERES solar radiation**, for temperature,
   humidity, wind, sunshine, precipitation and modelled soil wetness, with a
   record long enough (1981 onward) to define dry, typical and wet seasons.
2. **GPM IMERG precipitation**, a satellite-based rainfall estimate, as an
   independent second opinion on rainfall.

Both arrive through one free API that needs no account. This is the smallest
combination that is still credible, because it gives a long climate record
*and* a satellite-based check on the variable that matters most for rotation
choices: water.

**SMAP is deferred to a stretch goal.** It is the only candidate that measures
soil moisture from space, but its record starts in 2015, too short to define a
climatology, and it needs an Earthdata account and file-based processing.

## Candidate evaluation

| Criterion | NASA POWER (MERRA-2 + CERES) | GPM IMERG | SMAP |
| --- | --- | --- | --- |
| What it is | Reanalysis: a weather model constrained by observations. Solar radiation from satellite. | Satellite-based precipitation estimate combining many sensors. | Satellite microwave soil moisture. Level 4 adds a model for root-zone moisture. |
| Scientific relevance | High. Temperature, heat and frost exposure, rainfall, evaporative demand and soil wetness are the core drivers of crop water stress. | High. Rainfall reliability and extreme rain are central to the challenge. | High. Direct soil moisture information. |
| Geographic coverage | Global **[recall]** | Global **[recall]**; quality is lower at high latitudes | Global land **[official]** |
| Historical coverage | Meteorology from 1 Jan 1981 **[probe]**; solar from 1 Jan 1984 **[probe]** | Data returned for Jan 1999 and Jun 2000 through POWER **[probe]**; NASA describes the record as Jan 1998 to present **[search]** | From 31 March 2015 **[recall]** |
| Spatial resolution | 0.5° x 0.625° meteorology, 1° x 1° solar **[recall]** | 0.1° (about 10 km) at the source **[search]**; the grid served through POWER is unconfirmed | 9 km (Level 4, enhanced Level 3), 36 km (Level 3) **[recall]** |
| Temporal resolution | Daily (also hourly and monthly) **[probe]** | Daily through POWER **[probe]**; half-hourly at the source **[search]** | Every 2 to 3 days (Level 3) **[official]**; 3-hourly (Level 4) **[search]** |
| Access | Open REST API, JSON, no account **[probe]** | Through POWER: no account **[probe]**. Directly from the archive: Earthdata account **[recall]** | Earthdata account and HDF5 files **[recall]** |
| Latency | About 2 to 4 days **[probe]** | Through POWER: more than 3 weeks **[probe]**. At the source, the final version takes at least 3.5 months **[search]** | About 2.5 days reported for an earlier Level 4 version **[search]** |
| Licence | NASA open data; cite the POWER project **[recall]** | Open; CC BY 4.0 shown on a mirror record **[search]** | NASA open data **[recall]** |
| Effort for the MVP | Low | Low (same API) | High |
| Suitability for the MVP | **Core** | **Core** | Stretch |

## Verified behaviour that A2 must respect

These were learned from live probes and shape the ingestion design.

1. **IMERG needs UTC.** Requests in POWER's default local solar time return
   only fill values for IMERG, with the message "The IMERG Source Data is not
   available at the Local Solar Time (LST) standard." Adding
   `time-standard=UTC` returns data.
2. **The time standard changes daily totals.** For the same place and dates,
   MERRA-2 precipitation differed between local solar time and UTC (for
   example 29.94 versus 25.84 mm on one day). A2 must request **every**
   variable in UTC so that days line up. `ObservationSeries` already refuses to
   mix time standards.
3. **The fill value is -999.** The data contracts reject it as a number, so
   ingestion must convert it to an explicit missing status.
4. **Solar radiation starts later than weather.** A request for 1981 returned
   weather values and dropped radiation with an explanatory message. Any
   variable derived from radiation therefore starts in 1984.
5. **Recent days are incomplete.** On 14 Nov 2026, weather was available to
   about 10 to 12 Nov, solar to 9 Nov, and IMERG not at all after at least
   20 Oct. These gaps must be labelled "not yet available", not treated as
   zero.
6. **The two rainfall estimates disagree, sometimes strongly.** On one day in
   the probe, MERRA-2 gave 25.84 mm and IMERG gave 65.53 mm for the same
   location. This is expected: one is a model constrained by observations on a
   roughly 50 km grid, the other a satellite estimate on a roughly 10 km grid.
   CropShift will show this disagreement as a real source of uncertainty
   rather than hide it.
7. **Recent data comes from a different system.** Historical values are
   labelled MERRA2; the most recent weeks are labelled GEOS-IT and FLASHFlux.
   Provenance must record which system supplied each value.

## Variables planned for the MVP

Names on the left are CropShift's registered variables (`src/models.py`).
POWER parameter names and units were confirmed by probe.

| CropShift variable | Unit | POWER parameter | Kind of evidence |
| --- | --- | --- | --- |
| `air_temperature_mean` | degC | `T2M` | Reanalysis |
| `air_temperature_max` | degC | `T2M_MAX` | Reanalysis |
| `air_temperature_min` | degC | `T2M_MIN` | Reanalysis |
| `precipitation` | mm/day | `PRECTOTCORR` | Reanalysis (bias-corrected) |
| `precipitation` | mm/day | `IMERG_PRECTOT` | Satellite retrieval |
| `solar_irradiance` | MJ/m^2/day | `ALLSKY_SFC_SW_DWN` | Satellite-based |
| `relative_humidity` | % | `RH2M` | Reanalysis |
| `wind_speed` | m/s | `WS2M` | Reanalysis |
| `surface_soil_wetness` | fraction | `GWETTOP` | Reanalysis (modelled soil) |
| `root_zone_soil_wetness` | fraction | `GWETROOT` | Reanalysis (modelled soil) |

Both precipitation sources use the same variable and unit, and are told apart
by their provenance, never by a different name.

## Honest labelling

* **MERRA-2 is not an observation.** It is a model that assimilates
  observations. The interface will call it "NASA reanalysis", not "observed".
* **Soil wetness from POWER is modelled**, not measured. It will be labelled
  as such. SMAP would be the satellite-based alternative.
* **IMERG is an estimate** derived from satellite measurements and adjusted
  with rain gauges where they exist. It is not a rain gauge.
* **A grid cell is not a field.** A 50 km cell averages over many farms,
  slopes and soils. Every result will say so.

## Tradeoffs of the recommendation

| We gain | We give up |
| --- | --- |
| One API, no accounts, global coverage, 45 years of record | Field-scale detail: the weather grid is about 50 km |
| A satellite-based rainfall cross-check with no extra infrastructure | Direct satellite soil moisture (SMAP) in the MVP |
| A working offline demo from small cached JSON files | Vegetation and terrain information (MODIS, Landsat, SRTM) in the MVP |
| Time to spend on agronomy, uncertainty and usability | "More datasets" as a talking point |

## Other official resources considered

| Resource | Decision | Reason |
| --- | --- | --- |
| MODIS / VIIRS vegetation indices | Stretch | Would show observed bare periods, but needs an Earthdata account or a separate service. |
| SRTM elevation | Stretch | Slope informs erosion risk; a single static value per location. POWER already returns site elevation. |
| Landsat, ECOSTRESS, GEDI | Not planned | Field-scale imagery needs processing beyond a weekend. |
| GRACE / GRACE-FO | Not planned | Very coarse (hundreds of km); useful for regional water trends only. |
| NLDAS / GLDAS | Not planned | Overlaps with what POWER provides more simply. |
| United States soil and crop datasets (SSURGO, Web Soil Survey, CDL) | Stretch | Excellent quality but cover only the United States. |

## Local soil information

The challenge requires "local soil information" but names no global source.
For the MVP, the user selects or enters soil information (texture class at
minimum), and reference properties for each texture class come from a cited
publication chosen in A3. Automatic soil lookup is a stretch goal. Any value
the user does not supply stays an explicit gap.

## Citations to carry into the submission

The NASA POWER wording below is taken from the official Referencing Guide
(https://power.larc.nasa.gov/docs/referencing/) and replaces the A1 draft. The
pipeline generates both statements for every dataset.

* **NASA POWER:** "The data was obtained from National Aeronautics and Space
  Administration (NASA) Langley Research Center's Prediction Of Worldwide
  Energy Resources (POWER) project funded through the NASA Earth Science
  Division." and "The data was obtained from the POWER Project's Daily v2.10.3
  version on 2026/11/14."
* **MERRA-2:** Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis
  for Research and Applications, Version 2 (MERRA-2). *Journal of Climate*,
  30(14), 5419–5454. https://doi.org/10.1175/JCLI-D-16-0758.1
* **GPM IMERG:** Huffman, G. J., et al. GPM IMERG Final Precipitation L3,
  Version 07. NASA Goddard Earth Sciences Data and Information Services Center.
  https://doi.org/10.5067/GPM/IMERGDF/DAY/07 (which IMERG run POWER serves is
  an open item below)
* **SMAP (if used):** Reichle, R., et al. SMAP L4 Global 3-hourly 9 km
  EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data, Version 8.
  NASA National Snow and Ice Data Center DAAC.
  https://doi.org/10.5067/T5RUATAQREF8

## Open items

| # | Item | Status |
| --- | --- | --- |
| 1 | Which IMERG run and version does POWER serve, and on what grid? | Open. Only matters if IMERG is added. |
| 2 | What is the last date with IMERG data through POWER? | Open. Only matters if IMERG is added. |
| 3 | Confirm POWER's stated spatial resolutions and its usage limits. | **Done in A2.** |
| 4 | Confirm exact citation wording for NASA POWER. | **Done in A2.** MERRA-2 and CERES product citations still to be checked against their own pages. |
| 5 | Decide the baseline period for ranking seasons. | **Done in A2:** 2001 to 2025, see `data_layer.md`. |
| 6 | Requests for different points in the same grid cell are cached separately. | Open. Harmless with one fixed pilot site; to be addressed before users can type arbitrary coordinates (A5). |

## Probe log (phase A1)

All requests were made on 14 Nov 2026 to
`https://power.larc.nasa.gov/api/temporal/daily/point` (API version v2.10.3)
for a single test point (latitude 42.03, longitude -93.62) with `community=AG`
and `format=JSON`. No account or key was used. The responses were inspected
and then discarded: none of the values are stored in this repository.

| # | Request | Result |
| --- | --- | --- |
| 1 | 9 weather, solar and soil-wetness parameters, 1–5 Jul 2024 | HTTP 200, all values present, sources MERRA2 and SYN1DEG, fill value -999, local solar time |
| 2 | Parameter catalogue for the agroclimatology community, daily | HTTP 200, 152 parameters including `IMERG_PRECTOT` |
| 3 | Temperature, precipitation, solar, 1–3 Jan 1981 | HTTP 200, weather present, solar removed with a message that radiation starts 1 Jan 1984 |
| 4 | `IMERG_PRECTOT` without a time standard, 2024 and 2001 | HTTP 200, all fill values, message that IMERG is unavailable in local solar time |
| 5 | Mixed parameters, 1–13 Nov 2026 | HTTP 200, weather to 10 Nov, solar to 9 Nov, sources GEOSIT and FLASHFLUX |
| 6 | `IMERG_PRECTOT` and `PRECTOTCORR` with `time-standard=UTC`, five periods from 1999 to 2026 | HTTP 200, IMERG present for 1999, 2000, 2001 and 2024; all fill for 20 Oct – 13 Nov 2026 |
