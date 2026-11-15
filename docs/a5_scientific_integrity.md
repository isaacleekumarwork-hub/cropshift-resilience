# Scientific integrity of the interface (phase A5)

The interface adds no science. Every number is a value from the NASA dataset
(A2), the knowledge base (A3) or the comparison report (A4), and every
explanation is the engine's own six-part explanation. This document records the
overclaiming review and the tests that enforce it.

## Rules and where they are enforced

| Rule | How the interface keeps it | Test |
| --- | --- | --- |
| No overall score | No score is computed or displayed; the banner and comparison intro say so; evidence counts are captioned "not a score" | `test_no_overclaiming_phrase_appears` |
| No best rotation | No winner, safest, most resilient, most profitable or highest-yield wording anywhere; tradeoffs come verbatim from the engine | the same, 16 phrases, with and without soil and priorities |
| Historical, not forecast | Banner; chart titles say "past seasons"; subtitles say "not a forecast"; scenario limits shown | `test_app_states_its_stage_and_its_limits_honestly`, chart tests |
| Planting calendar not verified | Windows described as FAO GIEWS analysis windows, "not sowing dates"; strategy cards say the season of each crop was not reported | `test_pilot_windows_are_the_cited_giews_windows` (A4), card text |
| Rainfall alone does not decide suitability | Rainfall cards show the engine's condition ("not directly comparable without a water balance"); the section caption says "a first indication, not a water balance"; the water-use chart subtitle says "Not a water balance" | `test_conditional_results_show_their_conditions`, `test_water_use_chart_states_it_is_not_a_water_balance` |
| Unavailable is never good or bad | Unavailable cards are grey, say "evidence or input missing", and give the reason; they appear in every view | `test_missing_indicators_remain_visible` |
| Hypothetical soil never measured | "Illustrative soil profile — not measured at Katumani" in the soil tab; "hypothetical demonstration soil" in every soil headline; verification "hypothetical" in the soil table; the comparison intro says so | `test_demonstration_soil_is_labelled_illustrative_everywhere` |
| User soil not verified | Soil table shows the stated source and "not verified"; comparison intro says CropShift has not verified it | `test_entered_soil_changes_only_soil_results_and_keeps_provenance` |
| Priorities have no weights | Multiselect order only; "Priorities have no weights" shown; results identical with or without priorities | `test_priorities_do_not_change_the_results` |
| Pilot provisional | Banner, Overview status line, sidebar status, limitations panel | `test_overview_shows_location_source_period_and_origin` |
| No AI-generated science | OpenAI and Manus disabled and shown as such; no AI call exists | `test_app_reports_ai_services_as_disabled_by_default` |

## The five limitations the brief singled out

All five are in the *Important scientific limitations* panel on the Scientific
Evidence tab, built from the report where possible:

1. **Maize rainfall comparison.** The panel quotes the engine's own headline,
   "the documented growing period (125 to 180 days) is longer than the 92-day
   window by 33 to 88 days", and states that season totals are therefore not a
   complete maize water balance.
2. **Cowpea temperature comparison.** "The source gives 25-35 °C without saying
   which temperature it means. A mismatch with NASA's daily mean does not prove
   that cowpea is unsuitable." The cowpea temperature card also carries the
   engine's condition that the source's temperature measure is unstated.
3. **Pigeon pea water information.** Shown only when the report's pigeon pea
   water indicator is unavailable, which it always is: "Nothing is borrowed from
   another crop."
4. **Historical scenarios.** "Past seasons from 2001 to 2025 ... not predictions
   of future seasons."
5. **Pilot status.** The configuration's approval note, verbatim.

## Review of headlines, labels and tooltips

Every string in `app.py` and `src/visualizations.py` was read for overclaiming.
Changes made during the review:

* Overview caption: "names no best rotation" was reworded to "ranks no rotation
  above another", so the phrase "best rotation" appears nowhere on the page
  except inside the engine's list of things it refuses to produce.
* Metric captions say "Descriptions of the past record, not forecasts and not
  scores".
* Evidence-completeness counts are captioned "They are not a score of the
  rotations".
* The distribution chart uses a fixed, deterministic horizontal spread for
  points; no random jitter, so the same data always draws the same picture.

## What the interface does not do

* It does not reword, summarise or add to the engine's explanations.
* It does not hide unavailable results, collapse conditional ones into a
  verdict, or colour any result red or green.
* It does not store what users enter.
