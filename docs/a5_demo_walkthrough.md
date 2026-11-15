# Demonstration walkthrough (phase A5.9)

The twelve-step journey from the A5 brief, run twice on 15 November 2026:

* **Automated:** `tests/test_app.py::test_demonstration_walkthrough` drives the
  real `app.py` offline with Streamlit's test runner and asserts each step.
* **In a browser:** the app was started with
  `.venv/bin/python -m streamlit run app.py` and checked at 1440 × 900. Steps
  1, 3, 4, 5, 7 and 8 were done by hand in the browser (pH 5.4 with 140 mm/m;
  then field capacity 0.10 with wilting point 0.05), and steps 2 and 6 were
  seen on screen. Steps 9 to 12 were verified by the automated test only.

| # | Step | What happened | Result |
| --- | --- | --- | --- |
| 1 | Open CropShift RESILIENCE | Title, subtitle and the banner: provisional site, past seasons not forecasts, no rotation scored, ranked or recommended | Passed |
| 2 | View the Katumani pilot | Overview: Katumani area, Machakos County, Kenya; latitude −1.58, longitude 37.24; NASA POWER Daily API v2.10.3; 1 Jan 2001 to 31 Dec 2025, 9,131 days, 54,786 daily values; site status provisional | Passed |
| 3 | Inspect historical NASA rainfall | Monthly rainfall with both windows shaded; Climate Explorer: 25 long-rains seasons, 102 to 556 mm, dry up to 198 mm, wet from 284 mm, variability 39 % | Passed; chart values equal the engine's season totals (tested) |
| 4 | Select a dry historical scenario | Sidebar: *Dry seasons*. Table shows the 8 dry long-rains seasons (2019, 2022, 2011, 2009, 2016, 2014, 2004, 2015); the day-by-day chart opens on the representative dry season, 2009 | Passed |
| 5 | Compare the three rotations | Three cards side by side; maize rainfall card: "In the 8 dry long rains seasons: rainfall below the range in 8, within it in 0, above it in 0"; cowpea and pigeon pea water cards *Unavailable* with reasons | Passed |
| 6 | Review supported tradeoffs | *What changes between these strategies?*: plant-family diversity, water-use evidence ("incomplete, not favourable"), legumes and pest management, what is the same | Passed |
| 7 | Enter valid soil information | Soil & Farm Inputs, *Enter my soil information*: pH 6.0 (test) or 5.4 (browser), available water capacity 150 (test) or 140 mm/m (browser); submitted | Passed; "applied … CropShift has not verified it" |
| 8 | Observe soil-related changes | Soil cards now have values, e.g. "Pigeon pea: the root zone (2 m) could hold about 300 mm of plant-available water"; pigeon pea readily available water stays unavailable; weather results unchanged | Passed |
| 9 | Select a farmer priority | Sidebar: *Water conservation*. "Your priorities: 1. Water conservation"; related results starred and moved first; no weights | Passed |
| 10 | Review scientific explanations | *How to read this result*: the six parts, conditions, evidence with citations and audit status, confidence reason | Passed |
| 11 | Inspect NASA citations and limitations | Scientific Evidence: NASA POWER citation and version line, request URL, SHA-256, the five key limitations, what CropShift does not estimate, 13 sources with links | Passed |
| 12 | Return to the overview | Overview tab intact; no error anywhere | Passed |

Also checked in the browser: an invalid entry (field capacity 0.10 below
wilting point 0.20) is refused with "Not applied: field capacity must be greater
than the wilting point", the soil stays unapplied, and the page shows no stack
trace. Correcting the wilting point to 0.05 applied the soil (plant-available
water 0.05 m³/m³, "derived from inputs") and left the weather results unchanged.

### A defect found during the walkthrough, and fixed

After code was edited while the server was running, Streamlit's hot reload
created fresh copies of the modules while the cached knowledge base still held
enum values from the old copies. `KnowledgeBase.priority` compared enums by
identity, so the sidebar failed and, because the sidebar was not guarded, the
whole page showed Streamlit's generic error. Fixes: priorities and season
classes are now compared by value; the sidebar is rendered through the same
guard as the tabs. A fresh server start did not have the problem, and the
browser checks above were repeated on a fresh server after the fix.
