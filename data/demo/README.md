# Bundled demonstration data

This folder holds **real NASA POWER responses** saved during the hackathon so
that the app can be demonstrated without a network connection. Nothing here is
synthetic, edited or estimated.

Each file is named by the SHA-256 cache key of the request that produced it and
contains the request, the exact URL, the retrieval time and the original
response, unmodified, in `payload`. On every read the app re-checks the
response against its recorded fingerprint and refuses the file if they differ.

## Contents

| | |
| --- | --- |
| File | `4f87119a04095bb22483ce976c27c9947ffc065ca8d23f538212328d753a6956.json` |
| Site | Katumani area, Machakos County, Kenya (latitude -1.58, longitude 37.24) |
| Period | 1 January 2001 to 31 December 2025, daily, UTC days |
| Parameters | `ALLSKY_SFC_SW_DWN`, `PRECTOTCORR`, `RH2M`, `T2M`, `T2M_MAX`, `T2M_MIN` |
| Service | NASA POWER Daily API v2.10.3, agroclimatology community |
| Upstream products | MERRA-2, CERES SYN1deg |
| Retrieved | 14 November 2026, 02:57 UTC |
| Response fingerprint (SHA-256) | `1c2ed230e2661199ac278e4ac68b179c4b5750284091c094745de4a920e0edaf` |

Request:

```
https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN%2CPRECTOTCORR%2CRH2M%2CT2M%2CT2M_MAX%2CT2M_MIN&community=AG&longitude=37.2400&latitude=-1.5800&start=20010101&end=20251231&format=JSON&time-standard=UTC
```

To reproduce it:

```bash
python -m src.data_service pilot --refresh --save-bundled
```

## Citation

The data was obtained from National Aeronautics and Space Administration
(NASA) Langley Research Center's Prediction Of Worldwide Energy Resources
(POWER) project funded through the NASA Earth Science Division.

The data was obtained from the POWER Project's Daily v2.10.3 version on
2026/11/14.

## Notes

* The values are averages over NASA grid cells tens of kilometres wide. They
  are not measurements from an individual farm.
* The NASA POWER project asks to be notified when its data is passed on to
  others (https://power.larc.nasa.gov/docs/referencing/). See
  `docs/compliance.md`.
* This project is not endorsed by NASA.
