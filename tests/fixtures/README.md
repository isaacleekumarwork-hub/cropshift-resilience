# Test fixtures

## `power_daily_katumani_2020q1.json`

A **real, unmodified NASA POWER response**, recorded on 14 November 2026 at
02:57 UTC, in the app's own cache format (the original response is under
`payload`).

| | |
| --- | --- |
| Site | Latitude -1.58, longitude 37.24 (Katumani area, Machakos County, Kenya) |
| Period | 1 January to 31 March 2020, daily, UTC days (91 days) |
| Parameters | `ALLSKY_SFC_SW_DWN`, `PRECTOTCORR`, `RH2M`, `T2M`, `T2M_MAX`, `T2M_MIN` |
| Service | NASA POWER Daily API v2.10.3 |

Source: NASA Langley Research Center POWER project,
https://power.larc.nasa.gov/

Tests that need damaged or incomplete data make a copy of this response in
memory and alter the copy. Those altered values are test inputs, labelled as
such in the tests, and are never presented as NASA data.

To record it again:

```bash
NASA_CACHE_DIRECTORY=tests/fixtures/_tmp python -m src.data_service fetch \
  --lat -1.58 --lon 37.24 --start 2020-01-01 --end 2020-03-31
```
