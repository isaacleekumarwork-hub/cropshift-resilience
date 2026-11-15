# Evidence registry

Every source behind the agronomic knowledge base, how it was checked, and how
much rests on it. Generated from `data/knowledge/evidence_registry.json` on
15 November 2026; the data file is the authority.

## How sources were verified

All sources were read on 14 November 2026, during the hackathon. No value in
the knowledge base comes from the AI assistant's own knowledge: each was read
from the page or table named beside it.

| Review status | Meaning | Sources |
| --- | --- | --- |
| `content_read` | The cited tables or passages were read. | 11 |
| `abstract_read` | Only the published abstract was read; bibliographic details were confirmed against the Crossref record for the DOI. | 2 |
| `metadata_only` | Existence confirmed, content not read. | 0 |
| `not_verified` | Not checked. | 0 |

A claim may be marked *directly supported* only if its source was read. The
loader enforces this.

## Confidence classification

Words, not probabilities. No statistical model lies behind them.

| Level | Meaning | Claims |
| --- | --- | --- |
| Directly supported | The source states it for this crop or case. | 118 |
| Context-dependent | Stated, but for conditions that may not apply: a shared table row, an unspecified measure, a secondary compilation, a general principle. | 79 |
| Provisional | Indirect, ambiguous or interpreted: a source row that is internally inconsistent, or a scanning error that had to be read. | 5 |
| Insufficient evidence | No adequate source was found. The claim is recorded as unsupported. | 3 |
| **Total** | | **205** |

## Sources

| ID | Type | Review | Claims resting on it |
| --- | --- | --- | --- |
| `fao-56` | fao publication | content read | 54 |
| `fao-ca-diversification` | fao web resource | content read | 6 |
| `fao-ca-soil-cover` | fao web resource | content read | 1 |
| `fao-giews-kenya` | fao web resource | content read | 0 |
| `fao-tm3` | fao publication | content read | 12 |
| `feedipedia-common-bean` | compiled datasheet | content read | 22 |
| `feedipedia-cowpea-forage` | compiled datasheet | content read | 13 |
| `feedipedia-maize-forage` | compiled datasheet | content read | 16 |
| `feedipedia-mung-bean` | compiled datasheet | content read | 18 |
| `feedipedia-pigeon-pea-forage` | compiled datasheet | content read | 23 |
| `feedipedia-sorghum-forage` | compiled datasheet | content read | 17 |
| `franke-2018` | peer reviewed article | abstract read | 6 |
| `rao-mathuva-2000` | peer reviewed article | abstract read | 17 |

`fao-giews-kenya` supports no claim inside the knowledge base. It is cited by
the pilot site description in `src/pilot_sites.py`.

### `fao-56`

**Crop evapotranspiration: Guidelines for computing crop water requirements. FAO Irrigation and Drainage Paper 56**

- **Citation:** Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). Crop evapotranspiration: Guidelines for computing crop water requirements. FAO Irrigation and Drainage Paper 56. Rome: Food and Agriculture Organization of the United Nations. ISBN 92-5-104219-5. https://www.fao.org/4/x0490e/x0490e00.htm
- **Institution:** Food and Agriculture Organization of the United Nations (FAO)
- **Accessed:** 14 November 2026
- **Read:** Chapter 6, Table 11: lengths of crop development stages; Chapter 6, Table 12: single crop coefficients and mean maximum plant heights, with footnotes; Chapter 7, Table 19: typical soil water characteristics for different soil types; Chapter 8, Table 22: maximum effective rooting depth and soil water depletion fraction; Chapter 8, Table 23: salt tolerance of crops, with its rating key; Chapter 8, Table 24: seasonal yield response functions
- **Geographic scope:** Global guidance. Table 12 values are for non-stressed, well-managed crops in sub-humid climates. Table 11 rows are examples for the regions the table names.
- **Crop scope:** Many field crops. Rows used here: maize (grain), sorghum (grain), beans (dry) and pulses, green gram and cowpeas.
- **How it was checked:** Tables read on 14 Nov 2026 from FAO's HTML edition. Title, authors, year and ISBN taken from its title page.
- **Limitations:**
  - FAO states that the HTML edition was produced by optical character recognition. One value used from Table 19 contains a visible scanning error.
  - Values describe standard conditions: a well-watered, well-managed, disease-free crop. Rain-fed smallholder crops usually differ.
  - The source says stage lengths 'may vary substantially from region to region' and urges users to obtain local information.
  - There is no row for pigeon pea. Cowpea and green gram share a single row.

### `fao-ca-diversification`

**Conservation Agriculture in practice: Species diversification**

- **Citation:** Food and Agriculture Organization of the United Nations. Conservation Agriculture in practice: Species diversification. https://www.fao.org/conservation-agriculture/in-practice/species-diversification/en/ (undated web page, accessed 14 November 2026)
- **Institution:** Food and Agriculture Organization of the United Nations (FAO)
- **Accessed:** 14 November 2026
- **Read:** Section 'Crop rotation', including 'The effects of crop rotation'
- **Geographic scope:** Global guidance, not specific to any region.
- **Crop scope:** Crops in general. No crop or family is named.
- **How it was checked:** Page read on 14 Nov 2026. The page carries no date or author.
- **Limitations:**
  - General guidance. It gives no measurements, no references and no conditions under which the effects hold.
  - Written for conservation agriculture systems, which combine rotation with minimal tillage and soil cover.
  - Speaks of 'crop-specific' pests and diseases; it says nothing about crops of the same botanical family.

### `fao-ca-soil-cover`

**Conservation Agriculture in practice: Soil organic cover**

- **Citation:** Food and Agriculture Organization of the United Nations. Conservation Agriculture in practice: Soil organic cover. https://www.fao.org/conservation-agriculture/in-practice/soil-organic-cover/en/ (undated web page, accessed 14 November 2026)
- **Institution:** Food and Agriculture Organization of the United Nations (FAO)
- **Accessed:** 14 November 2026
- **Read:** Opening section on keeping the soil covered and the uses of cover crops
- **Geographic scope:** Global guidance; mentions semi-arid regions as a case where cover crops are beneficial.
- **Crop scope:** Cover crops and crop residues in general. No crop from this knowledge base is named.
- **How it was checked:** Page read on 14 Nov 2026. The page carries no date or author.
- **Limitations:**
  - General guidance. It gives no measurements, no references and no conditions under which the effects hold.
  - Does not address whether enough water is available to grow a cover crop in a semi-arid season.

### `fao-giews-kenya`

**GIEWS Country Brief: Kenya (reference date 4 May 2026)**

- **Citation:** FAO Global Information and Early Warning System on Food and Agriculture. GIEWS Country Brief: Kenya. Reference date 4 May 2026. https://www.fao.org/giews/countrybrief/country.jsp?code=KEN (accessed 14 November 2026)
- **Institution:** FAO Global Information and Early Warning System on Food and Agriculture (GIEWS)
- **Accessed:** 14 November 2026
- **Read:** Food security snapshot: text on the 2026 long rains and the 2025 short rains
- **Geographic scope:** Kenya, described by broad zones such as 'marginal bimodal rainfall southeastern and coastal areas'.
- **Crop scope:** Mentions maize and seasonal crops in general.
- **How it was checked:** Page read on 14 Nov 2026. Reference date taken from the page.
- **Limitations:**
  - A periodic brief: the page is replaced by newer editions, so the text read may no longer be online.
  - Describes broad zones and does not name Machakos. Placing the pilot site in the south-eastern marginal zone is this project's assumption.

### `fao-tm3`

**Irrigation Water Management: Irrigation Water Needs. Training manual no. 3**

- **Citation:** Brouwer, C., & Heibloem, M. (1986). Irrigation Water Management: Irrigation Water Needs. Training manual no. 3. Rome: Food and Agriculture Organization of the United Nations. https://www.fao.org/4/s2022e/s2022e00.htm
- **Institution:** Food and Agriculture Organization of the United Nations (FAO), with the International Institute for Land Reclamation and Improvement
- **Accessed:** 14 November 2026
- **Read:** Chapter 3, Table 6: indicative values of the total growing period; Chapter 3, Table 14: indicative values of crop water needs and sensitivity to drought, with its introduction
- **Geographic scope:** Global, indicative. Not specific to any region.
- **Crop scope:** Major field crops. Rows used here: maize (grain), sorghum, bean (dry), and the shared sorghum/millet row.
- **How it was checked:** Tables read on 14 Nov 2026 from FAO's HTML edition. Title, authors and year taken from its title page.
- **Limitations:**
  - The source says its water-need values 'provide a rough estimate and should only be used if the crop water needs cannot be calculated more accurately'.
  - Published in 1986; newer varieties may have different growing periods.
  - Sorghum and millet share one row for water need. There are no rows for cowpea, pigeon pea or mung bean.

### `feedipedia-common-bean`

**Common bean (Phaseolus vulgaris). Feedipedia datasheet**

- **Citation:** Heuzé V., Tran G., Nozière P., Lebas F., 2015. Common bean (Phaseolus vulgaris). Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO. https://www.feedipedia.org/node/266 Last updated on October 20, 2015, 14:50
- **Institution:** Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO
- **Accessed:** 14 November 2026
- **Read:** Taxonomic information; Description; Distribution; Environmental impact
- **Geographic scope:** Global description of the species.
- **Crop scope:** Phaseolus vulgaris in general; no cultivar detail.
- **How it was checked:** Sections read on 14 Nov 2026. Citation copied from the datasheet's own 'Datasheet citation' line.
- **Limitations:**
  - A secondary compilation written for animal feeding. It quotes primary sources that were not read here.
  - Ranges are stated without the measurement basis, for example which temperature average is meant.
  - Feedipedia's terms of reuse were not located; only facts and short quotations are used, with attribution.

### `feedipedia-cowpea-forage`

**Cowpea (Vigna unguiculata) forage. Feedipedia datasheet**

- **Citation:** Heuzé V., Tran G., Nozière P., Bastianelli D., Lebas F., 2015. Cowpea (Vigna unguiculata) forage. Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO. https://www.feedipedia.org/node/233 Last updated on October 20, 2015, 16:20
- **Institution:** Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO
- **Accessed:** 14 November 2026
- **Read:** Taxonomic information; Description; Distribution; Environmental impact
- **Geographic scope:** Global description of the species.
- **Crop scope:** Vigna unguiculata in general, with emphasis on forage use; no cultivar detail.
- **How it was checked:** Sections read on 14 Nov 2026. Citation copied from the datasheet's own 'Datasheet citation' line.
- **Limitations:**
  - A secondary compilation written for animal feeding. It quotes primary sources that were not read here.
  - Gives no soil pH range for cowpea.
  - Feedipedia's terms of reuse were not located; only facts and short quotations are used, with attribution.

### `feedipedia-maize-forage`

**Maize green forage. Feedipedia datasheet**

- **Citation:** Heuzé V., Tran G., Edouard N., Lebas F., 2017. Maize green forage. Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO. https://www.feedipedia.org/node/358 Last updated on June 21, 2017, 10:16
- **Institution:** Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO
- **Accessed:** 14 November 2026
- **Read:** Taxonomic information; Description; Distribution
- **Geographic scope:** Global description of the species.
- **Crop scope:** Zea mays in general, written about maize grown for forage; no cultivar detail.
- **How it was checked:** Sections read on 14 Nov 2026. Citation copied from the datasheet's own 'Datasheet citation' line. The companion 'Maize grain' datasheet gives the same climate and soil figures.
- **Limitations:**
  - A secondary compilation written for animal feeding and about forage maize. It quotes primary sources that were not read here.
  - Does not define the 'average day-temperature' it reports or name the primary source for it.
  - Feedipedia's terms of reuse were not located; only facts and short quotations are used, with attribution.

### `feedipedia-mung-bean`

**Mung bean (Vigna radiata). Feedipedia datasheet**

- **Citation:** Heuzé V., Tran G., Bastianelli D., Lebas F., 2015. Mung bean (Vigna radiata). Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO. https://feedipedia.org/node/235 Last updated on July 3, 2015, 10:04
- **Institution:** Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO
- **Accessed:** 14 November 2026
- **Read:** Common names; Taxonomic information; Description; Distribution; Environmental impact
- **Geographic scope:** Global description of the species. The datasheet notes that mung bean 'is not a major crop' in Africa.
- **Crop scope:** Vigna radiata in general; no cultivar detail.
- **How it was checked:** Sections read on 14 Nov 2026. Citation copied from the datasheet's own 'Datasheet citation' line.
- **Limitations:**
  - A secondary compilation written for animal feeding. It quotes primary sources that were not read here.
  - Gives no growing period in days.
  - Feedipedia's terms of reuse were not located; only facts and short quotations are used, with attribution.

### `feedipedia-pigeon-pea-forage`

**Pigeon pea (Cajanus cajan) forage. Feedipedia datasheet**

- **Citation:** Heuzé V., Thiollet H., Tran G., Delagarde R., Bastianelli D., Lebas F., 2017. Pigeon pea (Cajanus cajan) forage. Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO. https://feedipedia.org/node/22444 Last updated on March 8, 2017, 11:10
- **Institution:** Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO
- **Accessed:** 14 November 2026
- **Read:** Taxonomic information; Description; Distribution; Environmental impact
- **Geographic scope:** Global description of the species, with production figures by country for 2014.
- **Crop scope:** Cajanus cajan in general, with emphasis on forage use; no cultivar detail.
- **How it was checked:** Sections read on 14 Nov 2026. Citation copied from the datasheet's own 'Datasheet citation' line.
- **Limitations:**
  - A secondary compilation written for animal feeding. It quotes primary sources that were not read here.
  - Gives no growing period in days and no crop coefficient.
  - Feedipedia's terms of reuse were not located; only facts and short quotations are used, with attribution.

### `feedipedia-sorghum-forage`

**Sorghum forage. Feedipedia datasheet**

- **Citation:** Heuzé V., Tran G., Giger-Reverdin S., Lebas F., 2015. Sorghum forage. Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO. https://www.feedipedia.org/node/379 Last updated on October 7, 2015, 17:09
- **Institution:** Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO
- **Accessed:** 14 November 2026
- **Read:** Taxonomic information; Description; Distribution
- **Geographic scope:** Global description of the species.
- **Crop scope:** Sorghum bicolor in general, written about sorghum grown for forage; no cultivar detail.
- **How it was checked:** Sections read on 14 Nov 2026. Citation copied from the datasheet's own 'Datasheet citation' line.
- **Limitations:**
  - A secondary compilation written for animal feeding and about forage sorghum. It quotes primary sources that were not read here.
  - Its sentence on annual rainfall is ambiguously worded, so no rainfall range is taken from it.
  - Feedipedia's terms of reuse were not located; only facts and short quotations are used, with attribution.

### `franke-2018`

**Sustainable intensification through rotations with grain legumes in Sub-Saharan Africa: A review**

- **Citation:** Franke, A. C., van den Brand, G. J., Vanlauwe, B., & Giller, K. E. (2018). Sustainable intensification through rotations with grain legumes in Sub-Saharan Africa: A review. Agriculture, Ecosystems & Environment, 261, 172-185. https://doi.org/10.1016/j.agee.2017.09.029
- **DOI:** 10.1016/j.agee.2017.09.029
- **Institution:** Published in Agriculture, Ecosystems & Environment (Elsevier)
- **Accessed:** 14 November 2026
- **Read:** Abstract
- **Geographic scope:** Sub-Saharan Africa: a systematic review of 44 publications and 199 observations.
- **Crop scope:** Grain legumes (including soybean, groundnut and cowpea) followed by cereals (maize, sorghum, millet).
- **How it was checked:** Title, authors, journal, volume, pages and year confirmed against the Crossref record for the DOI. Abstract read from the Europe PMC record (PMC5946712, open access) on 14 Nov 2026. The full text was not read.
- **Limitations:**
  - Only the abstract was read. Methods, the individual studies and site-level results were not examined.
  - The abstract notes that agro-ecological zone and cereal type were confounded.
  - It reports that variability in the effect is large and not well explained.

### `rao-mathuva-2000`

**Legumes for improving maize yields and income in semi-arid Kenya**

- **Citation:** Rao, M. R., & Mathuva, M. N. (2000). Legumes for improving maize yields and income in semi-arid Kenya. Agriculture, Ecosystems & Environment, 78(2), 123-137. https://doi.org/10.1016/S0167-8809(99)00125-5
- **DOI:** 10.1016/S0167-8809(99)00125-5
- **Institution:** Published in Agriculture, Ecosystems & Environment (Elsevier); study at the ICRAF research station, Machakos
- **Accessed:** 14 November 2026
- **Read:** Abstract
- **Geographic scope:** One research station at Machakos, Kenya, November 1989 to February 1996.
- **Crop scope:** Maize, cowpea, pigeon pea, and the tree legume gliricidia.
- **How it was checked:** Title, authors, journal, volume, issue, pages and year confirmed against the Crossref record for the DOI. Abstract read from the Europe PMC record (AGRICOLA) on 14 Nov 2026. The full text was not read.
- **Limitations:**
  - Only the abstract was read. Soil type, rainfall in each season, varieties and management are unknown to this project.
  - One station and one seven-year period. The results are not a prediction for other farms or later years.
  - The trial ended in 1996; varieties and conditions have changed since.

## Sources looked for and not used

| Source | Why it was not used |
| --- | --- |
| FAO EcoCrop | The database redirected to a sign-in page on 14 November 2026, and the EcoCrop pages on the FAO GAEZ portal loaded empty. No value was taken from EcoCrop or from any copy of it. Several Feedipedia datasheets quote EcoCrop; those figures are held as secondary. |
| FAO Land and Water crop information pages | The English and French pages returned 'page not found'. |
| FAO Soils Bulletin 55 | Read in part; it holds no requirement table for these crops. |
| Climate Risk Profile for Machakos County (Kenya Ministry of Agriculture and CIAT, 2018) | Found, not read. It is the natural next source for which crops matter locally. |
| Full text of the two journal articles | Not accessed; only the abstracts were read. |
