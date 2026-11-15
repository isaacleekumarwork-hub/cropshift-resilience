# Pilot configuration and season windows (phase A4.3)

Code: `src/season_config.py`. Tests: `tests/test_scenario_engine.py`.

## The pilot site: provisional

| | |
| --- | --- |
| Site | Katumani area, Machakos County, Kenya (`katumani-machakos-ke`) |
| Coordinates | latitude −1.58, longitude 37.24 (WGS 84), unchanged from A2 |
| Status | **PROVISIONAL**: the participant has not approved the site |
| NASA grid cell | MERRA-2 cell about 55 km × 70 km, average elevation 1,327.62 m |

The configuration refuses to call itself approved unless the site record is
approved, and every comparison report repeats the approval note: "Provisional:
the participant has not approved this pilot site. It must not be presented as
the project's finalised site until approved."

### Plausibility of the coordinates

* **NASA echo** (14 Nov 2026): NASA POWER returned the requested point with a
  grid-cell elevation of 1,327.62 m.
* **Reverse geocoding** (15 Nov 2026): one request to OpenStreetMap Nominatim for
  (−1.58, 37.24) returned "Mua ward, Machakos Town, Machakos County, Kenya".
  Data © OpenStreetMap contributors, ODbL.

The point lies in Machakos County, as the site name says. It is not claimed to
be any farm, or the ICRAF station where the Machakos experiment ran.

### Replacing the site

`pilot_configuration(site, windows)` accepts any `PilotSite` and any season
windows. Nothing in the engine refers to Katumani by name. The comparison
refuses scenarios built for a different location than the configuration.

## Season windows

| Window | Calendar | Length | Source | Status |
| --- | --- | --- | --- | --- |
| Long rains | 1 March to 31 May | 92 days | FAO GIEWS Country Brief: Kenya: long rains "typically extend from March to May" in the marginal bimodal-rainfall south-eastern areas | Cited analysis window |
| Short rains | 1 October to 31 December | 92 days | Same brief: the "October-December" short rains | Cited analysis window |

The wording was re-checked on the live page on 15 November 2026.

**These are analysis windows, not sowing dates.** The model has an
`is_sowing_date` field that can only be false. The same FAO brief reports that
the 2026 long rains began early, in mid-February, which shows how far real
seasons depart from fixed calendar windows.

`SeasonWindow` supports:

* any start and end day of any month (29 February is not a valid boundary);
* windows that cross the new year (for example November to February), whose
  season year is the year in which they start;
* `cited` windows, which must name a registered source, and `user_defined`
  windows, which must not.

## Rotation strategies

| Strategy | Sequence | Documented system | Role |
| --- | --- | --- | --- |
| Continuous maize | maize | `machakos-continuous-maize` | Baseline (current practice is assumed; see below) |
| Maize rotated with cowpea | maize, cowpea | `machakos-maize-cowpea-rotation` | Alternative |
| Maize rotated with pigeon pea | maize, pigeon pea | `machakos-maize-pigeon-pea-rotation` | Alternative |

All three are systems that Rao and Mathuva (2000) actually grew at Machakos
from 1989 to 1996. The maize and pigeon pea **intercrop** they also grew is not
a rotation and is not compared.

Continuous maize is marked as the current-practice strategy because it was the
experiment's baseline. Whether it is any farmer's current practice is for the
user to say; that assumption is recorded on the strategy.

### What the study does not say, and how that is handled

| Not reported | Handling |
| --- | --- |
| Which crop was grown in which rainy season | `season_assignment = unknown`: each crop is evaluated against **both** windows |
| Planting dates | `planting_dates = unknown`; nothing assumes a crop is sown at the start of a window |
| Length of one cycle | `seasons_per_cycle = None` for the two rotations; one crop per slot is the stated assumption |
| Whether pigeon pea occupies more than one season | Flagged by the stored constraint `perennial-in-seasonal-rotation` |

A user may choose a season for each slot with
`strategy.with_seasons(("long-rains", "short-rains"), reason=...)`. The copy is
labelled hypothetical, its assumptions say it "does not reproduce the design of
any published study", and every report built on it flags hypothetical inputs.
A strategy that claims a documented system must use exactly that system's crops.

### Crop duration against the window

The documented growing periods (FAO Training Manual 3, Table 6) are longer than
either 92-day window for maize (125-180 days) and sorghum (120-130 days), and
slightly longer for common bean (95-110 days). The indicator
`growing_period_vs_window` reports the difference, and the rainfall indicator
states that rain outside the window and stored soil water are not counted. No
growing period is documented for cowpea, mung bean or pigeon pea, so the
indicator is unavailable for them.
