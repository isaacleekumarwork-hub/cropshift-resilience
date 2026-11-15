# Historical scenarios (phase A4.4)

Dry, typical and wet past seasons at the pilot site, from the validated NASA POWER record. These describe
seasons that happened between 2001 and 2025. **They are not forecasts.** Code: `src/scenario_engine.py`.

_Generated from the code and data on 15 November 2026 by a script; do not edit by hand._

## Data

* Dataset `4f87119a04095bb2…`, SHA-256 `1c2ed230e2661199…`: NASA POWER Daily API v2.10.3, the bundled pilot response.
* Requested point: latitude -1.58, longitude 37.24; NASA returned the same point, grid-cell elevation 1327.62 m.
* Observation period: 2001-01-01 to 2025-12-31; first and last valid day 2001-01-01 and 2025-12-31.
* Complete calendar years (every day of rainfall valid), verified rather than assumed: **25**.

## Method

1. Daily NASA POWER values are taken between each window's first and last day (UTC days).
2. A season's rainfall total requires 100 % of days valid; temperature summaries require 80 %.
3. Complete seasons of one window ranked by NASA rainfall total, lowest first (ties ordered by year). With n seasons and k = floor(n / 3): the k lowest are dry, the k highest are wet, the rest typical. Terciles are this project's choice, not a cited standard.
4. The representative season of each category is its median-ranked member, a real season.
5. Wet day: at least 1 mm (ETCCDI). Longest dry spell: the longest run of days below 1 mm within the window (ETCCDI CDD, applied to a season).
6. Heavy-rain days: at least 10 mm and 20 mm (ETCCDI R10mm, R20mm). Frost day: daily minimum below 0 °C (ETCCDI FD).
7. Year-to-year variability is the sample standard deviation of seasonal totals divided by their mean.

Thresholds:

* `wet_day_mm`: 1
* `heavy_rain_10mm`: 10
* `heavy_rain_20mm`: 20
* `frost_below_c`: 0
* `season_total_min_completeness_percent`: 100
* `temperature_min_completeness_percent`: 80

## Limitations

* Dry, typical and wet describe past seasons relative to each other at this site, 2001 to 2025. They are not forecasts and say nothing about future seasons.
* Rainfall is NASA POWER's MERRA-2 reanalysis estimate for a grid cell about 55 km by 70 km, not a gauge on a farm. Daily rain-day counts for a grid-cell average can differ from those at a single point.
* A rainfall total is not the water available to a crop: runoff, evaporation, soil storage and irrigation all intervene. No water balance is modelled.
* Season windows are fixed calendar windows. Real rainy seasons start and end on different dates each year.
* The ETCCDI index definitions are for station records over a year; here they are applied within a season window to a reanalysis grid-cell average.

## Long rains: 01 March to 31 May

Window basis: FAO GIEWS: in marginal bimodal-rainfall south-eastern areas the long rains 'typically extend from March to May'.

* Complete seasons classified: 25; excluded: 0.
* Rainfall over the window: mean 248.13 mm, median 209.42 mm, lowest 102.13 mm, highest 556.13 mm; year-to-year variability 38.9 %.
* Boundaries: dry seasons had at most **197.89 mm**; wet seasons had at least **284.39 mm**.
* Representative seasons (median-ranked member of each category): dry `long-rains-2009`, typical `long-rains-2007`, wet `long-rains-2024`.

| Rank | Season | Category | Rain (mm) | Wet days | Longest dry spell (days) | Wettest day (mm) | Days ≥ 20 mm | Mean temp (°C) | Lowest min (°C) | Highest max (°C) | Frost days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Long rains 2019 | dry | 102.1 | 27 | 26 | 14.3 | 0 | 23.3 | 13.2 | 35.1 | 0 |
| 2 | Long rains 2022 | dry | 124.6 | 29 | 17 | 21.7 | 1 | 22.6 | 14.2 | 33.8 | 0 |
| 3 | Long rains 2011 | dry | 157.2 | 46 | 12 | 11.7 | 0 | 22.2 | 14.1 | 33.0 | 0 |
| 4 | Long rains 2009 | dry | 162.4 | 52 | 14 | 6.6 | 0 | 22.2 | 14.6 | 34.3 | 0 |
| 5 | Long rains 2016 | dry | 184.0 | 37 | 19 | 15.6 | 0 | 22.5 | 12.5 | 35.1 | 0 |
| 6 | Long rains 2014 | dry | 184.2 | 45 | 11 | 14.4 | 0 | 21.7 | 12.8 | 31.9 | 0 |
| 7 | Long rains 2004 | dry | 190.5 | 47 | 16 | 30.0 | 1 | 21.9 | 12.4 | 33.5 | 0 |
| 8 | Long rains 2015 | dry | 197.9 | 41 | 19 | 15.0 | 0 | 22.1 | 13.8 | 33.0 | 0 |
| 9 | Long rains 2017 | typical | 201.9 | 39 | 16 | 46.9 | 1 | 22.4 | 14.0 | 34.5 | 0 |
| 10 | Long rains 2008 | typical | 202.4 | 38 | 13 | 15.6 | 0 | 21.4 | 13.8 | 32.8 | 0 |
| 11 | Long rains 2021 | typical | 204.7 | 46 | 15 | 17.3 | 0 | 21.8 | 13.8 | 32.6 | 0 |
| 12 | Long rains 2005 | typical | 207.2 | 49 | 12 | 22.8 | 1 | 22.4 | 14.1 | 34.5 | 0 |
| 13 | Long rains 2007 | typical | 209.4 | 56 | 8 | 11.8 | 0 | 21.9 | 14.3 | 32.8 | 0 |
| 14 | Long rains 2001 | typical | 218.1 | 51 | 8 | 13.1 | 0 | 21.5 | 13.6 | 32.0 | 0 |
| 15 | Long rains 2025 | typical | 245.7 | 53 | 7 | 30.1 | 1 | 22.2 | 12.5 | 33.5 | 0 |
| 16 | Long rains 2010 | typical | 279.8 | 67 | 5 | 14.8 | 0 | 21.7 | 13.7 | 32.0 | 0 |
| 17 | Long rains 2013 | typical | 283.6 | 58 | 15 | 30.7 | 2 | 21.4 | 12.9 | 33.1 | 0 |
| 18 | Long rains 2023 | wet | 284.4 | 46 | 11 | 29.7 | 4 | 21.6 | 13.9 | 33.2 | 0 |
| 19 | Long rains 2012 | wet | 303.1 | 54 | 20 | 37.3 | 1 | 21.6 | 13.9 | 34.5 | 0 |
| 20 | Long rains 2002 | wet | 318.0 | 63 | 12 | 15.0 | 0 | 21.4 | 13.4 | 32.4 | 0 |
| 21 | Long rains 2024 | wet | 322.0 | 57 | 6 | 43.3 | 2 | 21.9 | 13.9 | 33.3 | 0 |
| 22 | Long rains 2020 | wet | 337.1 | 58 | 11 | 29.9 | 3 | 21.3 | 12.7 | 32.1 | 0 |
| 23 | Long rains 2006 | wet | 344.7 | 60 | 17 | 27.9 | 3 | 21.2 | 11.7 | 31.7 | 0 |
| 24 | Long rains 2003 | wet | 382.3 | 60 | 16 | 28.6 | 3 | 21.8 | 14.0 | 34.2 | 0 |
| 25 | Long rains 2018 | wet | 556.1 | 69 | 4 | 42.5 | 3 | 20.3 | 12.7 | 31.4 | 0 |

## Short rains: 01 October to 31 December

Window basis: FAO GIEWS refers to the October-December short rains for the same areas.

* Complete seasons classified: 25; excluded: 0.
* Rainfall over the window: mean 256.91 mm, median 232.07 mm, lowest 109.57 mm, highest 489.79 mm; year-to-year variability 35.0 %.
* Boundaries: dry seasons had at most **199.36 mm**; wet seasons had at least **296.86 mm**.
* Representative seasons (median-ranked member of each category): dry `short-rains-2008`, typical `short-rains-2024`, wet `short-rains-2011`.

| Rank | Season | Category | Rain (mm) | Wet days | Longest dry spell (days) | Wettest day (mm) | Days ≥ 20 mm | Mean temp (°C) | Lowest min (°C) | Highest max (°C) | Frost days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Short rains 2005 | dry | 109.6 | 33 | 15 | 6.4 | 0 | 21.8 | 12.5 | 32.1 | 0 |
| 2 | Short rains 2022 | dry | 158.2 | 39 | 30 | 20.3 | 1 | 21.5 | 12.6 | 32.5 | 0 |
| 3 | Short rains 2010 | dry | 162.2 | 45 | 14 | 11.4 | 0 | 21.7 | 13.2 | 32.5 | 0 |
| 4 | Short rains 2008 | dry | 179.6 | 48 | 13 | 18.9 | 0 | 21.7 | 12.4 | 32.6 | 0 |
| 5 | Short rains 2017 | dry | 191.8 | 46 | 12 | 15.1 | 0 | 21.7 | 13.3 | 32.0 | 0 |
| 6 | Short rains 2018 | dry | 194.2 | 46 | 9 | 13.8 | 0 | 21.8 | 13.2 | 32.2 | 0 |
| 7 | Short rains 2016 | dry | 197.8 | 36 | 23 | 14.6 | 0 | 21.7 | 13.4 | 32.6 | 0 |
| 8 | Short rains 2004 | dry | 199.4 | 61 | 11 | 12.8 | 0 | 21.6 | 13.0 | 32.4 | 0 |
| 9 | Short rains 2003 | typical | 216.8 | 58 | 12 | 11.7 | 0 | 21.2 | 12.1 | 32.4 | 0 |
| 10 | Short rains 2014 | typical | 218.3 | 56 | 6 | 20.2 | 1 | 21.6 | 13.1 | 31.9 | 0 |
| 11 | Short rains 2021 | typical | 219.9 | 44 | 17 | 29.5 | 1 | 21.9 | 13.7 | 32.3 | 0 |
| 12 | Short rains 2025 | typical | 231.9 | 40 | 14 | 36.7 | 1 | 22.0 | 13.8 | 33.0 | 0 |
| 13 | Short rains 2024 | typical | 232.1 | 38 | 16 | 33.4 | 1 | 22.4 | 13.3 | 33.5 | 0 |
| 14 | Short rains 2007 | typical | 239.4 | 65 | 5 | 17.4 | 0 | 21.1 | 11.8 | 31.3 | 0 |
| 15 | Short rains 2013 | typical | 243.6 | 48 | 7 | 15.8 | 0 | 21.4 | 13.2 | 31.9 | 0 |
| 16 | Short rains 2009 | typical | 260.5 | 62 | 10 | 11.9 | 0 | 21.5 | 13.1 | 32.3 | 0 |
| 17 | Short rains 2020 | typical | 278.0 | 52 | 8 | 28.5 | 1 | 21.5 | 13.3 | 32.6 | 0 |
| 18 | Short rains 2012 | wet | 296.9 | 59 | 9 | 18.8 | 0 | 21.5 | 13.0 | 32.4 | 0 |
| 19 | Short rains 2001 | wet | 303.6 | 55 | 17 | 22.9 | 1 | 20.8 | 13.5 | 31.7 | 0 |
| 20 | Short rains 2015 | wet | 305.3 | 62 | 8 | 50.6 | 1 | 21.9 | 13.8 | 32.6 | 0 |
| 21 | Short rains 2011 | wet | 321.3 | 58 | 9 | 19.5 | 0 | 20.9 | 13.1 | 32.3 | 0 |
| 22 | Short rains 2002 | wet | 339.7 | 72 | 5 | 14.2 | 0 | 21.0 | 13.9 | 31.9 | 0 |
| 23 | Short rains 2023 | wet | 371.9 | 60 | 9 | 29.7 | 1 | 21.4 | 14.0 | 33.0 | 0 |
| 24 | Short rains 2006 | wet | 461.1 | 76 | 6 | 25.9 | 1 | 20.8 | 13.0 | 31.3 | 0 |
| 25 | Short rains 2019 | wet | 489.8 | 75 | 5 | 32.1 | 3 | 20.8 | 14.0 | 30.0 | 0 |

## Reading the tables

* Wet-day counts are high for a semi-arid area because a grid-cell average records light rain on many days;
  a gauge at one point would usually record fewer wet days. Use them to compare seasons with each other.
* No season in either window had a frost day by the ETCCDI definition. The lowest daily minimum is about
  12 °C. This does not rule out frost in hollows on a particular farm.
* Rainfall totals for the windows are well below the indicative seasonal water use of maize (500-800 mm,
  FAO Training Manual 3). That comparison, with its caveats, is in `rotation_comparison_methodology.md`.
