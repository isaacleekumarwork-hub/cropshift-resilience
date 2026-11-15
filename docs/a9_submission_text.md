# Submission text for the Space Apps project page

Prepared on 15 November 2026 in phase A9, ready to copy into the team's
Project page. Every sentence was checked against
[`a9_claims_register.md`](a9_claims_register.md).

**Form fields.** The official Project Submission Guide (re-read on
15 November 2026) lists these fields: Project Name, High-Level Project
Summary, Link to Project Demo, Link to Final Project, Detailed Project
Description, Use of Super Intelligence (SI), NASA Data, and Space Agency
Partner Data and Other References. The guide states **no character limits**.
The form itself is behind the participant's login and was not opened, so if a
field shows a limit when you paste, shorten the text there. The answers below
are written to be cut from the end.

**Ready to paste.** Project: CropShift RESILIENCE. Team: WindShift.
Participant: Isaac Lee Kumar. Both links are filled in and were checked
without a login. One bracketed note remains in the SI section for you to
complete or delete.

---

## Project Name

CropShift RESILIENCE

## Tagline (one sentence, for the summary's first line or the demo)

Compare crop rotations against 25 years of NASA climate history, with the
evidence, the gaps and the uncertainty in plain view.

## High-Level Project Summary

CropShift RESILIENCE is a web app that helps farmers, and the extension
officers who advise them, compare crop-rotation options against the real
climate record. For a provisional pilot area in Machakos County, Kenya, it uses
25 years of NASA POWER daily data to show how rainfall and temperature varied
across 50 past rainy seasons, grouped into dry, typical and wet thirds. It sets
three rotations documented in published research side by side: continuous
maize, maize with cowpea, and maize with pigeon pea. Farmers can add their own
soil information and priorities. Every result explains the data it used, its
assumptions, what it means and what it does not establish, and missing
evidence is shown as missing instead of being estimated. It does not predict
yields, forecast weather or name a best rotation. It addresses the Field Shift
challenge by turning NASA's open Earth observations into a transparent
starting point for adapting farm decisions to variable rainfall.

## Link to Project Demo

https://github.com/isaacleekumarwork-hub/cropshift-resilience/blob/main/docs/presentation/CropShift_RESILIENCE_demo.pdf

A seven-slide deck (title and introduction included), as a PDF in the public
repository. Test the link in a private browser window before submitting.

## Link to Final Project

https://github.com/isaacleekumarwork-hub/cropshift-resilience

The public GitHub repository (Apache-2.0). Do not give a localhost address:
judges cannot open it.

## Detailed Project Description

**What it does**

CropShift RESILIENCE lets a user explore what the weather actually did at one
area, season by season, and see how three crop rotations line up against that
history and against the published evidence about each crop.

* **Climate Explorer.** Every long-rains (March to May) and short-rains
  (October to December) season from 2001 to 2025, with rainfall totals, wet
  days, the longest dry spell, the wettest day and temperatures. Seasons are
  grouped into dry, typical and wet thirds of the record, and any season can be
  viewed day by day.
* **Rotation Comparison.** Continuous maize, maize rotated with cowpea and
  maize rotated with pigeon pea, all grown in a 1989 to 1996 cropping-systems
  experiment at Machakos (Rao and Mathuva, 2000), shown side by side. For each
  crop the app compares past season rainfall with the crop's indicative water
  use, temperatures with documented ranges, frost, the growing period against
  the rainy season, annual rainfall, soil pH and root-zone water, and the
  plant-family diversity of the sequence: 11 indicators and 14 constraints in
  all. Each result is marked supported, conditional or unavailable, with a
  confidence level and a six-part explanation.
* **Soil & Farm Inputs.** Optional soil pH, texture, field capacity, wilting
  point or available water capacity, each recorded with where it came from
  (own knowledge, laboratory, public dataset). Empty fields stay empty; nothing
  is filled in.
* **Farmer priorities.** Water conservation, crop diversity and eight others.
  They change the order in which results are shown, never the results.
* **Scientific Evidence.** Where every number came from, the audit status of
  every source, the important limitations, and a list of what CropShift does
  not estimate.
* **Downloads.** The comparison as a Markdown summary and as JSON.

An example of what it shows: at the pilot area, rain that fell inside the
92-day window was below maize's indicative seasonal water use (500 to 800 mm,
an FAO figure) in 24 of 25 long-rains seasons and in all 25 short-rains
seasons. This is a first indication, not a water balance. No verified water-use
figure exists in the sources for cowpea or pigeon pea, so those results say
"not available" and explain why.

**How it works**

1. A NASA data layer requests daily data from the NASA POWER API with
   timeouts and bounded retries, validates it at three levels, records its
   provenance, and stores NASA's response unmodified with a SHA-256
   fingerprint. A copy is bundled, so the app works offline.
2. A knowledge base holds six crops, thirteen sources and 205 cited claims,
   each with its source and location in the source. Gaps are recorded as "not
   established", never filled.
3. An evidence audit re-checked every source. An evidence gate lets a value
   into a calculation only if the audit supports it, and conditional values
   carry their conditions.
4. A deterministic engine builds the season scenarios and compares the
   rotations. It has no overall score by design.
5. A Streamlit interface presents the results with colour-blind-safe Plotly
   charts and plain-language explanations.

**The problem it addresses**

Rainfall at the pilot area varies widely: long-rains rainfall ranged from
102 mm to 556 mm between 2001 and 2025, a 39 % coefficient of variation.
Farmers choosing a rotation have to weigh rainfall they cannot predict.
Published research documents legume rotations at Machakos, but the results
vary, and the crop evidence is scattered across manuals, datasheets and
papers, often with conditions attached.

**What makes it different**

It is not a crop-recommendation chatbot. It combines real NASA environmental
observations, historical season comparisons, published rotation evidence,
optional soil inputs and farmer priorities, and it keeps the provenance of
every value. It treats missing evidence and uncertainty as results to show,
not gaps to paper over, and its deterministic core runs offline.

**Potential benefits**

These are potential, not demonstrated: no farmer has used the tool yet. Farmers
and extension officers could look at past rainy seasons and documented
rotations together, see what the evidence does and does not support, and bring
their own soil information and priorities. Because the core runs offline, it
could suit places with poor connectivity. The same approach could extend to
other sites and crops.

**Tools and languages**

Python 3.12, Streamlit, pandas, NumPy, Plotly, Pydantic, pydantic-settings,
HTTPX, pytest and uv. 905 automated tests run without network access,
including 31 that recalculate the key numbers from the raw NASA file without
the project's own code. One further test checks the live NASA service.

**Limitations**

* The Katumani pilot area is provisional, not a final site.
* Rainfall inside a fixed window is not a complete water balance.
* Global crop water figures may not match local varieties.
* The crop-specific planting calendar is unknown; the windows are analysis
  periods, not sowing dates.
* The sources do not say which temperature statistic their ranges refer to,
  so temperature results are not evidence of suitability.
* NASA values are area averages from a reanalysis, not farm measurements, and
  have not been compared with a local station.
* Dry, typical and wet are historical thirds, not forecasts.
* There are no yield, profit, nitrogen or soil-carbon estimates.
* The project has not been reviewed by an agronomist or tested with farmers.
  Its validation was internal.
* English only.

**Next steps**

Review with Kenyan agronomists and test with farmers; compare the NASA data
with local weather stations; add a daily soil water balance (FAO-56 reference
evapotranspiration); gather local variety and planting-calendar data; add more
sites, Kiswahili, and grounded plain-language explanations once user testing
shows they are needed.

**Team**

Team WindShift: Isaac Lee Kumar, solo participant, Singapore Local Event.
The participant chose the challenge and defined the product concept,
architecture, scope and acceptance criteria for each development phase, and
reviewed and approved each phase. Implementation was AI-assisted, as described
under Use of Super Intelligence.

## Use of Super Intelligence (SI)

Yes. An AI coding assistant, Claude Code (Anthropic), was used throughout
development under my direction. I chose the challenge and defined the product
concept, architecture, scope and acceptance criteria in a written brief for
each phase, and reviewed and approved each phase before the next began. The
assistant wrote the code, automated tests and documentation; read the official
challenge pages, NASA documentation and the scientific sources; ran the NASA
POWER requests; checked the app in a browser; captured the screenshots; laid
out the demo slides; and drafted this text.

What the SI did not do: it generated no environmental data (every value was
returned by NASA's service and is stored unmodified), no agronomic values
(every one was read from the published source it cites), and no video or
audio. The one AI-generated image is the app's decorative painted background
in the "Starry Night" theme (original SVG artwork inspired by Van Gogh's
public-domain painting, showing an imaginary landscape); it carries a visible
"AI-generated (SI)" watermark and a credit on every page. Screenshots are
captures of the running app. The running app
uses no AI: its scientific engine is deterministic, and its optional OpenAI and
Manus integrations are switched off and not built.

SI use is marked in the code and documentation: every Python module's opening
docstring, the README, `docs/provenance.md` and the app's footer.

[Add any other SI tools you used outside this repository, for example to draft
the phase briefs.]

## NASA Data

**NASA POWER (Prediction Of Worldwide Energy Resources), Daily API v2.10.3**,
NASA Langley Research Center, https://power.larc.nasa.gov/

* Point request for latitude -1.58, longitude 37.24 (the Katumani area of
  Machakos County, Kenya), community AG, 1 January 2001 to 31 December 2025:
  9,131 days, 100 % complete. Retrieved on 14 November 2026 and bundled with
  the project.
* Parameters: `PRECTOTCORR` (bias-corrected precipitation), `T2M`, `T2M_MAX`
  and `T2M_MIN` (temperature at 2 m), `RH2M` (relative humidity at 2 m) and
  `ALLSKY_SFC_SW_DWN` (all-sky surface shortwave irradiance).
* Underlying NASA products, as distributed by POWER: the **MERRA-2**
  reanalysis from NASA's Global Modeling and Assimilation Office for the
  meteorological values, and **CERES SYN1deg** (NASA Langley) for the solar
  values.
* How it is used: season rainfall totals, wet days, dry spells, wettest days,
  frost days and temperature statistics for 50 rainy seasons; dry, typical and
  wet thirds of the record; and comparisons with documented crop ranges.

Attribution: "The data was obtained from National Aeronautics and Space
Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy
Resources (POWER) project funded through the NASA Earth Science Division. The
data was obtained from the POWER Project's Daily v2.10.3 version on
2026/11/14."

This is an independent project and is not endorsed by NASA.

## Space Agency Partner Data and Other References

**Space Agency Partner data:** none used.

**Data and methods**

* NASA POWER Daily API v2.10.3 (above).
* Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research
  and Applications, Version 2 (MERRA-2). *Journal of Climate*, 30(14),
  5419–5454. https://doi.org/10.1175/JCLI-D-16-0758.1
* CERES SYN1deg, NASA Langley Research Center. https://ceres.larc.nasa.gov/
* Expert Team on Climate Change Detection and Indices (ETCCDI). Climate Change
  Indices: Definitions of the 27 core indices.
  https://etccdi.pacificclimate.org/list_27_indices.shtml (accessed
  15 November 2026).
* OpenStreetMap Nominatim, one reverse-geocoding request on 15 November 2026
  to confirm the pilot coordinates lie in Machakos County. Data ©
  OpenStreetMap contributors, Open Database Licence.

**Agronomic sources**

* Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). Crop
  evapotranspiration: Guidelines for computing crop water requirements. FAO
  Irrigation and Drainage Paper 56. Rome: FAO.
  https://www.fao.org/4/x0490e/x0490e00.htm
* Brouwer, C., & Heibloem, M. (1986). Irrigation Water Management: Irrigation
  Water Needs. Training manual no. 3. Rome: FAO.
  https://www.fao.org/4/s2022e/s2022e00.htm
* Heuzé V., Tran G., Nozière P., Lebas F., 2015. Common bean (Phaseolus
  vulgaris). Feedipedia, a programme by INRAE, CIRAD, AFZ and FAO.
  https://www.feedipedia.org/node/266
* Heuzé V., Tran G., Nozière P., Bastianelli D., Lebas F., 2015. Cowpea (Vigna
  unguiculata) forage. Feedipedia. https://www.feedipedia.org/node/233
* Heuzé V., Tran G., Edouard N., Lebas F., 2017. Maize green forage.
  Feedipedia. https://www.feedipedia.org/node/358
* Heuzé V., Tran G., Bastianelli D., Lebas F., 2015. Mung bean (Vigna
  radiata). Feedipedia. https://www.feedipedia.org/node/235
* Heuzé V., Thiollet H., Tran G., Delagarde R., Bastianelli D., Lebas F.,
  2017. Pigeon pea (Cajanus cajan) forage. Feedipedia.
  https://www.feedipedia.org/node/22444
* Heuzé V., Tran G., Giger-Reverdin S., Lebas F., 2015. Sorghum forage.
  Feedipedia. https://www.feedipedia.org/node/379
* Rao, M. R., & Mathuva, M. N. (2000). Legumes for improving maize yields and
  income in semi-arid Kenya. *Agriculture, Ecosystems & Environment*, 78(2),
  123–137. https://doi.org/10.1016/S0167-8809(99)00125-5
* Franke, A. C., van den Brand, G. J., Vanlauwe, B., & Giller, K. E. (2018).
  Sustainable intensification through rotations with grain legumes in
  Sub-Saharan Africa: A review. *Agriculture, Ecosystems & Environment*, 261,
  172–185. https://doi.org/10.1016/j.agee.2017.09.029
* FAO. Conservation Agriculture in practice: Species diversification.
  https://www.fao.org/conservation-agriculture/in-practice/species-diversification/en/
* FAO. Conservation Agriculture in practice: Soil organic cover.
  https://www.fao.org/conservation-agriculture/in-practice/soil-organic-cover/en/
* FAO GIEWS. Country Brief: Kenya (reference date 4 May 2026).
  https://www.fao.org/giews/countrybrief/country.jsp?code=KEN
* Europe PMC (https://europepmc.org/) and Crossref
  (https://www.crossref.org/) were used to re-check the two journal articles.

**Software (all open source)**

Python 3.12 (PSF licence); Streamlit (Apache-2.0); pandas, NumPy and HTTPX
(BSD-3-Clause); Plotly, Pydantic, pydantic-settings and pytest (MIT); uv
(Apache-2.0 or MIT). Full list of the 46 installed packages and their licences:
`docs/compliance.md` in the repository. CropShift's own code and
documentation are released under the Apache License 2.0.

**Demo deck**

Typefaces Space Grotesk and Inter from Google Fonts (SIL Open Font Licence).
All images are screenshots of the app; no stock images. If the "Starry Night"
theme is shown, its painted background is the app's own watermarked
AI-generated artwork.

**Tools**

Claude Code (Anthropic), an AI coding assistant, used for development as
described under Use of Super Intelligence.

**Code, text and images from other projects:** none.
