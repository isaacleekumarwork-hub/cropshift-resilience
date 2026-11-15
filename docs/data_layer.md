# NASA data layer: user guide

How to retrieve, check and reuse NASA environmental data with CropShift
RESILIENCE. Built in phase A2.

## What it does

Given a location and a historical date range, the data layer returns daily
values from the NASA POWER Daily API together with a quality report and a
provenance record. It works from the command line, from Python and inside the
Streamlit app, and it does not need Streamlit or any AI service.

```
request ─> cache? ─> NASA POWER ─> structure check ─> cache
                                         │
                                         v
        typed observations <─ value checks <─ unit check
                │
                ├─> quality report (completeness, warnings, accepted or not)
                ├─> provenance record (what, where, when, how to cite)
                └─> tables and monthly summaries
```

## Pilot site

| | |
| --- | --- |
| Site | Katumani area, Machakos County, Kenya |
| Coordinates | Latitude -1.58, longitude 37.24 |
| Period | 1 January 2001 to 31 December 2025 (9,131 days) |
| Days bounded by | UTC |
| Result on 14 Nov 2026 | All six variables 100 % complete; accepted |

Why this site: rainfall decides most seasons there, it has two rainy seasons a
year, and smallholder farmers in semi-arid regions stand to gain most from free
NASA data. Why this period: 25 complete years, a single solar product
throughout (CERES SYN1deg starts on 1 January 2001), and an end date well clear
of the recent months NASA may still revise. The full reasoning is in
`src/pilot_sites.py`.

The values describe NASA grid cells tens of kilometres wide, at an average
elevation of 1,328 m. **They are not measurements from an individual farm.**

## Commands

Retrieve the pilot dataset (uses the cache if it is there):

```bash
python -m src.data_service pilot
```

Force a fresh request to NASA:

```bash
python -m src.data_service pilot --refresh
```

Any other point and historical range:

```bash
python -m src.data_service fetch --lat -1.58 --lon 37.24 --start 2020-01-01 --end 2020-12-31
```

Only some parameters, or days bounded by local solar time:

```bash
python -m src.data_service fetch --lat 42.03 --lon -93.62 --start 2015-01-01 --end 2015-12-31 --parameters T2M,PRECTOTCORR --time-standard LST
```

Delete one request's cache entry:

```bash
python -m src.data_service fetch --lat -1.58 --lon 37.24 --start 2020-01-01 --end 2020-12-31 --invalidate
```

Run without a network, using stored data only:

```bash
OFFLINE_DEMO_MODE=true python -m src.data_service pilot
```

The command exits with 0 when the dataset is accepted, 2 when it was retrieved
but is too incomplete, and 1 when it could not be loaded.

## From Python

```python
from datetime import date

from src.data_processing import monthly_climatology, monthly_summary, to_wide_frame
from src.data_service import load_dataset, load_pilot_dataset
from src.nasa_client import PowerRequest

dataset = load_pilot_dataset()                 # or load_dataset(PowerRequest(...))
dataset.require_accepted()                     # raises if it is too incomplete

rain = dataset.get("precipitation")            # an ObservationSeries
first = rain.observations[0]
first.value, first.unit, first.period_start    # 0.18, Unit 'mm/day', 2001-01-01
first.provenance.kind                          # DataKind.REANALYSIS

dataset.quality.accepted                       # True
dataset.provenance.origin                      # network, cache or bundled
dataset.provenance.citations                   # how to cite it

daily = to_wide_frame(dataset)                 # one row per day
monthly = monthly_summary(dataset)             # totals and means per month
average_year = monthly_climatology(monthly)    # average of each calendar month

custom = load_dataset(
    PowerRequest(
        latitude=42.03, longitude=-93.62,
        start=date(2015, 1, 1), end=date(2015, 12, 31),
        parameters=("T2M", "PRECTOTCORR"),
    )
)
```

## The NASA endpoint

`https://power.larc.nasa.gov/api/temporal/daily/point`
([official documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/))

Every request sends exactly these query parameters:

| Parameter | Value | Note |
| --- | --- | --- |
| `parameters` | Comma-separated list, sorted | At most 20 per request (NASA's limit) |
| `community` | `AG` | Agroclimatology. Fixed, because units differ between communities |
| `longitude`, `latitude` | Four decimal places | About 11 m; far finer than any grid cell |
| `start`, `end` | `YYYYMMDD` | Past dates only |
| `format` | `JSON` | |
| `time-standard` | `UTC` (default) or `LST` | Always sent explicitly |

No account, key or personal identifier is sent.

## Data dictionary

### Supported parameters

| NASA parameter | CropShift variable | Unit | Kind of evidence | Source product | Grid | From |
| --- | --- | --- | --- | --- | --- | --- |
| `T2M` | `air_temperature_mean` | degC | Reanalysis | MERRA-2 | 0.5° x 0.625° | 1981 |
| `T2M_MAX` | `air_temperature_max` | degC | Reanalysis | MERRA-2 | 0.5° x 0.625° | 1981 |
| `T2M_MIN` | `air_temperature_min` | degC | Reanalysis | MERRA-2 | 0.5° x 0.625° | 1981 |
| `PRECTOTCORR` | `precipitation` | mm/day | Reanalysis, bias-corrected | MERRA-2 | 0.5° x 0.625° | 1981 |
| `ALLSKY_SFC_SW_DWN` | `solar_irradiance` | MJ/m^2/day | Satellite-based estimate | CERES SYN1deg (GEWEX SRB before 2001) | 1° x 1° | 1984 |
| `RH2M` | `relative_humidity` | % | Reanalysis | MERRA-2 | 0.5° x 0.625° | 1981 |

`T2M` and `PRECTOTCORR` are the core pair. The other four were added because
later phases need them: daily maximum and minimum for heat and frost exposure,
sunshine and humidity for evaporative demand. They arrive in the same single
request. Any other parameter is refused.

Daily maximum and minimum temperatures come from the 24 hourly values of the
day; all other values are daily means or totals (NASA POWER methodology).

### One observation (`EnvironmentalObservation`)

| Field | Meaning |
| --- | --- |
| `variable` | CropShift variable name |
| `value` | The number, or `None` for a gap |
| `unit` | The variable's one permitted unit |
| `missing` | `present`, `missing_at_source`, `not_yet_available`, `rejected_by_validation` |
| `quality` | `passed`, `suspect`, `failed`, `not_assessed` |
| `quality_note` | Why a value was flagged or discarded |
| `period_start`, `period_end` | The day covered |
| `temporal_resolution` | `daily` |
| `location` | The requested point |
| `provenance` | Kind of evidence, source, version, citation, request URL, retrieval time, time standard, grid, transformations |

### Daily long table (`to_frame`)

`date`, `variable`, `value` (empty for gaps), `unit`, `missing`, `quality`,
`kind`, `source`.

### Monthly table (`monthly_summary`)

| Column | Meaning |
| --- | --- |
| `year`, `month` | Calendar month |
| `variable` | The daily variable aggregated |
| `statistic` | `total` or `mean` |
| `value` | The monthly value; empty when not reported |
| `unit` | Unit of the monthly value (`mm` for rainfall totals) |
| `output_variable` | `precipitation_total` for rainfall; otherwise the same variable |
| `days_expected` | Length of the calendar month |
| `days_valid` | Days with a valid value |
| `completeness_percent` | `days_valid` over `days_expected` |
| `reported` | Whether the month met its completeness threshold |
| `method` | The aggregation in words |

## Data quality rules

### Level 1: structure (a failure rejects the whole response)

* The response has its header, geometry, parameter metadata and data sections.
* The fill value is a number and the time standard matches the request.
* The coordinates echoed back match the request within 0.01°.
* Every requested parameter is present, with a unit.
* Every date key is a valid `YYYYMMDD` date, and none appears twice.

Parameters that were not requested and dates outside the request are ignored
and noted.

### Level 2: units and values

* **Units.** Each parameter must report its documented unit. Any other unit
  stops ingestion with an error; nothing is converted by guesswork.
* **Missing values.** NASA's fill value (read from the response header,
  currently -999), nulls and absent dates become explicit gaps. Trailing gaps
  within 180 days of retrieval are labelled "not yet available".
* **Not numbers.** Text, true/false and other non-numeric values are discarded
  and reported as errors. They are never coerced.
* **Impossible values** (outside the hard physical limits in `src/models.py`)
  are discarded and reported as errors.
* **Unusual values** are kept and flagged `suspect`:

  | Variable | Flagged as unusual when |
  | --- | --- |
  | Mean temperature | below -70 or above 50 degC |
  | Daily maximum temperature | below -65 or above 55 degC |
  | Daily minimum temperature | below -80 or above 45 degC |
  | Precipitation | above 500 mm/day |
  | Solar irradiance | above 40 MJ/m^2/day |
  | Any day | minimum, mean and maximum temperature out of order |

  These screening limits were chosen by this project to be deliberately wide.
  They are in `PLAUSIBLE_RANGES` in `src/data_validation.py`.

A valid number is never altered. A real dry day stays 0; a gap never becomes 0.

### Level 3: completeness

For each variable: expected days, valid days, missing days, completeness
percentage, first and last valid date. A dataset is **accepted** only if every
variable is at least `NASA_MIN_COMPLETENESS_PERCENT` complete (default 90). A
dataset that falls short is still returned, marked not accepted, so the reason
can be shown; `require_accepted()` prevents it being used further.

### Monthly aggregation

| Variable | Monthly statistic | Reported when |
| --- | --- | --- |
| Precipitation | **Total** (sum of daily values, in mm) | Every day of the month is valid |
| Temperatures, solar, humidity | **Mean** of daily values | At least 80 % of days are valid |

A total over fewer days would be biased low, so it needs the full month. Both
thresholds are arguments of `monthly_summary`. Months that fall short are
marked not reported and left empty. A month only partly covered by the request
counts as incomplete.

### What passing these checks does not mean

The checks establish that a response is well formed, physically possible and
complete. They do **not** establish that the values are accurate for a
particular farm. See `scientific_assumptions.md`.

## Cache

| | |
| --- | --- |
| Location | `data/cache/` (setting `NASA_CACHE_DIRECTORY`); ignored by Git |
| One file per | Request: location, date range, parameters, community, time standard |
| File name | SHA-256 of the normalised request |
| Contents | The request, its URL, retrieval time and NASA's original response, unmodified |
| Lifetime | 30 days (setting `NASA_CACHE_TTL_HOURS`) |
| Writes | Atomic: written under a temporary name, then renamed |
| Verification | On every read: format, key, stored request and the response's SHA-256 fingerprint |
| Damaged entry | Ignored, reported as a warning, and replaced by a fresh request |
| Remove one entry | `--invalidate`, or `data_service.invalidate(request)` |
| Remove everything | Delete the folder |

An identical request is never sent to NASA twice while its entry is valid.
NASA POWER asks for exactly this: one request per grid cell.

## Offline mode

Set `OFFLINE_DEMO_MODE=true`. The app and the command line then:

1. read the local cache, even if the entry has expired (and say so);
2. otherwise read the bundled data in `data/demo/`;
3. otherwise stop with a clear message.

No network client is created in offline mode. Bundled data is real NASA data
saved during the hackathon and is labelled as bundled wherever it is shown. A
request that matches nothing stored fails; nothing is substituted.

In online mode, if NASA cannot be reached, the same stored data is used as a
fallback with a visible warning. A request that NASA *rejects* is never papered
over this way.

## Settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `OFFLINE_DEMO_MODE` | `false` | Stored data only; no network |
| `NASA_POWER_BASE_URL` | the endpoint above | Must be `https` |
| `NASA_REQUEST_TIMEOUT` | `30` | Seconds per attempt |
| `NASA_MAX_RETRIES` | `3` | Extra attempts after a rate limit, timeout or temporary server error (0 to 6) |
| `NASA_CACHE_DIRECTORY` | `data/cache` | Cache folder |
| `NASA_CACHE_TTL_HOURS` | `720` | Cache lifetime |
| `NASA_DEMO_DIRECTORY` | `data/demo` | Bundled data folder |
| `NASA_MIN_COMPLETENESS_PERCENT` | `90` | Acceptance threshold |

Retries wait 1, 2, 4 ... seconds (at most 30) with random jitter, and honour
NASA's `Retry-After` header up to 60 seconds. Requests NASA rejects outright
and malformed responses are not retried.

## Troubleshooting

| What you see | Likely cause | What to do |
| --- | --- | --- |
| "NASA POWER could not be reached after 4 attempt(s)" | No connection, or the service is down | Check the connection; or set `OFFLINE_DEMO_MODE=true` to use stored data |
| "Offline mode is on and no stored NASA response matches this request" | Offline, and this exact request was never retrieved | Set `OFFLINE_DEMO_MODE=false` once to retrieve it, or use the pilot dataset |
| "NASA POWER rejected the request (HTTP 422)" | NASA does not accept the request | Read the message that follows; check dates and coordinates |
| "Invalid request: ..." | The request failed our own checks before being sent | The message names the problem (for example a future date or unsupported parameter) |
| "... is available from 1984-01-01; start is too early" | Solar data starts later than weather data | Start in 1984 or later, or leave out `ALLSKY_SFC_SW_DWN` |
| "A stored response was ignored because it failed verification" | A cache file was damaged or edited | Nothing: it was replaced automatically. Offline, delete the file |
| "... is reported in 'K' but 'C' is documented" | NASA changed a unit | Do not work around it. The parameter table in `src/nasa_client.py` needs review |
| "dataset not accepted: ... below the required 90%" | Too many gaps | Choose a different period, or lower the threshold knowingly |
| Certificate error | A proxy or outdated certificates | Fix the certificates. Certificate checking is never switched off |
| The first run is slow | Python libraries being loaded for the first time | Later runs are fast |
