# Phase A8 validation report

Independent validation of CropShift RESILIENCE before submission. Carried out
on 15 November 2026, 10:54 to 11:15 Singapore time, on commit `e1d021d` plus
the A8 fixes listed in section K. Every earlier phase report was treated as a
claim to be reproduced, not as a fact.

**What this validation is not.** It was done by the same AI-assisted
development process that built the tool, with the participant directing it. It
is not an independent agronomist review, and nothing here should be presented
as external scientific endorsement. Usability was reviewed internally only; no
farmer or outside user has tested the application.

## A. Executive summary

**Outcome: the application is fit to demonstrate, with its limitations
stated.** No crash, incorrect calculation, fabricated value or exposed secret
was found.

* Every number checked was recalculated by a separate, simple path from the raw
  NASA file and matched: season totals, temperatures, wet days, dry spells,
  annual totals, the dry/typical/wet classification, and the soil equations.
* All twelve demonstration steps were done by hand in a real browser.
* The review found **four places where the wording said more than the
  evidence**, **two display defects** and **one caching defect**. All are
  fixed and covered by new tests.
* Sensitivity check: the most visible result ("past rainfall was below maize's
  indicative water use in almost every season") **does not depend on the
  92-day window**. Stretched to 180 days from the window start, rainfall stays
  below 500 mm in 24 of 25 long-rains and 21 of 24 short-rains seasons.

**Still open (participant decisions and A9 work):**
* the pilot site is provisional;
* no licence has been chosen;
* the project is not yet public;
* the demo and the submission text do not exist yet.

## B. Baseline and regression

| Item | Found |
| --- | --- |
| Branch and state | `main` at `e1d021d`, clean working tree, no remote |
| Python | 3.12.13 in `.venv` (system default 3.15 not used) |
| Entry point | `app.py`, run as `.venv/bin/python -m streamlit run app.py` from the repository root; one application, one `src` package |
| Flags | OpenAI and Manus disabled; `openai_ready` false even with a key unless the switch is on (tested) |
| Secrets | None in the working tree or in any commit of the history; no `.env` file; `.env` ignored |
| Baseline tests | `.venv/bin/python -m pytest`: **866 passed, 1 skipped**, as A5 reported |

## C. Scientific evidence findings

Prioritised by the claims that drive what users see. "Re-read" means the source
passage was read again in A4 (15 Nov) or A8.

| # | Claim | Source | Verification method | Finding | Severity | Correction | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Maize needs 500-800 mm over the season | FAO TM3, Ch. 3, Table 14 | Re-read the table and the manual's definition | "Crop water need (ETcrop)" is evapotranspiration over the **total growing period**; the minimum applies to short growing periods. Interpretation in the engine is correct | — | None | Verified |
| 2 | Maize grows 125-180 days | FAO TM3, Table 6 | Re-read | Correct, and longer than the 92-day window. The rainfall headline did not say it counted only 92 days | P1 wording | Headline now ends "(rain within the 92-day window only; not a water balance)". Sensitivity check above shows the conclusion holds for 125 and 180 days | Fixed |
| 3 | Cowpea grows at 25-35 °C | Feedipedia cowpea (citing Madamba et al., 2006) | Re-read | Range verified; **which temperature statistic is NOT VERIFIED**: the source does not say. NASA's daily mean is never inside it (median 0 % of days), which is more likely a measure mismatch than evidence about cowpea | P1 wording | Every temperature headline now says the source does not say which temperature it means, "so this is not evidence of unsuitability". Excluding these comparisons altogether would change the agreed method: participant decision | Qualified |
| 4 | Pigeon pea grows better at 20-40 °C | Feedipedia pigeon pea | Re-read | A place preference, not a limit; statistic unstated. 96 % of days inside is expected for so wide a range and says little | P2 | Same headline caveat | Qualified |
| 5 | Maize optimal at 18-21 °C "average day-temperature" | Feedipedia maize | Re-read | Verified; "day-temperature" may be daytime, not the daily mean | P1 wording | Same headline caveat | Qualified |
| 6 | Common bean 15-23 °C; growth stops below 10 °C | Feedipedia bean | Re-read | Verified ("average temperatures"; period unstated) | P2 | Same caveat | Qualified |
| 7 | Sorghum 25-30 °C at seedling, 30 °C during growth | Feedipedia sorghum | Re-read | Stage-specific; stage dates unknown | — | Already excluded from calculation (A4 gate) | Verified exclusion |
| 8 | Maize after cowpea +17 %; maize after pigeon pea only marginally better (Machakos 1989-96) | Rao and Mathuva (2000), abstract | Abstract re-read (A4) | Verified in the abstract; one station, one period. The tradeoff text quoted only the positive review average | P1 balance | Tradeoff now gives both Machakos results and the weaker effect after cowpea, labelled "Past study results, not predictions" | Fixed |
| 9 | Cereals after grain legumes yield 41 % more on average (199 observations, sub-Saharan Africa) | Franke et al. (2018), abstract | Abstract re-read (A4) | Verified, with large variation. Two farmer explanations said a cereal without a legume "usually means lower" yields; that generalises an average | P1 wording | Rewritten: "on average … varies a lot … at Machakos maize after pigeon pea gained little". The temperature-rule explanation also now says sources often do not define their temperature | Fixed |
| 10 | Legume nitrogen | Feedipedia; Franke | Re-read | No nitrogen quantity is stated or implied; the indicator says "no quantity is estimated" and that 88 % of pigeon pea's fixed nitrogen leaves in the grain | — | None | Verified |
| 11 | Same family should not follow itself | none | A4 audit | Unsupported; never applied | — | None | Verified exclusion |
| 12 | TAW = 1000 (θFC − θWP) Zr; RAW = p TAW; Table 22 and Table 19 values | FAO-56 Ch. 7 and 8 | Re-read (A4); worked by hand (A8) | Verified | — | None | Verified |
| 13 | Rainy seasons March-May and October-December | FAO GIEWS Kenya brief | Live page re-read (A4, 15 Nov) | Verified; analysis windows only | — | None | Verified |
| 14 | Wet day ≥ 1 mm; frost day minimum < 0 °C | ETCCDI index definitions | Re-read (A4) | Verified; applied to a grid cell and a season (declared adaptation) | — | None | Verified |

### Answers to the brief's seven questions

1. **Maize water use:** read correctly as evapotranspiration over the whole
   growing period. It is compared with rain inside a 92-day window, which the
   headline now states.
2. **Maize growing period:** not compatible with a 92-day window. This is
   reported, and the sensitivity check shows the rainfall shortfall persists
   over 125 and 180 days.
3. **Cowpea temperature:** the statistic is not stated; NOT VERIFIED. The
   comparison stays conditional with an explicit "not evidence of
   unsuitability".
4. **Pigeon pea temperature:** justified only as a loose description; the range
   is a preference for places, and it is labelled so.
5. **Rotation relationships:** the Machakos findings are applied only as
   site-specific background for the same county, and the FAO guidance is
   labelled general.
6. **Legume benefits:** after the fixes, no text implies a nitrogen quantity or
   an expected yield gain. Study results are labelled as past results.
7. **Generalisation:** the 1989-96 ICRAF station results are applied to the
   Katumani grid cell only as background; that step is a declared assumption.

### Claims that remain NOT VERIFIED

| Item | Consequence |
| --- | --- |
| Which temperature each Feedipedia range refers to (all six crops) | Temperature results stay conditional and low-confidence, with the caveat in the headline |
| Whether TM3's global indicative growing periods and water needs fit local Katumani varieties | Stated as a limitation; local variety data would replace them |
| Content beyond the two abstracts (Franke full text open but unread; Rao full text inaccessible) | Both used as background only; never as calculation inputs |
| Agronomist review of the knowledge base | None has happened; must not be claimed |

## D. NASA data integrity

All checks in `tests/test_independent_verification.py` read the raw cached file
with the Python standard library only, with no data layer and no pandas.

| Check | Result |
| --- | --- |
| Endpoint and parameters | `https://power.larc.nasa.gov/api/temporal/daily/point`, community AG, `time-standard=UTC`, PRECTOTCORR, T2M, T2M_MAX, T2M_MIN, RH2M, ALLSKY_SFC_SW_DWN |
| Coordinates | Requested −1.58, 37.24; NASA echoes the same point (longitude first in GeoJSON), elevation 1,327.62 m |
| Dates | Every day 1 Jan 2001 to 31 Dec 2025: 9,131 = 25 × 365 + 6 leap days, all present, no fill values (−999) |
| Units | mm/day for rainfall, °C for temperature, as the app states |
| Fingerprint | SHA-256 of the canonical payload recomputed independently: `1c2ed230…0edaf`, matches the record and the app |
| Season totals | 10 sample seasons (both windows, dry and wet extremes, 2025) recalculated; all match to 0.01 mm |
| Temperature statistics | Mean of daily mean, lowest minimum, highest maximum and frost days for 4 seasons; all match |
| Wet days and longest dry spell | Long rains 2019 recalculated; match |
| Annual totals | All 25 years recalculated; match |
| Year-crossing window | November-February on the real record, including 29 Feb 2012; total matches; the 2025/26 season is correctly excluded as outside the record |
| Order independence | Shuffling the daily records changes no total and no class |
| Corrupted cache, in the browser | A copy with one value changed to 999 mm was refused ("failed verification"); the app fell back to the bundled response and said so |
| Live source | `pytest tests/test_live_power.py --run-live`: 1 passed (one ten-day request; NASA's current values equal the recorded ones) |
| Interpretation | The app says grid cells, not a farm; rainfall is never called irrigation demand; seasons are always "past", never forecast; "25 complete years" is verified, not assumed |

No numerical discrepancy was found.

## E. Agronomic and soil findings

* **Crops and families:** the six identifiers and two families match the
  sources' taxonomy lines (re-read in A4).
* **Growing periods, water needs and temperature ranges:** verified; see
  section C for the qualifications.
* **Soil equations, worked by hand:**

  | Crop | Available water (m³/m³) | Expected TAW (mm) | Expected RAW (mm) | Engine |
  | --- | --- | --- | --- | --- |
  | Maize (Zr 1.0-1.7 m, p 0.55) | 0.15 | 150-255 | 82.5-140.2 | Match |
  | Sorghum (1.0-2.0 m, 0.55) | 0.12 | 120-240 | 66.0-132.0 | Match |
  | Common bean (0.6-0.9 m, 0.45) | 0.10 | 60-90 | 27.0-40.5 | Match |
  | Cowpea (0.6-1.0 m, 0.45) | 0.20 | 120-200 | 54.0-90.0 | Match |

* **Soil boundaries:** zero available water gives zero; negative values and NaN
  are rejected; out-of-range values are rejected; implausible but possible
  values are kept with a warning.
* **Labels:** the illustrative soil is labelled hypothetical in the soil table,
  in every soil headline and in the comparison introduction (seen in the
  browser). No reference value is presented as a Katumani measurement.
* **Rotation strategies:**
  * *Studied:* the crops of each system, grown at Machakos 1989-96.
  * *Not documented:* the season of each crop and the cycle length. These are
    represented as unknown, and each crop is shown in both windows.
  * *Recommendations:* none. No strategy is presented as a verified local
    farming recommendation.

## F. Scenario and comparison validation

**Tercile classification.**

* *Reproduced:* the classification was rebuilt independently from the raw
  totals. Classes, boundaries (long rains: dry up to 197.9 mm, wet from
  284.4 mm) and representative seasons all match.
* *Ties:* ordered by year (A4 test).
* *Sample size:* 25 seasons per window, each with 100 % of days valid.
* *Why thirds:* equal-sized groups from a short record, using no outside
  threshold.
* *Limitations:*
  * the classes are relative to these 25 years only;
  * the boundaries would move if the record changed;
  * the method is the project's own choice, not a standard;
  * the classes describe rainfall totals only, not their timing.

**Indicators recalculated independently:**

* the positions for all 25 short-rains seasons for maize;
* the share of days inside 18-21 °C for long rains 2018;
* the soil equations (section E);
* plant families and repetition (A4 tests).

**Properties tested:**

| Property | Test |
| --- | --- |
| Reordering records does not change totals | `test_classification_does_not_depend_on_record_order` |
| Priority order does not change results | `test_priorities_change_presentation_not_results`, `test_priorities_do_not_change_the_results` |
| Removing soil makes soil results unavailable | `test_soil_indicators_are_unavailable_without_soil_and_say_how_to_get_it` |
| Unsupported evidence cannot create a result | `test_injected_unverified_value_cannot_reach_a_result` and the gate tests |
| Same inputs give the same output | `test_comparison_is_deterministic`, `test_pilot_classification_is_reproducible` |
| Missing water evidence gives no water estimate | `test_pigeon_pea_water_indicators_remain_unavailable`, `test_cowpea_water_use_is_not_borrowed_from_another_crop` |
| Past years stay traceable | `test_rainfall_indicator_uses_the_nasa_season_totals` |
| No overall score appears | `test_no_overall_score_or_ranking`, `test_no_overclaiming_phrase_appears` |
| A reloaded module's enums still match cached objects | `test_cached_knowledge_base_answers_for_a_reloaded_priority_enum`, `test_cached_scenarios_filter_by_a_reloaded_category_enum` |

**Communication audit.** Every headline template, farmer explanation and
tradeoff note was read. The fixes are:

* the rainfall headline;
* the temperature headlines;
* the legume tradeoff;
* two farmer explanations;
* source names in explanations: they had been cut at an author's initial, for
  example "Heuzé V";
* season medians shown to two decimals ("173.18 mm"), now rounded.

## G. Browser walkthrough

The app was started with `.venv/bin/python -m streamlit run app.py` and used
at 1440 × 900 with real clicks and typing.

| # | Step | Method | Outcome |
| --- | --- | --- | --- |
| 1 | Open CropShift RESILIENCE | Manual | Passed: title, subtitle, banner |
| 2 | View the Katumani pilot | Manual | Passed: site, coordinates, provisional status, source, period |
| 3 | Inspect NASA rainfall | Manual (clicked tab) | Passed: 25 seasons, 198 / 284 mm boundaries, chart |
| 4 | Select a dry scenario | Manual (sidebar click) | Passed: 8 dry seasons listed; day-by-day view on 2009, the representative season |
| 5 | Compare the three rotations | Manual (clicked tab) | Passed: three cards; "In the 8 dry long rains seasons: rainfall below the range in 8"; pigeon pea water unavailable |
| 6 | Review tradeoffs | Manual | Passed: balanced legume note visible |
| 7 | Enter valid soil | Manual (typed pH 6.2, picked loam from the list, submitted) | Passed: "applied … not verified"; table shows user reported / not verified |
| 8 | Soil results update | Manual | Passed: maize pH inside 4.3-8.7; root zone 130-306 mm; pigeon pea readily available water unavailable |
| 9 | Select a priority | Manual (keyboard only: typed "Water", Enter) | Passed: "1. Water conservation", ★ marks, "no weights" |
| 10 | Open an explanation | Manual (clicked) | Passed: numbered parts shown. Found the truncated-citation defect here; fixed |
| 11 | NASA citations and limitations | Manual (clicked tab) | Passed: all five key limitations, NASA citation and version, SHA-256, MERRA-2 reference |
| 12 | Return to the overview | Manual (clicked tab) | Passed |

**Additional interactions:**

| Interaction | Method | Outcome |
| --- | --- | --- |
| Missing soil (default) | Manual | Passed: soil results unavailable with how to obtain them |
| Illustrative soil | Manual | Passed: "not measured at Katumani" and "hypothetical demonstration soil" everywhere |
| Invalid soil | Manual in A5 (field capacity below wilting point refused); automatic in A8 | Passed. Not repeated by hand in A8; that code did not change |
| Scenario change (short rains) | Manual | Passed |
| Navigation between all six tabs | Manual | Passed |
| Page reload | Manual | Passed: session returns to defaults, no error |
| Application restart | Manual | Passed |
| Offline mode with a tampered cache | Manual (second server, `OFFLINE_DEMO_MODE=true`) | Passed: tampered data refused, bundled data used, warning shown |
| Missing bundled data | Automatic (`test_app_fails_clearly_when_offline_data_is_missing`) | Passed |
| Hot reload after a code change | Manual | Passed for the A5 regression: no crash, sidebar and tabs work. **New finding:** with Streamlit's polling file watcher, the edited engine module was not re-imported, so the running server kept the old wording until restarted. The cached results are now also keyed on a fingerprint of all source and knowledge files, so wherever modules are reloaded, stale results cannot be served |

## H. Security and reliability

| Area | Finding | Severity | Status |
| --- | --- | --- | --- |
| Secrets in Git | None in tree or history | — | Pass |
| `.env` | Not present; ignored by Git | — | Pass |
| Paid integrations | Off by default; need switch and key | — | Pass |
| Secrets in exports and logs | A test key did not appear in any download or in the settings text | — | Pass |
| Credentials in URLs | NASA POWER needs none; none used | — | Pass |
| Dependencies | 46 installed packages checked against the OSV database on 15 Nov 2026: no known advisories. A point-in-time result, not a guarantee | — | Pass |
| Reproducible install | `requirements.txt` gave version ranges only | Low | Fixed: `requirements-lock.txt` records the exact tested versions (without hashes) |
| Input validation | Bounds, NaN, future dates, unknown categories and contradictory soil values rejected; user text shown only inside tables, never as HTML | — | Pass |
| Error details | Browser shows generic messages only; tabs and sidebar guarded | — | Pass |
| Stale cached results after code or knowledge changes | Possible with module reloads | Medium | Fixed: source fingerprint in every cache key |
| Network exposure of the local server | Streamlit listens on all network interfaces by default and prints a network URL | Low | Open: for a local demo on shared Wi-Fi, add `--server.address localhost` |
| Corrupt or missing data | Refused and reported; fallback to bundled data | — | Pass |

**Privacy, from the code:**

* **Location:** none collected; the site is fixed.
* **Soil entries:** held only in the browser session's server memory, gone on
  reload, and never written to disk.
* **Files written:** the only one is the NASA response cache.
* **Logs:** go to the server console only; no log file.
* **Telemetry:** Streamlit usage statistics are off.
* **Downloads:** contain the user's own soil entries, by their action.

## I. Accessibility and usability

Reviewed internally only. No farmer or external user has tested the app.

**Strengths (checked):**

* **First screen:** the purpose is on it ("Explore historical climate
  conditions and compare evidence-backed crop rotations").
* **Contrast:** status words are written, not colour-coded alone, and pass
  WCAG AA (measured 7.4, 6.4 and 6.1 to 1; captions 13.7 to 1).
* **Screen readers:** radio buttons are announced by their visible labels.
* **Keyboard:** the priority picker and the soil form work from the keyboard.
* **Charts:** every chart names its units and its caveat.
* **Kinds of information:** measured, modelled, literature and hypothetical
  are labelled separately.

**Fixed:** the orange "dry" bars were only about 2.3 to 1 against white; all
bars now have a dark outline.

**Weaknesses (open):**

* **Length and repetition:** the comparison page is long (about 50 result
  cards), and maize appears in all three columns.
* **Jargon:** "evapotranspiration", "depletion fraction" and "reanalysis"
  remain, although each is explained in the result's explanation.
* **Charts and screen readers:** charts have no text alternative beyond their
  titles; the scenario table is the accessible equivalent for season rainfall.
* **Language:** English only.
* **Mobile:** columns stack on a phone, making the page longer still.

**Can a user answer the brief's six questions?**

| Question | Where |
| --- | --- |
| What conditions have occurred here? | Climate Explorer |
| How do the strategies differ? | "What changes between these strategies?" |
| Which indicators are supported? | Status on every result card; confidence counts |
| What is missing? | Unavailable cards with reasons; "Still missing" on the soil tab |
| What can this tool help me explore? | Overview, "How to use CropShift" |
| What should I not decide from this alone? | "What CropShift does not estimate"; the disclaimer |

## J. Submission readiness

Re-verified on the live official Project Submission Guide on 15 Nov 2026:

* **Deadline:** Sunday 15 November, 11:59 p.m. in the Local Event's time zone.
* **Demo:** 7 slides including title and introduction, or a video of at most
  30 seconds.
* **Links:** publicly accessible with no login, permission or registration.
* **AI disclosure:** a "Use of Super Intelligence (SI)" field, with SI
  acknowledged in code text and metadata.
* **NASA data:** at least one NASA data source or resource.
* **New since A1:** an optional site-classification request for hosted links,
  to avoid access problems during judging.

| Item | State | Class |
| --- | --- | --- |
| Public project link (repository and/or hosted app) | Not public; no remote | **Blocker**: needs the participant's decision and approval |
| Demo (7 slides or 30-second video) | Not made | **Blocker** (A9) |
| Submission form text (summary, description, SI use, NASA data, references) | Material exists in the docs; text not written | **Blocker** (A9) |
| Licence | None chosen; the terms say NASA would distribute under Apache 2.0 without one | Warning: participant decision |
| Pilot site approval | Provisional | Warning: may be presented as provisional, never as final |
| NASA data citations | In the app, README and `provenance.md` | Ready |
| Scientific references | 13 sources plus ETCCDI, with full citations | Ready |
| AI disclosure | README, `provenance.md`, module docstrings, app | Ready; the participant writes the SI field |
| README, methodology, limitations | Present | Ready; final pass in A9 |
| Architecture diagram | Mermaid diagram in `architecture.md` | Ready |
| Screenshots | None saved | A9 |
| Team information | Solo participant | Participant |
| NASA POWER notification | Not sent | After publishing |

## K. Files changed in A8

| File | Change | Why |
| --- | --- | --- |
| `src/comparison_engine.py` | Rainfall and temperature headlines carry their key caveat; balanced legume tradeoff; sources named by title and year | Wording said more than the evidence; citations displayed as "Heuzé V" |
| `data/knowledge/rotation_relationships.json` | Two farmer explanations reworded | "Usually means lower yields" generalised an average |
| `docs/agronomic_knowledge.md` | Same two explanations | Kept in step with the data |
| `app.py` | Source fingerprint in every cache key; season medians rounded | Stale results after code or knowledge changes; "173.18 mm" |
| `src/visualizations.py` | Dark outline on every bar | Orange bars below 3:1 contrast |
| `requirements-lock.txt` | New: exact versions of the 46 tested packages | Reproducible installation |
| `tests/test_independent_verification.py` | New, 31 tests | Independent recalculation from the raw NASA file and by hand |
| `tests/test_scientific_communication.py` | New, 8 tests | Pin the wording fixes; reproduce the hot-reload defect |
| `docs/rotation_comparison_methodology.md` | Regenerated | Sample results now show the corrected wording |
| `docs/a8_validation_report.md` | New | This report |
| `README.md`, `docs/provenance.md`, `docs/implementation_plan.md` | Updated | Lock file, work log, status |

No existing test was changed or weakened in A8. The A4 evidence-audit and
scenario documents were regenerated and came out identical.

## L. Test report

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` (baseline) | 866 passed, 1 skipped |
| `.venv/bin/python -m pytest` (after A8) | **905 passed, 1 skipped**, 0 failed |
| `.venv/bin/python -m pytest tests/test_live_power.py --run-live` | 1 passed |
| OSV query for all 46 installed packages | 0 known advisories |

## M. A8 acceptance checklist

| Item | Result |
| --- | --- |
| A1-A5 baseline reproduced | Passed |
| Repository integrity verified | Passed |
| Scientific references reviewed | Passed |
| Critical numeric claims verified | Passed (temperature statistics NOT VERIFIED and qualified) |
| Abstract-only limitations preserved | Passed |
| NASA observations independently checked | Passed |
| Seasonal aggregations independently checked | Passed |
| Dataset provenance verified | Passed |
| Crop requirements audited | Passed |
| Soil equations independently checked | Passed |
| Rotation assumptions verified | Passed |
| Scenario classification reproduced | Passed |
| Comparison indicators independently checked | Passed |
| Missing evidence handled correctly | Passed |
| No unsupported recommendations | Passed (after the wording fixes) |
| Streamlit launches | Passed |
| All twelve browser steps manually verified | Passed |
| Hot-reload regression checked | Passed (no crash); new staleness finding fixed |
| Offline operation verified | Passed (browser, tampered cache) |
| Secrets and privacy reviewed | Passed |
| Dependency security reviewed | Passed (point-in-time OSV check) |
| Accessibility reviewed | Passed (internal review; open weaknesses listed) |
| Farmer usability assessed without inventing external testing | Passed |
| Official challenge requirements reviewed where accessible | Passed |
| Submission assets inventoried | Passed |
| A6/A7 reassessment completed | Passed |
| New tests pass | Passed |
| Existing regression tests pass | Passed |
| No paid services activated | Passed |
| No A9 implementation started | Passed |

## N. A6 and A7 reassessment

**A6, OpenAI explanations: defer until after submission.**

* **Explanations already exist.** Every result has a six-part explanation, and
  the browser walkthrough found them readable. No usability problem was
  demonstrated that a conversational layer would solve.
* **It would be safe only if heavily restricted.** It could be limited to
  restating `summary_markdown(report)`. Even then, the A8 review found four
  places where carefully written deterministic text overstated the evidence;
  generated text would raise that risk, and every output would need checking.
* **It costs money and needs a network.** It needs a paid key, and it would
  break the fully offline demonstration unless kept optional.
* **It takes time.** A client, a new dependency, failure handling, labelling
  and tests: several hours of the roughly 10 left at the end of A8, for no measured benefit.

**A7, Manus research reports: do not implement for this submission.**

* No need for long-form external research was found: the evidence base is
  curated and audited.
* Any citation it produced would need the same manual verification as A3/A4.
* Asynchronous jobs add complexity.
* It costs money and depends on an external service.
* The China-affiliation question (compliance item C4) is unresolved.

## O. A9 readiness

**Blockers:**

1. Decide how to make the project public (a public repository, and optionally
   a hosted app), and approve publishing.
2. Make the demo: 7 slides or a 30-second video.
3. Write the submission form text.

**Decisions:**

* a licence;
* whether to present Katumani as a provisional pilot (recommended) or approve it;
* whether to keep the temperature comparisons, which are qualified, or hide them.

**Assets to prepare:**

* screenshots of the Overview, the Climate Explorer with dry seasons, the
  comparison, and the evidence tab;
* the reference list from `provenance.md`;
* the SI disclosure text;
* the NASA data paragraph.

**Demonstration sequence:** as in `a5_application_guide.md`:

1. Overview.
2. Dry seasons in the Climate Explorer.
3. Rainfall cards and pigeon pea's unavailable water result in the comparison.
4. Illustrative soil.
5. Water-conservation priority.
6. Limitations and "What CropShift does not estimate".

**Claims that are safe to present:**

* It uses 25 years of real NASA POWER daily data for one area, verified and
  traceable to its source.
* It compares three rotations grown in a Machakos study across 50 real past
  rainy seasons, side by side.
* Every value cites its source, location and audit status. Unsupported values
  are excluded and missing evidence is shown, not filled.
* In this record, rainfall in both rainy seasons almost always fell short of
  maize's indicative seasonal water use, even counted over its full growing
  period. Say: rain alone, not a water balance.
* It works offline and makes no AI call.

**Claims to qualify or avoid:**

| Avoid | Say instead |
| --- | --- |
| Any yield, profit or nitrogen benefit as a prediction | Quote study results only as past results, with their place and years |
| "Validated", "agronomist-reviewed" or "farmer-tested" | Internally validated; not externally reviewed |
| Calling a rotation best, safest or more resilient | Show the tradeoffs side by side |
| Treating cowpea or pigeon pea temperature results as suitability | Explain that the source temperature measure is unknown |
| Calling Katumani the project's site | Say it is a provisional pilot site |
| Calling dry, typical and wet a forecast or climate projection | Say they are thirds of the past 25 seasons |
