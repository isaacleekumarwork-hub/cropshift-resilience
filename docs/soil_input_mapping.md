# Soil inputs and the three soil mappings (phase A4.2)

Code: `src/soil_inputs.py`. Tests: `tests/test_soil_inputs.py`.

## The three mappings

They are the three `soil_information` mappings in the A3 registry
(`data/knowledge/variable_mappings.json`). Nothing was renamed or swapped for
something easier.

| A3 mapping | Crop value (source) | Soil input | Calculation | Indicator |
| --- | --- | --- | --- | --- |
| `soil-ph-requirement-to-soil-ph` | Documented pH range (Feedipedia; none for cowpea) | `soil_ph` | Inside, below or above each admitted range | `soil_ph_vs_documented_range` |
| `rooting-depth-to-soil-water` | Maximum rooting depth Zr, m (FAO-56 Table 22; Feedipedia for pigeon pea) | Available water θFC − θWP, m³/m³ | TAW = 1000 (θFC − θWP) Zr, mm (FAO-56 Equation 82) | `root_zone_available_water` |
| `depletion-fraction-to-soil-water` | Depletion fraction p (FAO-56 Table 22; none for pigeon pea) | The same available water | RAW = p TAW, mm (FAO-56 Equation 83) | `readily_available_water` |

Both equations were re-read in FAO-56 Chapter 8 during the A4 evidence audit.
The A3 registry also names `soil_field_capacity`, `soil_wilting_point` and
`soil_available_water_capacity` as the targets of the two water mappings; all
three are accepted.

Drainage class is accepted as well, because the stored constraint
`waterlogging-sensitive-crop-on-wet-soil` needs it. It is not one of the three
mappings.

## What a user can enter (`SoilProfileInput`)

Every field is optional. Absence stays absence.

| Field | Unit | Physical limits (rejected outside) | Plausibility screen (warning only) |
| --- | --- | --- | --- |
| `soil_ph` | pH | 0 to 14 | 4.0 to 9.0, the widest span of any crop pH range held |
| `texture` | USDA class | the twelve classes | none |
| `field_capacity`, `wilting_point` | m³/m³ | 0 to 1; field capacity must exceed wilting point; give both or neither | FAO-56 Table 19 spans (0.07-0.42 and 0.02-0.29) |
| `available_water_capacity` | mm per m of soil | 0 to 500 | FAO-56 Table 19 span (50-200 mm/m) |
| `drainage` | well, moderately or poorly drained | the three classes | none |
| `depth_top_cm`, `depth_bottom_cm` | cm | bottom below top | none |

If field capacity, wilting point and available water capacity are all given,
they must agree within 10 mm/m, or the input is rejected as contradictory.

## Where a value comes from

Each entry carries a source class, as the user states it:

| Source class | Meaning | Evidence kind recorded | Verification status |
| --- | --- | --- | --- |
| `user_reported` | The farmer's own knowledge or observation | user reported | not verified |
| `lab_measured` | The user reports a laboratory measurement | **user reported** | **not verified**: CropShift has not seen the laboratory report |
| `public_soil_dataset` | Read by the user from a public soil map; the dataset must be named | user reported | not verified |
| `provisional_assumption` | A hypothetical demonstration value | assumed | hypothetical |
| `unknown` | Not provided | (the field is left empty; an entry with this class is rejected) | not provided |

When only a texture class is known, the FAO-56 Table 19 range for that class is
used and labelled *literature reference*: a typical value for a soil type, not a
measurement of the field. The garbled silty clay row is refused by the evidence
gate. Sandy clay, sandy clay loam and clay loam have no row in Table 19, so the
soil water indicators are unavailable for them unless measured values are
entered.

Each resolved value (`SoilValueRecord`) keeps: variable, value or class, unit,
source class, source identifier, where it applies, collection or entry date,
verification status, limitations and warnings, and a provenance record. The same
values are also exported in the A1 `SoilInformation` contract, where a reported
laboratory value is categorised as *user entered*, never *measured locally*.

## When soil information is missing

* The dependent indicators are **unavailable**, with what is missing and how to
  obtain it ("A soil test from a soil-testing laboratory or the local
  agricultural extension service reports pH", and so on).
* Every other indicator is calculated as normal.
* No default soil is inserted.

## The demonstration profile

`demonstration_soil_profile()` returns pH 6.5, loam, well drained, every value
a `provisional_assumption`, labelled "Hypothetical demonstration soil (not real
data)". The profile model refuses to mix hypothetical and real entries. Every
indicator built on it says so in its headline and carries the
`hypothetical_assumption` information layer, and the report's first limitation
says the soil is hypothetical. It is not Katumani soil data.

## Never from NASA

No function in the module accepts or reads a weather value; a test checks the
module source for weather variable names. Soil properties are never inferred
from NASA temperature or rainfall.

## Interface for A5

```python
from src.soil_inputs import SoilProfileInput, SoilValueInput, SoilTextureInput, SoilDrainageInput

soil = SoilProfileInput(
    soil_ph=SoilValueInput(value=6.1, source_class="lab_measured", source_identifier="Report 17"),
    texture=SoilTextureInput(texture_class="sandy_loam", source_class="user_reported"),
)
report = compare_strategies(..., soil=soil)   # or run_pilot_comparison(soil=soil)
```

The engine does not use Streamlit session state; A5 builds the input object
from its widgets and passes it in.

## Limitations

* User values are not verified. Laboratory values are only as good as the
  sampling and the laboratory.
* The calculation assumes the soil holds water the same way through the whole
  root zone, although the values usually describe the topsoil.
* Published rooting depths assume no layer that stops roots; soil depth at the
  field is not asked for.
* The depletion fraction is used unadjusted. FAO-56 gives it for an
  evapotranspiration rate of about 5 mm/day and describes an adjustment that
  needs crop evapotranspiration, which is not calculated.
