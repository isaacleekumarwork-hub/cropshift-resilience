# Agronomic knowledge base

Built in phase A3. Version 0.3.0, compiled 14 November 2026. Tables in this
document were generated from the data files in `data/knowledge/` on
15 November 2026; the data files are the authority.

## Status: provisional

* **The pilot site has not been approved.** It is still the proposal made in
  phase A2. Nothing in the knowledge base says that a crop suits that site.
* **Values describe species in general**, under the conditions each source
  states. No cultivar-specific value is stored.
* **Nothing was estimated.** Where the sources read give no value, the gap is
  recorded as "not established", with the reason.
* **Nothing is compared, ranked or recommended.** The knowledge base stores
  facts and their evidence. Phase A4 decides how to use them.

## What every value is

| Kind | Meaning | How to recognise it |
| --- | --- | --- |
| **Sourced** | Read from a named table or passage of a registered source | Has a source, a locator and a confidence level |
| **Derived** | Worked out from sourced values by a stated step | None in the knowledge base, except one inferred life cycle (maize), which is labelled "inferred" |
| **Assumed** | A step this project took that a source does not state | Listed under "Assumptions" for each crop, and for the pilot site |
| **Unknown** | Not established by the sources read | Listed under "Not established", with the reason |

Sources and how each was checked are in
[`evidence_registry.md`](evidence_registry.md).

## Crop selection

Six crops in two botanical families.

| Crop | Scientific name | Family | Life cycle | Fixes nitrogen | Record status | Evidence from Machakos |
| --- | --- | --- | --- | --- | --- | --- |
| Common bean (dry) | *Phaseolus vulgaris L.* | Fabaceae | annual | yes | provisional | none found |
| Cowpea | *Vigna unguiculata (L.) Walp.* | Fabaceae | annual | yes | incomplete | yes |
| Maize | *Zea mays L.* | Poaceae | annual (inferred) | not described as such | provisional | yes |
| Mung bean (green gram) | *Vigna radiata (L.) R. Wilczek* | Fabaceae | annual | yes | incomplete | none found |
| Pigeon pea | *Cajanus cajan (L.) Huth* | Fabaceae | short lived perennial | yes | incomplete | yes |
| Sorghum (grain) | *Sorghum bicolor (L.) Moench* | Poaceae | annual | not described as such | provisional | none found |

### Why these crops

| Crop | Reason for inclusion | Strength of the case |
| --- | --- | --- |
| Maize | The cereal in the seven-year cropping-systems experiment at Machakos; full water-use data in the FAO handbooks | Strong: regional evidence and complete water data |
| Cowpea | The short-duration legume rotated with maize in that experiment | Strong regional evidence; water data incomplete |
| Pigeon pea | The long-duration legume rotated and intercropped with maize in that experiment; described as drought resistant | Strong regional evidence; **no water-use data at all** |
| Sorghum | The cereal the sources describe as coping better than maize in drought; full water-use data | Good general evidence; **no regional evidence** |
| Common bean | A short-season legume with complete water-use data and well-documented temperature limits | Good general evidence; **no regional evidence** |
| Mung bean (green gram) | A fast-maturing legume described as drought tolerant | Weakest case: shared FAO row, no growing period, no regional evidence |

The selection was limited to crops for which authoritative, readable sources
could be found in the time available. Three of the six have no evidence tying
them to the pilot region; they are included for their general characteristics
and marked accordingly. Only two families are represented, so the knowledge
base can say little about family diversity.

### What "fixes nitrogen: not described as such" means

For maize and sorghum the field is false. That records only that no source
read describes them as nitrogen-fixing. It is not a sourced statement that
they do not.

## Kinds of requirement

Sources use different kinds of threshold. They are stored separately and must
never be treated as the same thing.

| Kind | Meaning | Example |
| --- | --- | --- |
| **Optimal** | The source calls it optimal or best | Maize: 18 to 21 °C average day-temperature |
| **Suitable** | Conditions under which the source says the crop grows | Common bean: average temperatures of 15 to 23 °C |
| **Tolerated** | Outer limits: the crop withstands it, or growth stops beyond it | Common bean: growth stops below 10 °C |
| **Stage-specific** | Applies to one named development stage | Sorghum: 25 to 30 °C at seedling |
| **Typical** | A typical value under the source's standard conditions | Crop coefficients, rooting depth, growing period |

Two further distinctions are enforced:

* **Seasonal water use is not rainfall demand.** The FAO figures are crop
  evapotranspiration for a well-watered crop. They are stored as
  `crop_seasonal_water_requirement`, in millimetres per growing period, and
  every record says so.
* **Annual rainfall is not water available to a crop.** Figures such as "750 to
  1100 mm a year" describe where a crop is grown. They are stored separately,
  as `crop_annual_rainfall_requirement`.

## Crop profiles

### Common bean (dry)

**What is known.** Common bean has a short growing period (about 95 to 110 days) and lower total water use than the cereals (roughly 300 to 500 mm), but is rated medium to high in sensitivity to drought. It is grown where average temperatures are between 15 and 23 °C, and high temperatures may hamper seed production. It fixes nitrogen, though less efficiently than other legumes.

**Why it matters.** A short season and low total water use can fit a brief rainy season, but drought sensitivity and a preference for cooler conditions limit where that helps.

**Evidence.** Water-use values come from two FAO irrigation handbooks. Climate, soil and nitrogen statements come from a Feedipedia datasheet.

**What is uncertain.** No source read places common bean at the pilot site. How much nitrogen it leaves for a following crop is not established, and the 15 to 23 °C range uses an unspecified average.

**Region-specific?** No. These are general characteristics of the species.

| Characteristic | Kind | Value | Unit | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Crop coefficient, initial stage | Typical | 0.4 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Beans, dry and Pulses', and the text following the table | Context-dependent |
| Crop coefficient, mid-season | Typical | 1.15 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Beans, dry and Pulses' and footnote 2 | Directly supported |
| Crop coefficient, end of season | Typical | 0.35 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Beans, dry and Pulses' | Directly supported |
| Maximum height | Typical | 0.4 | m | `fao-56`, Chapter 6, Table 12, row 'Beans, dry and Pulses', column 'Maximum Crop Height' | Directly supported |
| Maximum rooting depth | Typical | 0.6 to 0.9 | m | `fao-56`, Chapter 8, Table 22, row 'Beans, dry and Pulses' | Directly supported |
| Depletion fraction (p) | Typical | 0.45 | fraction | `fao-56`, Chapter 8, Table 22, row 'Beans, dry and Pulses' | Directly supported |
| Yield response factor (Ky) | Typical | 1.15 | dimensionless | `fao-56`, Chapter 8, Table 24, row 'Beans' | Directly supported |
| Growing period | Typical | 95 to 110 | day | `fao-tm3`, Chapter 3, Table 6, row 'Bean dry' | Context-dependent |
| Seasonal water use | Typical | 300 to 500 | mm/total growing period | `fao-tm3`, Chapter 3, Table 14, row 'Bean' | Context-dependent |
| Temperature | Suitable | 15 to 23 | degC | `feedipedia-common-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Temperature | Tolerated | up to 35 | degC | `feedipedia-common-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Temperature | Tolerated | at least 10 | degC | `feedipedia-common-bean`, Section 'Distribution', second paragraph (citing Wortmann, 2006; Smoliak et al., 1990) | Directly supported |
| Annual rainfall | Optimal | 500 to 1500 | mm/year | `feedipedia-common-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Annual rainfall | Tolerated | 300 to 4300 | mm/year | `feedipedia-common-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Soil pH | Suitable | 4 to 9 | pH | `feedipedia-common-bean`, Section 'Distribution', second paragraph | Context-dependent |

Sourced statements:

- **nitrogen fixation:** Described as an N-fixing legume that is less efficient in fixing nitrogen than other legumes, but reported to have fixed up to 125 kg N/ha. (`feedipedia-common-bean`; directly supported)
- **drought sensitivity:** Sensitivity to drought: medium-high. (`fao-tm3`; context-dependent)
- **waterlogging:** Generally cannot withstand waterlogging, though some cultivars do well in standing water. (`feedipedia-common-bean`; directly supported)
- **wet conditions:** Does not do well under very wet conditions, which cause fungal attacks and flower drop. (`feedipedia-common-bean`; directly supported)
- **frost:** Has slight frost tolerance, but frost hinders yield at various stages of growth. (`feedipedia-common-bean`; directly supported)
- **soil preference:** Does better on well-drained sandy loam, silt loam or clay loam soils that are rich in organic content. (`feedipedia-common-bean`; context-dependent)
- **nutrient sensitivities:** Sensitive to aluminium, boron, manganese and high levels of sodium. Zinc deficiency may arise on calcareous soils, and magnesium and molybdenum deficiencies on sandy acidic soils. (`feedipedia-common-bean`; directly supported)
- **salinity:** Rated sensitive to salinity. Yield first declines at a soil saturation-extract conductivity of 1.0 dS/m. (`fao-56`; directly supported)
- **root system:** Has a taproot with many adventitious roots. (`feedipedia-common-bean`; directly supported)
- **climate preference:** A warm-season legume that does better under subtropical and temperate conditions. (`feedipedia-common-bean`; directly supported)
- **altitude:** Grows from sea level up to an altitude of 2200-3000 m. (`feedipedia-common-bean`; context-dependent)

Not established by the sources read:

- **soil ph optimal:** Only a broad 'grows well' range was found; no optimal range.
- **base temperature:** No source read gives a base temperature for development, only that growth stops below 10 °C.
- **nitrogen left for next crop:** No source read says how much fixed nitrogen remains in the soil after the grain is harvested.
- **regional use:** No source read reports common bean being grown at or near the pilot site.

Assumptions:

- The FAO rows 'Beans, dry and Pulses', 'Bean dry' and 'Beans' are taken to describe Phaseolus vulgaris grown for dry grain. The rows are broader than that single species.

### Cowpea

**What is known.** Cowpea is an annual, nitrogen-fixing legume with a lower mid-season water use than maize (crop coefficient 1.05). It needs well-drained soil and grows at temperatures of 25 to 35 °C. At Machakos it was the short-duration legume rotated with maize, and maize yielded about 17 % more after it than when grown continuously.

**Why it matters.** It is the legume with direct experimental evidence at the pilot location, both for rotation with maize and for the pest problems that came with it.

**Evidence.** Crop coefficients and rooting depth come from an FAO handbook row shared with green gram. Climate and soil statements come from a Feedipedia datasheet. Regional evidence comes from the abstract of a seven-year Machakos experiment.

**What is uncertain.** Its growing period, seasonal water need, soil pH range and drought tolerance were not found in the sources read. The Machakos result is from one station between 1989 and 1996.

**Region-specific?** The rotation and pest findings are from one research station at Machakos, Kenya, 1989 to 1996. The crop characteristics are general.

| Characteristic | Kind | Value | Unit | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Crop coefficient, initial stage | Typical | 0.4 | dimensionless | `fao-56`, Chapter 6, Table 12, group row 'e. Legumes (Leguminosae)', and the text following the table | Context-dependent |
| Crop coefficient, mid-season | Typical | 1.05 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Green Gram and Cowpeas' | Directly supported |
| Crop coefficient, end of season | Typical | 0.35 to 0.6 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Green Gram and Cowpeas' and footnote 6 | Directly supported |
| Maximum height | Typical | 0.4 | m | `fao-56`, Chapter 6, Table 12, row 'Green Gram and Cowpeas', column 'Maximum Crop Height' | Context-dependent |
| Maximum rooting depth | Typical | 0.6 to 1 | m | `fao-56`, Chapter 8, Table 22, row 'Green Gram and Cowpeas' | Directly supported |
| Depletion fraction (p) | Typical | 0.45 | fraction | `fao-56`, Chapter 8, Table 22, row 'Green Gram and Cowpeas' | Directly supported |
| Temperature | Suitable | 25 to 35 | degC | `feedipedia-cowpea-forage`, Section 'Distribution', second paragraph (citing Madamba et al., 2006) | Context-dependent |
| Annual rainfall | Suitable | 750 to 1100 | mm/year | `feedipedia-cowpea-forage`, Section 'Distribution', second paragraph (citing Madamba et al., 2006) | Context-dependent |

Sourced statements:

- **nitrogen fixation:** Described as an N-fixing legume that can be included in crop rotations to increase soil nitrogen. (`feedipedia-cowpea-forage`; directly supported)
- **drainage:** Grows on a wide range of soils provided they are well drained. (`feedipedia-cowpea-forage`; directly supported)
- **waterlogging:** Sensitive to waterlogging, though less so than other legumes. (`feedipedia-cowpea-forage`; directly supported)
- **humidity and disease:** High moisture may hinder cowpea crops in the sub-humid tropics because of the many diseases they are susceptible to. (`feedipedia-cowpea-forage`; directly supported)
- **shade:** Tolerant of shading and can be combined with tall cereal plants such as sorghum and maize. (`feedipedia-cowpea-forage`; directly supported)
- **root system:** Has a well developed root system. (`feedipedia-cowpea-forage`; directly supported)
- **salinity:** Rated moderately tolerant to salinity. Yield first declines at a soil saturation-extract conductivity of 4.9 dS/m. (`fao-56`; directly supported)
- **altitude:** Widespread in most tropical areas below an altitude of 2000 m. (`feedipedia-cowpea-forage`; context-dependent)
- **duration:** Described as a 'short-duration legume' in the Machakos cropping-systems experiment. (`rao-mathuva-2000`; directly supported)

Reported for a named region:

- Cowpea was the short-duration legume rotated with maize in a cropping-systems experiment at the ICRAF research station at Machakos, Kenya, from November 1989 to February 1996. (`rao-mathuva-2000`; applies to: One research station at Machakos, 1989-1996.)
- In that experiment cowpea was affected by pests and diseases, which the authors say indicates a need for integrated pest management. (`rao-mathuva-2000`; applies to: One research station at Machakos, 1989-1996.)

Not established by the sources read:

- **soil ph:** The datasheet read gives no soil pH range for cowpea.
- **growing period:** No source read gives a growing period in days as a range. The one example found (FAO, Mediterranean, shared with green gram) is internally inconsistent: its stages add up to 100 days beside a printed total of 110.
- **seasonal water need:** The FAO table of indicative crop water needs has no row for cowpea.
- **yield response factor:** The FAO table of yield response factors has no row for cowpea.
- **drought tolerance:** The sections read make no statement about cowpea's tolerance of drought.
- **nitrogen left for next crop:** No source read says how much fixed nitrogen remains in the soil after the grain is harvested.

Assumptions:

- The FAO row 'Green Gram and Cowpeas' is used for cowpea. It is a shared row, so its values are not specific to cowpea.

### Maize

**What is known.** Maize uses more water at mid-season than most field crops (crop coefficient 1.20) and needs roughly 500 to 800 mm of water over a growing period of 125 to 180 days. It is rated medium to high in sensitivity to drought, is harmed most by drought at flowering, does not tolerate flooding and is killed by frost.

**Why it matters.** Where rain is the only source of water, a crop with high water use and high drought sensitivity is the one most exposed in a dry season.

**Evidence.** Water-use values come from two FAO irrigation handbooks. Climate and soil ranges come from a Feedipedia datasheet. Maize was grown in a seven-year experiment at Machakos.

**What is uncertain.** The values describe well-watered crops under standard conditions, not rain-fed smallholder fields. No heat-stress threshold, base temperature or local variety information was found.

**Region-specific?** No. These are general characteristics of the species.

| Characteristic | Kind | Value | Unit | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Crop coefficient, initial stage | Typical | 0.3 | dimensionless | `fao-56`, Chapter 6, Table 12, group row 'i. Cereals', and the text following the table | Context-dependent |
| Crop coefficient, mid-season | Typical | 1.2 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Maize, Field (grain) (field corn)' | Directly supported |
| Crop coefficient, end of season | Typical | 0.35 to 0.6 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Maize, Field (grain) (field corn)' and footnote 11 | Directly supported |
| Maximum height | Typical | 2 | m | `fao-56`, Chapter 6, Table 12, row 'Maize, Field (grain) (field corn)', column 'Maximum Crop Height' | Directly supported |
| Maximum rooting depth | Typical | 1 to 1.7 | m | `fao-56`, Chapter 8, Table 22, row 'Maize, Field (grain) (field corn)' | Directly supported |
| Depletion fraction (p) | Typical | 0.55 | fraction | `fao-56`, Chapter 8, Table 22, row 'Maize, Field (grain) (field corn)' | Directly supported |
| Yield response factor (Ky) | Typical | 1.25 | dimensionless | `fao-56`, Chapter 8, Table 24, row 'Maize' | Directly supported |
| Growing period | Typical | 125 to 180 | day | `fao-tm3`, Chapter 3, Table 6, row 'Maize grain' | Context-dependent |
| Seasonal water use | Typical | 500 to 800 | mm/total growing period | `fao-tm3`, Chapter 3, Table 14, row 'Maize' | Context-dependent |
| Temperature | Optimal | 18 to 21 | degC | `feedipedia-maize-forage`, Section 'Distribution', second paragraph | Context-dependent |
| Annual rainfall | Optimal | at least 750 | mm/year | `feedipedia-maize-forage`, Section 'Distribution', second paragraph | Context-dependent |
| Annual rainfall | Tolerated | 230 to 4100 | mm/year | `feedipedia-maize-forage`, Section 'Distribution', second paragraph | Context-dependent |
| Soil pH | Tolerated | 4.3 to 8.7 | pH | `feedipedia-maize-forage`, Section 'Distribution', second paragraph | Context-dependent |

Sourced statements:

- **frost:** Frost kills the plants. (`feedipedia-maize-forage`; directly supported)
- **drought timing:** Drought is detrimental at flowering, as it affects pollination and impairs yields. (`feedipedia-maize-forage`; directly supported)
- **drought sensitivity:** Sensitivity to drought: medium-high. (`fao-tm3`; context-dependent)
- **waterlogging:** Maize has no tolerance to flooding. (`feedipedia-maize-forage`; directly supported)
- **soil preference:** Optimal conditions include deep, well-drained, rich soils, although maize is grown on a great variety of soils. (`feedipedia-maize-forage`; context-dependent)
- **salinity:** Rated moderately sensitive to salinity. Yield first declines at a soil saturation-extract conductivity of 1.7 dS/m. (`fao-56`; directly supported)
- **altitude:** Grown from sea level to an altitude of 3800 m in the Andean mountains. (`feedipedia-maize-forage`; context-dependent)

Reported for a named region:

- Maize was the cereal in a cropping-systems experiment at the ICRAF research station at Machakos, Kenya, from November 1989 to February 1996. (`rao-mathuva-2000`; applies to: One research station at Machakos, 1989-1996.)

Not established by the sources read:

- **base temperature:** No source read gives a base or other cardinal temperature for development.
- **heat stress threshold:** No source read gives a temperature above which maize is damaged, or for how long.
- **soil ph optimal:** Only the tolerated pH range was found; no optimal range.
- **local varieties:** No source read describes the varieties grown near the pilot site or their growing periods.

Assumptions:

- The FAO rows for 'Maize, Field (grain)' and 'Maize grain' are taken to describe the same crop as the maize in the Machakos trial.

### Mung bean (green gram)

**What is known.** Mung bean, also called green gram, is a fast-maturing annual legume that fixes nitrogen. The sources describe it as tolerant of drought, sensitive to waterlogging, and best suited to temperatures of about 28 to 30 °C. Its mid-season water use is lower than maize (crop coefficient 1.05).

**Why it matters.** A fast-maturing, drought-tolerant legume is a candidate for a short or unreliable rainy season.

**Evidence.** Crop coefficients and rooting depth come from an FAO handbook row shared with cowpeas. Climate, soil and nitrogen statements come from a Feedipedia datasheet.

**What is uncertain.** No source read gives its growing period in days or its seasonal water need, and none places it at the pilot site. The datasheet says it is not a major crop in Africa.

**Region-specific?** No. These are general characteristics of the species.

| Characteristic | Kind | Value | Unit | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Crop coefficient, initial stage | Typical | 0.4 | dimensionless | `fao-56`, Chapter 6, Table 12, group row 'e. Legumes (Leguminosae)', and the text following the table | Context-dependent |
| Crop coefficient, mid-season | Typical | 1.05 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Green Gram and Cowpeas' | Directly supported |
| Crop coefficient, end of season | Typical | 0.35 to 0.6 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Green Gram and Cowpeas' and footnote 6 | Directly supported |
| Maximum height | Typical | 0.4 | m | `fao-56`, Chapter 6, Table 12, row 'Green Gram and Cowpeas', column 'Maximum Crop Height' | Context-dependent |
| Maximum rooting depth | Typical | 0.6 to 1 | m | `fao-56`, Chapter 8, Table 22, row 'Green Gram and Cowpeas' | Directly supported |
| Depletion fraction (p) | Typical | 0.45 | fraction | `fao-56`, Chapter 8, Table 22, row 'Green Gram and Cowpeas' | Directly supported |
| Temperature | Optimal | 28 to 30 | degC | `feedipedia-mung-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Temperature | Tolerated | at least 15 | degC | `feedipedia-mung-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Annual rainfall | Suitable | 600 to 1000 | mm rainfall/year | `feedipedia-mung-bean`, Section 'Distribution', second paragraph | Context-dependent |
| Soil pH | Suitable | 5 to 8 | pH | `feedipedia-mung-bean`, Section 'Distribution', second paragraph (citing Mogotsi, 2006) | Context-dependent |

Sourced statements:

- **nitrogen fixation:** Described as an N-fixing legume that can provide large amounts of biomass and nitrogen to the soil, with reported amounts ranging from 30 to 251 kg N/ha. (`feedipedia-mung-bean`; directly supported)
- **drought:** Tolerant of drought. (`feedipedia-mung-bean`; directly supported)
- **waterlogging:** Sensitive to waterlogging. (`feedipedia-mung-bean`; directly supported)
- **moisture at maturity:** High moisture at maturity tends to spoil the seeds, which may sprout before being harvested. (`feedipedia-mung-bean`; directly supported)
- **soil preference:** Grows on a wide range of soils but prefers well-drained loams or sandy loams. (`feedipedia-mung-bean`; context-dependent)
- **salinity:** Somewhat tolerant to saline soils. (`feedipedia-mung-bean`; context-dependent)
- **maturity:** A fast-growing, warm-season legume that reaches maturity very quickly under tropical and subtropical conditions. (`feedipedia-mung-bean`; directly supported)
- **root system:** Has a well-developed root system. (`feedipedia-mung-bean`; directly supported)
- **altitude:** Found from sea level up to an altitude of 1850 m in the Himalayas. (`feedipedia-mung-bean`; context-dependent)
- **importance in africa:** Though produced in many African countries, the mung bean is not a major crop there. (`feedipedia-mung-bean`; directly supported)

Not established by the sources read:

- **growing period:** No source read gives a growing period in days as a range; one says only that it matures 'very quickly'. The one example found (FAO, Mediterranean, shared with cowpeas) is internally inconsistent and is filed under cowpea.
- **seasonal water need:** The FAO table of indicative crop water needs has no row for mung bean or green gram.
- **yield response factor:** The FAO table of yield response factors has no row for mung bean or green gram.
- **nitrogen left for next crop:** The amounts of nitrogen reported span 30 to 251 kg/ha with no conditions; none says how much remains after harvest.
- **regional use:** No source read reports mung bean being grown at or near the pilot site.

Assumptions:

- The FAO row 'Green Gram and Cowpeas' is used for mung bean because the Feedipedia datasheet lists 'green gram' as a common name of Vigna radiata. It is a shared row, so its values are not specific to mung bean.

### Pigeon pea

**What is known.** Pigeon pea is a short-lived perennial, nitrogen-fixing shrub with a deep taproot. The sources describe it as drought resistant, very heat-tolerant and suited to rain-fed semi-arid farming, but sensitive to waterlogging. At Machakos, maize intercropped with pigeon pea yielded about 24 % more than continuous maize, while maize rotated after pigeon pea was only marginally better.

**Why it matters.** It is the most drought-tolerant legume in the knowledge base and has direct experimental evidence at the pilot location, but the benefit seen there came from intercropping rather than rotation.

**Evidence.** Crop characteristics come from a Feedipedia datasheet. Regional evidence comes from the abstract of a seven-year Machakos experiment.

**What is uncertain.** No crop coefficient, growing period or seasonal water need was found, so its water use cannot be compared with the other crops. Most of the nitrogen it fixes is reported to go into pods and seeds.

**Region-specific?** The rotation, intercropping and pest findings are from one research station at Machakos, Kenya, 1989 to 1996. The crop characteristics are general.

| Characteristic | Kind | Value | Unit | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Maximum height | Typical | 1 to 2 | m | `feedipedia-pigeon-pea-forage`, Section 'Description', subsection 'Morphology' | Context-dependent |
| Maximum rooting depth | Typical | 2 | m | `feedipedia-pigeon-pea-forage`, Section 'Description', subsection 'Morphology' | Context-dependent |
| Temperature | Suitable | 20 to 40 | degC | `feedipedia-pigeon-pea-forage`, Section 'Distribution', first paragraph (citing FAO, 2016a) | Context-dependent |
| Annual rainfall | Optimal | at least 625 | mm/year | `feedipedia-pigeon-pea-forage`, Section 'Distribution', first paragraph | Context-dependent |
| Annual rainfall | Tolerated | at least 250 | mm/year | `feedipedia-pigeon-pea-forage`, Section 'Distribution', first paragraph | Context-dependent |
| Soil pH | Optimal | 5 to 7 | pH | `feedipedia-pigeon-pea-forage`, Section 'Distribution', first paragraph | Context-dependent |

Sourced statements:

- **nitrogen fixation:** Described as an N-fixing legume that does not need inoculation before sowing. Reported to fix 40-97 kg N/ha/year in Africa, with 88 % used for the formation of pods and seeds. (`feedipedia-pigeon-pea-forage`; directly supported)
- **drought:** Described as drought resistant and highly tolerant of dry periods, and as particularly suited to rain-fed agriculture in semi-arid areas because of its deep taproot, heat tolerance and fast growth. (`feedipedia-pigeon-pea-forage`; directly supported)
- **heat:** Very heat-tolerant. (`feedipedia-pigeon-pea-forage`; directly supported)
- **frost:** Sensitive to frost, though it keeps growing at temperatures close to 0 °C and tall plants can survive light frost. (`feedipedia-pigeon-pea-forage`; directly supported)
- **waterlogging:** Sensitive to waterlogging. (`feedipedia-pigeon-pea-forage`; directly supported)
- **soil preference:** Can grow on a wide range of soils, from sands to heavy black clays. (`feedipedia-pigeon-pea-forage`; directly supported)
- **salinity:** Has low tolerance of soil salinity, although some cultivars were reported to tolerate 6-12 dS/m. (`feedipedia-pigeon-pea-forage`; context-dependent)
- **shade:** Under shade it shows reduced growth and bears few pods. (`feedipedia-pigeon-pea-forage`; directly supported)
- **altitude:** Found from sea level to an altitude of 2000 m. (`feedipedia-pigeon-pea-forage`; context-dependent)
- **duration:** Described as a 'long-duration legume' in the Machakos cropping-systems experiment. (`rao-mathuva-2000`; directly supported)

Reported for a named region:

- Pigeon pea was the long-duration legume, both rotated and intercropped with maize, in a cropping-systems experiment at the ICRAF research station at Machakos, Kenya, from November 1989 to February 1996. (`rao-mathuva-2000`; applies to: One research station at Machakos, 1989-1996.)
- In that experiment pigeon pea was affected by pests and diseases, which the authors say indicates a need for integrated pest management. (`rao-mathuva-2000`; applies to: One research station at Machakos, 1989-1996.)
- Kenya is listed among the main producers of pigeon peas, with 0.28 million tonnes in 2014. (`feedipedia-pigeon-pea-forage`; applies to: Kenya as a whole, 2014; no county is named.)

Not established by the sources read:

- **crop coefficients:** The FAO crop coefficient table has no row for pigeon pea. Its legume group values were not applied, because pigeon pea is a tall, deep-rooted perennial shrub unlike the crops in that group.
- **depletion fraction:** The FAO rooting-depth table has no row for pigeon pea.
- **growing period:** No source read gives a growing period in days. One calls it 'long-duration'.
- **seasonal water need:** The FAO table of indicative crop water needs has no row for pigeon pea.
- **yield response factor:** The FAO table of yield response factors has no row for pigeon pea.
- **nitrogen left for next crop:** One source reports that 88 % of fixed nitrogen goes into pods and seeds; none says how much remains for a following crop.

### Sorghum (grain)

**What is known.** Sorghum uses less water at mid-season than maize (crop coefficient 1.00 to 1.10 against 1.20), needs roughly 450 to 650 mm over about 120 to 130 days, and is rated low in sensitivity to drought. It roots deeply and tolerates short waterlogging.

**Why it matters.** It is the cereal the sources describe as coping better than maize when rain is short, which makes it a natural comparison in a dry season.

**Evidence.** Water-use values come from two FAO irrigation handbooks. Climate, soil and drought statements come from a Feedipedia datasheet.

**What is uncertain.** No source read places sorghum at the pilot site, and one describes it as widespread only up to 1000 m, below the pilot grid cell's average elevation. Its rainfall range could not be recorded because the source is ambiguous.

**Region-specific?** No. These are general characteristics of the species.

| Characteristic | Kind | Value | Unit | Source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Crop coefficient, initial stage | Typical | 0.3 | dimensionless | `fao-56`, Chapter 6, Table 12, group row 'i. Cereals', and the text following the table | Context-dependent |
| Crop coefficient, mid-season | Typical | 1 to 1.1 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Sorghum - grain' | Directly supported |
| Crop coefficient, end of season | Typical | 0.55 | dimensionless | `fao-56`, Chapter 6, Table 12, row 'Sorghum - grain' | Directly supported |
| Maximum height | Typical | 1 to 2 | m | `fao-56`, Chapter 6, Table 12, row 'Sorghum - grain', column 'Maximum Crop Height' | Directly supported |
| Maximum rooting depth | Typical | 1 to 2 | m | `fao-56`, Chapter 8, Table 22, row 'Sorghum - grain' | Directly supported |
| Depletion fraction (p) | Typical | 0.55 | fraction | `fao-56`, Chapter 8, Table 22, row 'Sorghum - grain' | Directly supported |
| Yield response factor (Ky) | Typical | 0.9 | dimensionless | `fao-56`, Chapter 8, Table 24, row 'Sorghum' | Directly supported |
| Growing period | Typical | 120 to 130 | day | `fao-tm3`, Chapter 3, Table 6, row 'Sorghum' | Context-dependent |
| Seasonal water use | Typical | 450 to 650 | mm/total growing period | `fao-tm3`, Chapter 3, Table 14, row 'Sorghum/Millet' | Context-dependent |
| Temperature | Stage-specific (seedling) | 25 to 30 | degC | `feedipedia-sorghum-forage`, Section 'Distribution', first paragraph | Context-dependent |
| Temperature | Stage-specific (growth after the seedling stage (day-temperature)) | 30 | degC | `feedipedia-sorghum-forage`, Section 'Distribution', first paragraph | Context-dependent |
| Soil pH | Optimal | 5.5 to 7.5 | pH | `feedipedia-sorghum-forage`, Section 'Distribution', first paragraph | Context-dependent |

Sourced statements:

- **drought:** Sorghum is tolerant to drought because of its root system. It performs better than maize in drought conditions and so grows in stress-prone semi-arid areas unsuitable for maize. (`feedipedia-sorghum-forage`; directly supported)
- **drought sensitivity:** Sensitivity to drought: low. (`fao-tm3`; context-dependent)
- **waterlogging:** Somewhat tolerant to waterlogging for short periods; sensitive to sustained flooding. (`feedipedia-sorghum-forage`; directly supported)
- **frost:** Sensitive to frost. (`feedipedia-sorghum-forage`; directly supported)
- **soil preference:** Grows best on deep, well-drained loamy clay. (`feedipedia-sorghum-forage`; context-dependent)
- **root system:** Roots are adventitious, and the root system can extend from the top 90 cm of soil to twice that depth. (`feedipedia-sorghum-forage`; directly supported)
- **rainfall note:** The source describes optimal conditions as 'with less than 400-750 mm annual rainfall'. The wording is ambiguous, so no rainfall range is recorded as a number. (`feedipedia-sorghum-forage`; provisional)
- **weed striga:** In Africa the parasitic weed Striga hermonthica attaches itself to the roots and is particularly noxious to sorghum. (`feedipedia-sorghum-forage`; directly supported)
- **salinity:** Rated moderately tolerant to salinity. Yield first declines at a soil saturation-extract conductivity of 6.8 dS/m. (`fao-56`; directly supported)
- **altitude:** Described as widespread from sea level up to an altitude of 1000 m. (`feedipedia-sorghum-forage`; context-dependent)

Not established by the sources read:

- **annual rainfall range:** The only statement found is ambiguously worded and was not turned into a number.
- **soil ph tolerated:** Only a preferred pH range was found; no outer limits.
- **base temperature:** No source read gives a base or other cardinal temperature for development.
- **regional use:** No source read reports sorghum being grown at or near the pilot site.
- **suitability above 1000 m:** One source describes sorghum as widespread up to 1000 m, while the NASA grid cell for the pilot site averages 1,328 m. No source read resolves whether sorghum suits that elevation.

Assumptions:

- The FAO rows for 'Sorghum - grain' and 'Sorghum' are taken to describe grain sorghum as a smallholder would grow it.


## Growth-stage examples

From FAO Irrigation and Drainage Paper 56, Table 11. These are examples for the
region and planting period the table names. **None is a local value for the
pilot site**, and the source itself says stage lengths "may vary substantially
from region to region".

| Crop (as the source names it) | Region | Planting | Initial | Development | Mid-season | Late | Stages sum | Printed total | Consistent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Beans (dry) | Continental Climates | May/June | 20 | 30 | 40 | 20 | 110 | 110 | yes |
| Beans (dry) | Pakistan, Calif. | June | 15 | 25 | 35 | 20 | 95 | 95 | yes |
| Green gram, cowpeas | Mediterranean | March | 20 | 30 | 30 | 20 | 100 | 110 | **no** |
| Maize (grain) | Arid Climate | Dec/Jan | 25 | 40 | 45 | 30 | 140 | 140 | yes |
| Maize (grain) | East Africa (alt.) | April | 30 | 50 | 60 | 40 | 180 | 180 | yes |
| Sorghum | Arid Region | Mar/April | 20 | 35 | 45 | 30 | 130 | 140 | **no** |
| Sorghum | USA, Pakis., Med. | May/June | 20 | 35 | 40 | 30 | 125 | 130 | **no** |

Three rows are internally inconsistent in the source: the four stages do not
add up to the printed total. Both figures are stored exactly as printed, the
rows are marked provisional, and neither was corrected. The loader refuses an
inconsistent row unless the discrepancy is declared.

## Soil knowledge

### Four kinds of soil information, never merged

| Category | What it is | In this project today |
| --- | --- | --- |
| **A. Measured locally** | Measured in the field in question | None. No field measurement exists. |
| **B. Mapped estimate** | Read from an authoritative soil map | None. No soil map has been integrated. |
| **C. User-entered** | Stated by the user, not measured here | The intended route for texture, drainage and pH (phase A5). |
| **D. Demonstration assumption** | Assumed so that a demonstration can run | None yet. Any that is added must be labelled as assumed. |

Two further categories keep other things from being mistaken for the above:
**reference values** (typical values for a soil type, from literature, such as
the table below) and **derived** values (calculated from other soil values by a
stated formula).

`SoilInformation.evidence_categories()` reports the category of every item, and
`SoilInformation.unmeasured()` lists everything that is not a local
measurement. A soil value whose provenance is satellite data, reanalysis or
model output is refused: **soil properties are never inferred from NASA
temperature or rainfall.**

### Soil-water reference values by texture class

From FAO Irrigation and Drainage Paper 56, Table 19. Typical values for a soil
type. **Not a measurement of any field.**

| Texture class | Field capacity (m³/m³) | Wilting point (m³/m³) | Available water (m³/m³) | Confidence |
| --- | --- | --- | --- | --- |
| Sand | 0.07 to 0.17 | 0.02 to 0.07 | 0.05 to 0.11 | Directly supported |
| Loamy sand | 0.11 to 0.19 | 0.03 to 0.10 | 0.06 to 0.12 | Directly supported |
| Sandy loam | 0.18 to 0.28 | 0.06 to 0.16 | 0.11 to 0.15 | Directly supported |
| Loam | 0.20 to 0.30 | 0.07 to 0.17 | 0.13 to 0.18 | Directly supported |
| Silt loam | 0.22 to 0.36 | 0.09 to 0.21 | 0.13 to 0.19 | Directly supported |
| Silt | 0.28 to 0.36 | 0.12 to 0.22 | 0.16 to 0.20 | Directly supported |
| Sandy clay loam | not in the source | not in the source | not in the source | — |
| Clay loam | not in the source | not in the source | not in the source | — |
| Silty clay loam | 0.30 to 0.37 | 0.17 to 0.24 | 0.13 to 0.18 | Directly supported |
| Sandy clay | not in the source | not in the source | not in the source | — |
| Silty clay | 0.30 to 0.42 | 0.17 to 0.29 | 0.13 to 0.19 | Provisional |
| Clay | 0.32 to 0.40 | 0.20 to 0.24 | 0.12 to 0.20 | Directly supported |

Three of the twelve USDA texture classes are not in the source table and are
left absent. The silty clay row contains a scanning error in FAO's HTML
edition ("0-30 - 0.42"), read here as 0.30 to 0.42 and marked provisional.

### Crop soil requirements held

| Topic | Held | Not held |
| --- | --- | --- |
| Soil pH | A range for five crops, of differing kinds (optimal, suitable or tolerated) | Cowpea; optimal pH for maize and common bean; tolerated limits for sorghum and pigeon pea |
| Drainage and waterlogging | A sourced statement for every crop | Any measure of how long each crop tolerates waterlogging |
| Texture preference | A sourced statement for five crops | Cowpea beyond "well drained"; any numeric limit |
| Salinity | An FAO rating and threshold for maize, sorghum, beans and cowpea; statements for pigeon pea and mung bean | — |
| Nutrients | Sensitivities and deficiencies for common bean | Every other crop; fertiliser needs for all |
| Organic matter | That common bean does better on soils rich in organic content | Any threshold |
| Soil depth | Rooting depths assume no restricting layer | The depth of soil at any site |

## Rotation relationships

Each relationship is one of four strengths. A tendency is not a rule.

| Strength | Meaning | Count |
| --- | --- | --- |
| Documented tendency | Measured across studies; varies by case | 6 |
| Site-specific finding | Reported for one place and period | 3 |
| General principle | Stated as guidance, not quantified | 4 |
| Unsupported | No adequate source was found | 2 |

| Relationship | Type | Strength | Applies to | Sources |
| --- | --- | --- | --- | --- |
| `cereal-after-grain-legume` | legume inclusion | documented tendency | Fabaceae, Poaceae | `franke-2018` |
| `fixed-nitrogen-leaves-with-the-grain` | nitrogen benefit | documented tendency | common-bean, pigeon-pea | `feedipedia-common-bean`, `feedipedia-pigeon-pea-forage` |
| `legume-benefit-is-not-only-nitrogen` | nitrogen benefit | documented tendency | Fabaceae, Poaceae | `franke-2018` |
| `legume-effects-on-cereal-pests` | pest disease carryover | unsupported | Fabaceae, Poaceae | `franke-2018` |
| `legumes-and-soil-organic-matter` | soil organic matter | documented tendency | Fabaceae | `franke-2018` |
| `legumes-and-striga` | weed pressure | documented tendency | sorghum, Fabaceae | `feedipedia-sorghum-forage`, `franke-2018` |
| `machakos-legume-pests` | pest disease carryover | site specific finding | cowpea, pigeon-pea | `rao-mathuva-2000` |
| `machakos-maize-after-cowpea` | legume inclusion | site specific finding | cowpea, maize | `rao-mathuva-2000` |
| `machakos-maize-with-pigeon-pea` | legume inclusion | site specific finding | maize, pigeon-pea | `rao-mathuva-2000` |
| `rooting-depth-diversity` | rooting diversity | general principle | crops in general | `fao-ca-diversification` |
| `rotation-breaks-crop-specific-pests` | same crop repetition | general principle | crops in general | `fao-ca-diversification` |
| `rotation-diversity-in-general` | rotation diversity | general principle | crops in general | `fao-ca-diversification` |
| `same-family-repetition` | same family repetition | unsupported | Fabaceae, Poaceae | `fao-ca-diversification` |
| `soil-cover-between-crops` | soil cover | general principle | crops in general | `fao-ca-soil-cover` |
| `sorghum-and-maize-under-drought` | water use contrast | documented tendency | maize, sorghum | `fao-tm3`, `feedipedia-sorghum-forage` |

### What each one says

#### `cereal-after-grain-legume`

Across 199 observations in sub-Saharan Africa, a cereal grown after a grain legume yielded on average 0.49 t/ha more grain than the same cereal grown continuously, an increase of 41 %. The effect is highly significant, but its variability is large.

- **Scope:** Cereal-based systems in sub-Saharan Africa: a systematic review of 44 publications.
- **Known exceptions:** Effects were smaller in the humid forest and derived savannah of West Africa and in the Sudano-Sahelian zone. Maize responded more strongly than millet and sorghum, although cereal type and agro-ecological zone were confounded. Residual effects were stronger after soybean and groundnut than after cowpea.
- **Limitations:** An average across many sites. It is not a prediction for any one farm or season. Only the abstract was read. The review concerns yield, which this project does not predict; it is held as evidence that the rotation effect exists and varies.
- **What is uncertain:** The size of the effect varies widely between sites and the reasons are not well explained. It was weaker in the driest and the most humid zones, and weaker after cowpea than after soybean or groundnut.

#### `fixed-nitrogen-leaves-with-the-grain`

A legume that fixes nitrogen does not necessarily leave it in the field. Pigeon pea is reported to fix 40-97 kg N/ha/year in Africa, with 88 % used for the formation of pods and seeds. Common bean is described as less efficient in fixing nitrogen than other legumes.

- **Scope:** General descriptions of the two species; the pigeon pea figure is for Africa.
- **Known exceptions:** A legume grown as green manure and returned to the soil, instead of harvested for grain, would leave more nitrogen. No source read quantifies this for the crops here.
- **Limitations:** From secondary datasheets; the primary studies were not read. No source read gives the nitrogen left for a following crop under any conditions.
- **What is uncertain:** How much nitrogen any of these crops leaves behind under local conditions is not established by the sources read.

#### `legume-benefit-is-not-only-nitrogen`

Applying nitrogen fertiliser to the cereal reduces the benefit of a preceding legume, but at 60-120 kg N/ha the response still equalled 0.32 t/ha, or 59 % of the response with no nitrogen applied. The review concludes that effects other than nitrogen are important.

- **Scope:** Cereal-based systems in sub-Saharan Africa: a systematic review.
- **Known exceptions:** The review says grain legumes are unlikely to have a major influence on the availability of nutrients other than nitrogen and phosphorus, or on soil pH.
- **Limitations:** Only the abstract was read. The review calls for more research to explain the wide variability in nitrogen benefits between sites.
- **What is uncertain:** What the non-nitrogen effects are, and how large they are on a given farm, is not settled.

#### `legume-effects-on-cereal-pests`

That rotating a cereal with a grain legume reduces pests and diseases in the cereal is not established for sub-Saharan Africa. The review read says the impact is 'probably important' but that evidence is lacking, and that studies on nematodes are inconclusive, probably because legumes host some of the nematodes that harm maize.

- **Scope:** Sub-Saharan Africa, grain legume and cereal rotations.
- **Limitations:** Absence of evidence in one review is not evidence that there is no effect. Only the abstract was read.
- **What is uncertain:** Almost everything: which pests, which crop pairs, and how large any effect is. This needs local knowledge.

#### `legumes-and-soil-organic-matter`

Beneficial impacts of grain legumes on soil organic matter can occur if legumes contribute to greater overall cropping productivity, but studies generally report no such impacts.

- **Scope:** Sub-Saharan Africa, grain legumes in cereal-based systems.
- **Known exceptions:** The review allows that an effect can occur where the legume raises the productivity of the whole system.
- **Limitations:** Only the abstract was read. Concerns grain legumes harvested for seed, not cover crops or green manures.
- **What is uncertain:** An effect may occur where legumes raise overall productivity, and the finding does not cover cover crops or green manures.

#### `legumes-and-striga`

Evidence of impacts of grain legumes on weeds in sub-Saharan Africa is limited to striga. Separately, the parasitic weed Striga hermonthica is described as particularly noxious to sorghum in Africa.

- **Scope:** Sub-Saharan Africa; Africa in general for the sorghum statement.
- **Limitations:** The abstract read says the evidence concerns striga but does not state the size or direction of the effect. Neither source says whether striga is present at the pilot site.
- **What is uncertain:** The abstract does not say how large the effect is, and whether striga occurs at the pilot site is unknown.

#### `machakos-legume-pests`

In the Machakos experiment both cowpea and pigeon pea were affected by pests and diseases, which the authors say indicated the need for integrated pest management to realise the potential benefits of legume-based systems.

- **Scope:** One research station at Machakos, Kenya, November 1989 to February 1996.
- **Limitations:** The abstract does not name the pests or diseases. One station and one period.
- **What is uncertain:** Which pests and diseases, and how severe, is not stated in the abstract. Conditions may have changed since 1996.

#### `machakos-maize-after-cowpea`

At Machakos, maize grown in sequence with cowpea produced 17 % higher maize yields than continuous sole maize over the experiment.

- **Scope:** One research station at Machakos, Kenya, November 1989 to February 1996.
- **Known exceptions:** In the same experiment, maize rotated with pigeon pea yielded only marginally better than continuous maize.
- **Limitations:** One station and one seven-year period. Soil, varieties, management and the rainfall of each season are unknown to this project. Only the abstract was read. Held as evidence that the rotation effect occurred there. It is not a yield prediction.
- **What is uncertain:** The result is from one station between 1989 and 1996. How it varied between dry and wet seasons is not in the abstract.

#### `machakos-maize-with-pigeon-pea`

At Machakos, maize intercropped with pigeon pea produced 24 % higher maize yields than continuous sole maize, whereas maize rotated with pigeon pea yielded only marginally better.

- **Scope:** One research station at Machakos, Kenya, November 1989 to February 1996.
- **Known exceptions:** The gain came from growing the two crops together, not from growing them in sequence.
- **Limitations:** Intercropping is not rotation. This project models sequences of crops, so the 24 % finding does not transfer to a rotation. One station and one seven-year period. Only the abstract was read.
- **What is uncertain:** Why rotation with pigeon pea gave little benefit there is not explained in the abstract.

#### `rooting-depth-diversity`

Crops in rotation root at different soil depths and so explore different soil layers for nutrients; nutrients leached to deeper layers can be recycled by deeper-rooting crops.

- **Scope:** General guidance for conservation agriculture.
- **Limitations:** Stated as a principle, without measurements or conditions. Published rooting depths for the crops here assume no restricting soil layer.
- **What is uncertain:** The guidance gives no measurements. Whether deeper roots help depends on the depth and condition of the soil, which is unknown here.

#### `rotation-breaks-crop-specific-pests`

Crop rotation has a phytosanitary function: it prevents the carry-over of crop-specific pests and diseases from one crop to the next.

- **Scope:** General guidance for conservation agriculture.
- **Known exceptions:** Pests and diseases that are not specific to one crop are not covered by this statement.
- **Limitations:** Stated as a principle, without measurements, references or conditions. Names no pest, disease or crop.
- **What is uncertain:** The guidance names no pest or crop and gives no measurements. Which problems apply locally needs local knowledge.

#### `rotation-diversity-in-general`

The effects FAO lists for crop rotation include reduced risk of pest and weed infestations, better distribution of water and nutrients through the soil profile, increased nitrogen fixation through plant-soil symbionts, and increased humus formation.

- **Scope:** General guidance for conservation agriculture.
- **Known exceptions:** For grain legumes in sub-Saharan Africa, the review read reports generally no impact on soil organic matter, which qualifies the claim about humus.
- **Limitations:** A list of expected effects, without measurements, references or conditions. Written for conservation agriculture, which combines rotation with minimal tillage and permanent soil cover.
- **What is uncertain:** These are expectations, not measurements. At least one of them, building organic matter, is not borne out for grain legumes in the review read.

#### `same-family-repetition`

That growing crops of the same botanical family in succession carries over pests and diseases is widely asserted, but no source read for this knowledge base states it. The FAO guidance read speaks only of 'crop-specific' pests and diseases.

- **Scope:** No scope: the claim is not supported by the sources read.
- **Limitations:** This records a gap in the sources read, not a finding that the effect does not exist. A targeted search of plant-pathology literature would be needed to support or reject it for these families.
- **What is uncertain:** Whether the rule holds for cereals or for legumes here, and for which pests. This needs plant-pathology sources or local expertise.

#### `soil-cover-between-crops`

Keeping the soil covered protects it during fallow periods. A mulch layer inhibits evaporation of soil moisture and leads to greater infiltration of water, and the share of rain that infiltrates depends on the amount of cover.

- **Scope:** General guidance for conservation agriculture; the page mentions semi-arid regions as a case where cover crops are beneficial.
- **Limitations:** Stated as a principle, without measurements or conditions. The guidance does not address whether a semi-arid season leaves enough water to grow a cover crop. No crop from this knowledge base is named.
- **What is uncertain:** The guidance gives no measurements. How long each rotation leaves the soil bare here is unknown, because no local planting calendars are held.

#### `sorghum-and-maize-under-drought`

Sorghum performs better than maize in drought conditions and grows in stress-prone semi-arid areas unsuitable for maize. An FAO manual rates sensitivity to drought as low for sorghum and millet and medium-high for maize, and gives sorghum a lower indicative water need.

- **Scope:** General statements about the two species; the FAO classes are indicative and worldwide.
- **Limitations:** General statements, not a comparison made at the pilot site. One source describes sorghum as widespread only up to 1000 m, below the average elevation of the pilot grid cell.
- **What is uncertain:** No comparison was found for the pilot site, and one source places sorghum mainly below 1000 m.


### Three findings that go against common assumptions

1. **A legume does not automatically enrich the soil for the next crop.**
   Pigeon pea is reported to put 88 % of the nitrogen it fixes into pods and
   seeds, which leave the field at harvest.
2. **Grain legumes are generally not found to raise soil organic matter** in
   the sub-Saharan African studies reviewed.
3. **Keeping crops of the same family apart is not supported by any source
   read.** It is recorded as unsupported, and the tool will not apply it.

## Cropping systems a study actually compared

The Machakos experiment (Rao and Mathuva, 2000) grew and compared these
systems. They are the only rotations in the knowledge base that someone
actually grew, and two of them include a legume.

| System | Arrangement | Crops | Reported outcome (Machakos, 1989 to 1996) |
| --- | --- | --- | --- |
| Continuous sole maize | continuous | maize | The comparison baseline. The abstract gives no yield for it. |
| Maize rotated with cowpea | rotation | maize, cowpea | 17 % higher maize yields than continuous sole maize. Cowpea was affected by pests and diseases. |
| Maize intercropped with pigeon pea | intercrop | maize, pigeon-pea | 24 % higher maize yields than continuous sole maize. Pigeon pea was affected by pests and diseases. |
| Maize rotated with pigeon pea | rotation | maize, pigeon-pea | Maize yielded only marginally better than continuous sole maize. Pigeon pea was affected by pests and diseases. |

These are records of what was grown, **not recommendations**. The abstract
read does not give the details needed to turn them into a rotation plan:

- Which crop was grown in which rainy season.
- How long one full cycle of the system lasted.
- Varieties, planting dates, spacing and fertiliser use.
- Soil type and the rainfall of each season of the experiment.

Phase A4 must get those details from the farmer or another source before it
can build a rotation to compare. Together, continuous maize and the two
rotations give the three strategies the challenge suggests comparing, one of
them a plausible "existing rotation". Which system a given farmer uses today is
for the farmer to say.

The intercrop is kept separate. It produced the largest gain in maize yield,
but it grows both crops at once and cannot be modelled as a sequence.

## Rotation constraints

Stored for phase A4. **Nothing in A3 evaluates them.**

| Severity | Meaning | Count |
| --- | --- | --- |
| Hard | The evidence says the crop cannot succeed under the condition | 1 |
| Advisory | Worth warning about; not a prohibition | 6 |
| Context-dependent | Depends on variety, management or local detail | 6 |
| Unsupported | Commonly asserted, but no adequate source was found | 1 |

| Constraint | Severity | Applies to | Condition | Inputs A4 would need |
| --- | --- | --- | --- | --- |
| `frost-kills-maize` | hard | maize | Frost during the growing period. | `air_temperature_min` |
| `continuous-cereal-without-legume` | advisory | Poaceae | A rotation in which cereals follow cereals with no legume. | — |
| `frost-sensitive-crops` | advisory | common-bean, pigeon-pea, sorghum | Frost during the growing period. | `air_temperature_min` |
| `growing-period-longer-than-season` | advisory | common-bean, maize, sorghum | The crop's documented growing period exceeds the length of the season it is planted in. | `crop_cycle_length`, `precipitation` |
| `legume-needs-pest-management` | advisory | cowpea, pigeon-pea | Cowpea or pigeon pea included in the rotation. | — |
| `same-crop-in-succession` | advisory | crops in general | The same crop in two or more consecutive rotation slots. | — |
| `waterlogging-sensitive-crop-on-wet-soil` | advisory | common-bean, cowpea, maize, mung-bean, pigeon-pea | Soil the user describes as poorly drained, or a season wet enough to waterlog the field. | `precipitation` |
| `cold-stops-common-bean-growth` | context dependent | common-bean | Temperatures below 10 °C during the growing period. | `air_temperature_mean`, `air_temperature_min`, `crop_temperature_requirement` |
| `drought-at-flowering-maize` | context dependent | maize | A dry spell during the flowering period of the maize crop. | `precipitation` |
| `perennial-in-seasonal-rotation` | context dependent | pigeon-pea | Pigeon pea placed in a rotation slot that assumes one crop per season. | — |
| `seasonal-water-need-above-rainfall` | context dependent | common-bean, maize, sorghum | Indicative crop water use over the growing period is greater than the season's rainfall. | `crop_seasonal_water_requirement`, `precipitation_total` |
| `soil-ph-outside-documented-range` | context dependent | common-bean, maize, mung-bean, pigeon-pea, sorghum | Measured or user-supplied soil pH outside the crop's documented pH range. | `crop_soil_ph_requirement`, `soil_ph` |
| `temperature-outside-documented-range` | context dependent | common-bean, cowpea, maize, mung-bean, pigeon-pea, sorghum | Growing-season temperatures outside the crop's documented temperature range. | `air_temperature_max`, `air_temperature_mean`, `air_temperature_min`, `crop_temperature_requirement` |
| `same-family-in-succession` | unsupported | Fabaceae, Poaceae | Two crops of the same botanical family in consecutive rotation slots. | — |

A constraint may be classed as hard only if every piece of its evidence
directly supports it; the loader enforces this. The single hard constraint,
frost killing maize, rests on a categorical statement in its source. The source
does not give a temperature. In A3, treating 0 °C as frost was this project's
assumption; the A4 evidence audit replaced it with the ETCCDI frost-day
definition (daily minimum below 0 °C), and the constraint now says so.

### Plain-language explanations

- **`frost-kills-maize`** (hard). What a farmer would be told: "Frost kills maize. If frost occurs on your land during the growing season, maize is not a safe choice for that season. NASA's weather record covers a wide area and can miss frost in low-lying spots, so trust your own experience of frost on your fields."
- **`continuous-cereal-without-legume`** (advisory). What a farmer would be told: "Growing a cereal season after season without a legume usually means lower cereal yields than a rotation with a legume. Research in Africa, including a trial at Machakos, found this on average, but the size of the benefit varies a lot from place to place."
- **`frost-sensitive-crops`** (advisory). What a farmer would be told: "Frost damages sorghum, pigeon pea and common bean, though not equally. If frost occurs on your land in the season, expect losses."
- **`growing-period-longer-than-season`** (advisory). What a farmer would be told: "If a crop takes longer to mature than your rains usually last, it may run out of water before harvest. The growing periods we hold are general figures; a short-season variety can behave very differently."
- **`legume-needs-pest-management`** (advisory). What a farmer would be told: "In a long trial at Machakos, cowpea and pigeon pea were damaged by pests and diseases. If you add these crops, plan how you will manage pests, and ask a local adviser which ones to expect."
- **`same-crop-in-succession`** (advisory). What a farmer would be told: "Planting the same crop season after season gives its pests and diseases a chance to build up. Changing the crop breaks that cycle. Which problems matter on your land is something a local adviser can tell you."
- **`waterlogging-sensitive-crop-on-wet-soil`** (advisory). What a farmer would be told: "Maize, beans, cowpea, pigeon pea and mung bean do not cope well with standing water. On land that drains poorly, or in a very wet season, they are at risk. You know better than any map whether your field holds water."
- **`cold-stops-common-bean-growth`** (context dependent). What a farmer would be told: "Common bean stops growing in cold weather, below about 10 °C. Whether that matters here depends on how often and how long it gets that cold on your land during the season."
- **`drought-at-flowering-maize`** (context dependent). What a farmer would be told: "Maize suffers most if it runs short of water when it is flowering. Whether a dry spell hits that stage depends on when you plant and which variety you grow."
- **`perennial-in-seasonal-rotation`** (context dependent). What a farmer would be told: "Pigeon pea stays in the field much longer than maize or beans, often across more than one rainy season. A rotation plan needs to allow for that."
- **`seasonal-water-need-above-rainfall`** (context dependent). What a farmer would be told: "Each crop needs a certain amount of water to grow well. If a season's rain is well below that, the crop is likely to be short of water unless the soil stored water beforehand or you can irrigate. This is only a rough guide."
- **`soil-ph-outside-documented-range`** (context dependent). What a farmer would be told: "Each crop does best within a range of soil acidity. If your soil is outside that range the crop may struggle, but how much depends on the crop and the soil. A soil test is the only way to know your pH."
- **`temperature-outside-documented-range`** (context dependent). What a farmer would be told: "Each crop grows best within a range of temperatures. If your seasons are usually warmer or cooler than that range, the crop may do less well. This comparison uses averages over a wide area and cannot show short hot or cold spells."
- **`same-family-in-succession`** (unsupported). What a farmer would be told: "People often advise against following one crop with another from the same plant family. The sources behind this tool do not confirm that for these crops, so the tool does not apply it. Ask a local adviser."

## Farmer priorities

Categories and what evidence each would need. **No weights are assigned**;
weights come from the farmer. **No prices, costs or returns are held or
estimated.**

| Priority | Origin | Evidence held | What would be needed to assess it |
| --- | --- | --- | --- |
| Water conservation | Official challenge text | partial | Seasonal crop water use for every crop in the rotation, calculated for the local climate, together with the season's rainfall. A published water-need range alone is not enough. |
| Nitrogen-fixing potential | Official challenge text | partial | Which crops fix nitrogen, and how much of it remains in the field after harvest for the following crop under local conditions. |
| Erosion reduction | Official challenge text | not available | How long each rotation leaves the soil bare, the slope of the field, and how intense the rain is when the soil is bare. |
| Organic matter improvement | Official challenge text | partial | Measured change in soil organic matter under each rotation, or the amount of residue each rotation returns to the soil. |
| Forage value | Official challenge text | not available | Forage yield and feed quality of each crop under local conditions, and whether the farmer keeps livestock. |
| Market and economic considerations | Official challenge text | not available | Current local prices, costs and demand for each crop. These change from season to season and place to place. |
| Pest and disease cycle disruption | Official challenge text | partial | Which pests and diseases affect each crop locally, which crops host them, and how long they survive without a host. |
| Resilience across dry and wet seasons | CropShift addition | partial | A comparison of each rotation under dry, typical and wet historical seasons, using crop water use, drought sensitivity and the validated NASA record. This is the work of phase A4. |
| Crop diversity | CropShift addition | available | The crops in the rotation and the botanical family of each. |
| Operational simplicity | CropShift addition | not available | Labour, equipment and timing demands of each crop on the farm in question. |

Three priorities have no supporting evidence and must be shown as "needs local
information", never scored: forage value, market and economic considerations,
and operational simplicity.

## Interfaces for phase A4

Each crop characteristic is paired with the input it would be compared with.
These are contracts only: A3 performs no comparison.

| Crop characteristic | Compared with | Input comes from | Available today | Main limitation |
| --- | --- | --- | --- | --- |
| Annual rainfall | `precipitation_total` | NASA data layer (A2) | yes | An annual total hides how rain is split between seasons; the pilot site has two rainy seasons a year. |
| Depletion fraction (p) | `soil_available_water_capacity`, `soil_field_capacity`, `soil_wilting_point` | The user or a soil source | no | Soil water characteristics must come from the user or a soil source. Reference values by texture class are typical values, not measurements. |
| Growing period | `precipitation` | NASA data layer (A2) | yes | No rule for the start and end of a rainy season has been adopted yet. Phase A4 must define and cite one. |
| Crop coefficient, end of season | `reference_evapotranspiration` | A calculation A4 must define | no | Reference evapotranspiration is not retrieved; it must be calculated, and the standard method needs wind speed, which the data layer does not yet retrieve. |
| Crop coefficient, initial stage | `reference_evapotranspiration` | A calculation A4 must define | no | Reference evapotranspiration is not retrieved; it must be calculated, and the standard method needs wind speed, which the data layer does not yet retrieve. |
| Crop coefficient, mid-season | `reference_evapotranspiration` | A calculation A4 must define | no | Reference evapotranspiration is not retrieved; it must be calculated, and the standard method needs wind speed, which the data layer does not yet retrieve. |
| Maximum rooting depth | `soil_available_water_capacity`, `soil_field_capacity`, `soil_wilting_point` | The user or a soil source | no | Soil water characteristics must come from the user or a soil source; they are never taken from NASA weather data. |
| Seasonal water use | `precipitation_total` | NASA data layer (A2) | yes | The crop figure is evapotranspiration, not rainfall demand. The two are not directly comparable without a water balance. |
| Soil pH | `soil_ph` | The user or a soil source | no | Soil pH must be measured or supplied by the user. It is never inferred from NASA temperature or rainfall. |
| Temperature | `air_temperature_mean`, `air_temperature_max`, `air_temperature_min` | NASA data layer (A2) | yes | A monthly or seasonal mean cannot show short spells of heat or cold, which are what damage crops. |
| Yield response factor (Ky) | `reference_evapotranspiration` | A calculation A4 must define | no | Needs a calculated water deficit, which does not exist yet. |

Limits that apply to every pairing with NASA data:

* A monthly or seasonal mean cannot show short spells of heat or cold.
* Rainfall is not the water available to a crop, and never includes irrigation.
* Nothing about disease incidence or yield can be read from temperature or
  rainfall.
* NASA values describe a grid cell tens of kilometres wide at its average
  elevation (1,328 m for the pilot cell).

## Limitations of the knowledge base

* **Secondary sources for climate and soil.** Temperature, rainfall and pH
  ranges come from Feedipedia datasheets, which compile primary sources that
  were not read. FAO EcoCrop, the intended primary source, was not accessible.
* **Standard conditions.** All water-use values describe well-watered,
  well-managed crops. Rain-fed smallholder crops use less and differ in timing.
* **Shared and group values.** Cowpea and mung bean share one FAO row. Initial
  crop coefficients are group values for all cereals or all legumes.
* **Abstracts only.** The two journal articles were read in abstract only.
* **Thin regional evidence.** One experiment, at one station, from 1989 to
  1996, for three of the six crops.
* **Missing water data.** Pigeon pea has no crop coefficient, growing period or
  water need. Cowpea and mung bean have no growing period or seasonal need.
* **No temperature thresholds for stress.** No heat-stress threshold or base
  temperature was found for any crop.
* **No pests or diseases by name.** Nothing is held about which pests affect
  which crops locally.
* **No economics.** No prices, costs, labour or market information.
* **No local calendars.** Planting and harvest dates for the pilot region are
  not held, so bare-soil periods cannot yet be assessed.
* **Not reviewed by an agronomist.** The knowledge base was compiled during a
  hackathon and has had no expert review.

## Using the knowledge base

```python
from src.crop_knowledge import load_knowledge_base
from src.models import RequirementBasis, SoilTextureClass

kb = load_knowledge_base()                       # local files only; no network

maize = kb.get_crop("maize")
maize.requirements_for("crop_seasonal_water_requirement")       # 500 to 800 mm
maize.requirements_for("crop_temperature_requirement", RequirementBasis.OPTIMAL)
maize.is_unknown("heat_stress_threshold")        # True: never guessed

kb.relationships_for("maize")                    # by crop, by family, or general
kb.documented_rotations(with_legume=True)        # rotations a study actually grew
kb.constraints_for("pigeon-pea")
kb.soil_reference(SoilTextureClass.LOAM)         # or None if not in the source
kb.confidence_summary()                          # claims at each confidence level
kb.unknowns()                                    # what is not established, per crop
```

The files are plain JSON under `data/knowledge/`, validated on load:

| File | Contents |
| --- | --- |
| `manifest.json` | Schema version, knowledge-base version, status, file list |
| `evidence_registry.json` | Sources |
| `crops.json` | Families, crop profiles, growth-stage examples |
| `soil_reference.json` | Soil-water reference values by texture class |
| `rotation_relationships.json` | Relationships, constraints and documented cropping systems |
| `farmer_priorities.json` | Priority definitions |
| `variable_mappings.json` | Interface contracts for A4 |

To add or change a value: edit the JSON, cite a source that is in the
registry, give the locator and a confidence level, and run the tests. The
loader rejects a claim with no source, a "directly supported" claim whose
source was not read, a hard constraint without direct evidence, contradictory
ranges, wrong units and impossible values.
