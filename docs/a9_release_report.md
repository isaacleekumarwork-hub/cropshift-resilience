# A9 release report: documentation, publication readiness and submission

Phase A9, 15 November 2026, 14:40 to 15:10 Singapore time. Deadline:
Sunday 15 November, 23:59 in the Local Event's time zone.

**Outcome: the repository is public at
https://github.com/isaacleekumarwork-hub/cropshift-resilience under Apache-2.0,
published with the participant's approval and checked without a login.**
Nothing was deployed or submitted. What remains is the participant's: the demo
deck's names and public link, the Project page, and pressing "Submit for
Judging" (section L).

## A. Executive summary

* The A8 fixes were committed after a secrets check (`aa5efdf`, branch
  `a8-validation`; `main` was not moved).
* A claims register fixes what may be said, what must be qualified and what
  must never be claimed. The README, slides and submission text were checked
  against it.
* The README was rewritten so a judge can understand and run the project in a
  few minutes.
* Eight real screenshots of the running app were captured.
* A seven-slide demo deck was built as a private claude.ai Slides artifact
  from those screenshots and the engine's actual outputs.
* Copy-ready text for every field of the Project page was drafted.
* Installation was tested from a fresh clone, offline, with the lock file.
* The app's own About tab still said "Development stage A5" and listed A8 as
  not started; that text and the phase table were corrected.
* No video was made: the slide deck is the compliant demo, and a video would
  not change the outcome.

## B. Git and release status

| Item | State |
| --- | --- |
| A8 commit | `aa5efdf` on branch `a8-validation` ("Validate science, data and app end to end; fix overclaiming wording (A8)") |
| A9 commit | `bc5bff3` ("Prepare release and submission materials; license under Apache-2.0 (A9)"): LICENSE, README, claims register, submission text, this report, screenshots, the About-tab correction and its tests, provenance, compliance and plan updates, `.gitignore` (`.gstack/`, a local browser tool's folder) |
| `main` | Fast-forwarded to `bc5bff3` after approval |
| Remote | `origin` = https://github.com/isaacleekumarwork-hub/cropshift-resilience (public), created with `gh repo create --public --source . --push`; `main` pushed and tracking `origin/main`. Other local branches were not pushed |
| History rewritten | No. No force-push |
| Author identity | `isaacleekumarwork` with a Gmail address on all three commits (see section E) |

## C. Final scientific claims register

The register is [`a9_claims_register.md`](a9_claims_register.md): 16 safe
claims with their evidence, 11 claims that must carry a qualification, 12
forbidden claims and a list of words to avoid.

**Check of final materials.** The README, the submission text, the release
report and all seven slides were searched for the words to avoid ("best",
"recommended", "optimal", "predicts", "forecast", "will yield", "increases
yield", "proven", "validated", "farmer-tested", "guarantees", "score",
"suitable for your farm") and read against the register. Every hit is a
negation ("does not forecast", "no score", "never name a best rotation"), a
source's own range name ("optimal range"), or the licence ("suggested
licence"). The app's screens were already enforced by tests from A5 and A8.

## D. Documentation completed

| Item | Where |
| --- | --- |
| Answers to the judges' eight questions | `README.md`, first section |
| Installation, Python version, dependencies, lock file | `README.md`, "Run it" (tested from a fresh clone) |
| Launch instructions, local only | `README.md`: `--server.address localhost` |
| Architecture overview | `README.md`, "How it works"; `docs/architecture.md` |
| NASA data methodology | `README.md`; `docs/data_layer.md`, `data_sources.md`, `historical_scenarios.md` |
| Agronomic knowledge methodology | `README.md`; `docs/agronomic_knowledge.md`, `scientific_evidence_audit.md`, `rotation_comparison_methodology.md` |
| Scientific limitations | `README.md`, "What CropShift does not claim"; claims register |
| Provenance and references | `docs/provenance.md` (A9 row added); References field in `a9_submission_text.md` |
| Testing instructions | `README.md`, "Tests" |
| AI-assisted development disclosure | `README.md`; `docs/provenance.md`; SI field text |
| Licence information | `README.md`, "Licence" (pending approval) |
| Reproduction guide | `README.md`, "Reproducing the results" (commands checked) |
| Screenshots | `docs/screenshots/` (eight PNG files) |

## E. Licence and attribution review

**Licence: Apache-2.0, approved by the participant on 15 November 2026.** The
standard text was fetched from GitHub's licence API
(`gh api /licenses/apache-2.0 --jq .body > LICENSE`, 202 lines, SHA-256
`c95bae1d…efe2c`) and the README's licence section and compliance item C1
were updated. It is compatible with every dependency, carries an explicit
patent grant, and matches what the Space Apps terms name as NASA's default.

| Check | Result |
| --- | --- |
| Third-party code copied into the repository | None |
| Third-party packages | 46, all permissive (MIT, BSD, Apache-2.0, MPL-2.0, PSF, MIT-CMU); installed by the user, not redistributed (`compliance.md`) |
| Bundled NASA data | One unmodified POWER response in `data/demo/`. NASA's open data policy allows sharing; both attribution statements are in the README, the app and `data/demo/README.md` |
| POWER courtesy requests | Notify `larc-power-project@mail.nasa.gov` of the use and redistribution once public (compliance item C2). Not sent: that is the participant's message to send |
| Research-derived material | Facts with citations and paraphrased statements. A scan of `data/knowledge/` found no quoted passage of 40 characters or more. Feedipedia's reuse terms were not located (C7); only facts are used, with attribution |
| OpenStreetMap | Attribution "© OpenStreetMap contributors (ODbL)" shown in the app and listed in References |
| Fonts and images in the deck | Space Grotesk and Inter, Google Fonts, SIL Open Font Licence; images are screenshots of the app only |
| NASA branding | No NASA logo, insignia or mission identifier anywhere; "not endorsed by NASA" stated |
| Minors | No people appear anywhere |
| **Git history secrets** | All commits searched for API-key, token and private-key patterns: none. The only `.env`-type file ever committed is `.env.example`, whose key values are empty |
| `.gitignore` | Excludes `.env`, `.env.*` (except the example), `.streamlit/secrets.toml`, `.venv/`, caches, `data/cache/`, databases, logs, `.DS_Store`, `.claude/`, `.gstack/` |
| **Personal data** | No name, e-mail or local path in any tracked file. **The commit author e-mail is a personal Gmail address on all three commits** (compliance item C5): it becomes public on publication. Changing it means rewriting history, which A9 forbids without approval |
| Intended contents only | 84 tracked files plus the A9 additions: code, tests, the NASA response, knowledge JSON, docs and screenshots. Largest file 900 KB (the NASA response) |

## F. Presentation and screenshots

**Screenshots** (`docs/screenshots/`, captured from the running app at
1440 × 900, 2× scale, on 15 November 2026):

| File | Shows |
| --- | --- |
| `01-overview.png` | Overview: provisional pilot site, record at a glance |
| `02-climate-explorer-dry.png` | Climate Explorer, long rains, dry seasons highlighted |
| `02b-seasonal-rainfall-chart.png` | The seasonal rainfall chart alone |
| `03-rotation-comparison.png` | The three strategies side by side |
| `03b-maize-water-use-chart.png` | Season rainfall against maize's indicative water use |
| `03c-rainfall-results-and-missing-evidence.png` | Result cards: maize conditional, cowpea and pigeon pea unavailable |
| `04-soil-inputs.png` | The soil entry form with source labels |
| `05-scientific-evidence.png` | Important limitations and what CropShift does not estimate |

**Slide deck:** seven slides, as the guide requires (title and introduction
included), in English: (1) title, team and challenge; (2) the problem;
(3) the NASA data; (4) how CropShift works; (5) live comparison;
(6) scientific integrity; (7) potential impact and next steps. Built as a
private claude.ai Slides artifact (https://claude.ai/artifact/NXfYrVVpHwFVxQnNHf86qd)
that can be edited and downloaded as PDF or PowerPoint. Every number on the
slides comes from the engine output or the NASA record; every screenshot is
real. Each slide has speaker notes.

Checked by rendering the slide HTML locally: every slide's content stays
inside its margins after one round of fixes (a wrapped headline number, an
over-long column and a split percentage). The deck still holds three
placeholders: `[Team name]`, `[Your full name]` and `[public repository link]`.

The deck is private. Judges cannot open it until it is exported and hosted
publicly (section L).

**Video:** not made. Optional, and the deck carries the scientific caveats
better.

## G. Submission text

[`a9_submission_text.md`](a9_submission_text.md) has copy-ready text for every
field the official guide lists: Project Name, a tagline, the High-Level
Project Summary, Link to Project Demo and Link to Final Project (placeholders),
the Detailed Project Description (what it does, how it works, the problem,
what makes it different, potential benefits, tools, limitations, next steps,
team), Use of Super Intelligence, NASA Data, and Space Agency Partner Data and
Other References (none from partner agencies; full reference list). The
public guide states no character limits; the form itself is behind the
participant's login and was not opened.

## H. Public link status

| Link | Status |
| --- | --- |
| Public repository | **https://github.com/isaacleekumarwork-hub/cropshift-resilience**. Checked without credentials on 15 Nov 2026: the repository page, README, LICENSE, a screenshot and the NASA data file all return HTTP 200; the GitHub API reports visibility public, licence Apache-2.0, default branch main; in a signed-out browser the README renders with all six screenshots loaded |
| Public demo (slides) | **Does not exist.** The deck is a private artifact |
| Hosted app | None, and none is needed: the guide accepts a code repository as the final project link |
| `http://localhost:8501` | Local only. Not a submission link; judges cannot open it |

## I. Final test results

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest` (A9 baseline, before any A9 change) | 905 passed, 1 skipped |
| Fresh clone of `a8-validation`, `uv pip install --offline -r requirements-lock.txt`, then `pytest` | Install OK from the local cache; 905 passed, 1 skipped; `streamlit run` answered its health check (HTTP 200) |
| `pytest tests/test_imports.py tests/test_app.py` after the About-tab correction | 97 passed |
| `.venv/bin/python -m pytest` (final, all A9 code changes in) | **905 passed, 1 skipped** in 102 s |
| App bound to localhost only | Confirmed: `--server.address localhost`, listening on `127.0.0.1:8501` only |
| Browser check of all six tabs (final, headless Chromium) | No error on any tab. Overview 1 chart; Climate Explorer 5 charts; Rotation Comparison 1 chart and 3 downloads; Soil, Evidence and About render; About reads "Development stage A9 of A9: demonstration and submission" |
| Earlier in A9, while capturing screenshots | Dry-season selection, three strategies, soil entry form and the limitations panel all rendered as shown in `docs/screenshots/` |
| Offline operation and priorities | Not re-clicked in A9: covered by the A8 hand walkthrough (tampered-cache offline run, keyboard priority selection), by the fresh-clone run with `OFFLINE_DEMO_MODE=true`, and by the automated tests |

**Tests changed in A9:** `test_phase_plan_is_consistent` and
`test_app_states_its_stage_and_its_limits_honestly` now pin the new state
(A9 current, A8 complete, A6 and A7 deferred with empty modules, About text
naming the internal validation). Both still fail if the state is misreported.
No other test was changed.

## J. Outstanding blockers

1. ~~No public link.~~ **Resolved:** the repository is public (section H).
2. **Demo not hosted.** The deck has to be exported to PDF (or shared publicly)
   and given a link that needs no login.
3. **Placeholders.** Team name and participant name in the deck and the form;
   repository and demo links in the deck and the form.
4. **Submission itself.** Only the participant can tick the two boxes and press
   "Submit for Judging".

Not blockers, but decisions: the licence, the commit e-mail address, and how
to present the pilot site (provisional, as everywhere now, unless approved).

## K. Submission checklist

| Item | Status | Evidence |
| --- | --- | --- |
| Final code passes tests | Passed | 905 passed, 1 skipped (section I) |
| A8 fixes committed | Passed | `aa5efdf` |
| README complete | Passed | Answers all eight questions |
| Installation instructions tested | Passed | Fresh clone, offline, lock file |
| Scientific claims audited | Passed | Claims register; section C |
| NASA attribution complete | Passed | README, app, `data/demo/README.md`, NASA Data field |
| AI-use disclosure complete | Passed (participant to add any other tools) | README, provenance, SI field |
| Third-party licences checked | Passed | Section E |
| Project licence approved | Passed | Apache-2.0 approved 15 Nov 2026; `LICENSE` added |
| Public repository approved and published | Passed | Approved 15 Nov 2026; section H |
| Public link verified without login | Passed for the repository; **not done** for the demo | Section H |
| Seven-slide deck or compliant video created | Passed (placeholders remain) | Private Slides artifact |
| Demo assets checked | Passed | Real screenshots; local render check |
| Submission text prepared | Passed | `a9_submission_text.md` |
| Official form requirements checked | Passed (public guide; form not opened) | Section G |
| Submission completed by the participant | **Not done** | Participant only |
| Confirmation of submission recorded | **Not done** | After submission |

## L. Exact participant actions needed

Steps 1 to 3 were completed on 15 November 2026 after the participant
approved the licence and publishing. The commit e-mail was published as it
was. The rest, in order, with the time each takes:

1. ~~**Decide**~~ (done: Apache-2.0, publish). Still open: team name and your
   full name as they should appear.
2. ~~**Commit and publish**~~ (done; the commands used, for the record):

   ```bash
   gh api /licenses/apache-2.0 --jq .body > LICENSE
   ```

   ```bash
   git add -A && git commit -m "Prepare release and submission materials (A9)"
   ```

   ```bash
   git switch main && git merge --ff-only a8-validation
   ```

   ```bash
   gh repo create cropshift-resilience --public --source . --remote origin --push --description "Compare crop rotations against 25 years of NASA climate history, with evidence and uncertainty in plain view. NASA Space Apps 2026."
   ```

3. ~~**Check the repository link**~~ (done without credentials; a private
   window check of your own is still worthwhile, 1 minute).
4. **Finish the deck** (5 minutes): replace the two remaining placeholders
   (`[Team name]`, `[Your full name]`; the repository link is filled in), then
   export it as PDF from the deck's Share menu. Add the PDF to the repository
   (for example `docs/presentation/CropShift_RESILIENCE_demo.pdf`) and push,
   or upload it to Google Drive with "anyone with the link" access. Check the
   link in a private window.
5. **Fill in the Project page** (10 minutes) from `a9_submission_text.md`,
   replacing the placeholders and adding any other SI tools you used. Upload
   two or three screenshots from `docs/screenshots/` (the page accepts PNG up
   to 10 MB). Save progress.
6. **Submit** before 23:59: tick "Terms and Conditions" and "Confirm All Work
   is Original", press "Submit for Judging", and confirm the banner appears.
7. **Afterwards**: optionally e-mail the NASA POWER project
   (`larc-power-project@mail.nasa.gov`) about the use and redistribution of
   its data, and optionally ask the Local Lead whether the provisional site
   needs any mention.

## M. Post-submission roadmap

1. **Local validation first:** review by Kenyan agronomists of the knowledge
   base, the season windows and the pilot site; sessions with farmers and
   extension officers to learn which results they understand and use.
2. **Science:** compare NASA POWER with local station records; add a daily
   soil water balance with FAO-56 reference evapotranspiration (needs wind
   speed); find which temperature statistic each crop range means; add local
   variety and planting-calendar data.
3. **Reach:** more sites and crops; Kiswahili; a shorter comparison page;
   text alternatives for charts.
4. **A6, grounded explanations:** revisit only after user testing shows the
   six-part explanations are not enough. If built, restrict it to restating the
   engine's own report, label every generated sentence, keep it optional and
   off by default, and test it against the claims register.
5. **A7, research workflows:** revisit after the competition for deeper,
   verified literature work, with every citation checked by hand, and only
   after the China-affiliation question (compliance item C4) is resolved.

The disabled integration placeholders (`src/openai_service.py`,
`src/manus_service.py`, the `ENABLE_OPENAI` and `ENABLE_MANUS` settings and
their tests) are kept unchanged for this.
