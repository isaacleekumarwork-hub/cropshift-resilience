# A9 publication report

Team WindShift, CropShift RESILIENCE, 15 November 2026 (Singapore time).
Statuses: **Completed** (done), **Verified** (done and checked), **Pending
participant action**, **Blocked**.

## A. Final release status

| Step | Status |
| --- | --- |
| Apache-2.0 licence, copyright notice | Verified |
| Commit identity rewritten to an anonymous address | Verified (section D) |
| A9 changes committed with the new identity | Verified |
| Old public repository (personal e-mail in its history) | Completed: deleted by the participant; verified 404 |
| New public repository from the rewritten history | Verified (section B) |
| Public access checked without login | Verified (section H) |
| NASA Space Apps submission | Pending participant action; not authorised for the assistant |

## B. Public GitHub URL

**https://github.com/isaacleekumarwork-hub/cropshift-resilience**, created
as a new public repository after the participant deleted the first one. Same
name, so the links in the submission text and the deck are unchanged.
Description: "CropShift RESILIENCE by Team WindShift — transparent
crop-rotation comparisons using NASA historical climate data and traceable
agronomic evidence."

## C. Git branch and final commit

Branch `main`. Release commit `b276ed4` ("Add NOTICE and copyright; name team
WindShift; record identity rewrite (A9)"), pushed to an empty repository with
a normal push (no force, no mirror). This report's results were added in the
commit after it. Commit hashes from before the rewrite are obsolete.

## D. Git identity rewrite

**What changed.** Every commit on `main` (six, from the A1 foundation to the
demo deck) originally carried the participant's personal e-mail as author and
committer, and the first publication made them public. With the
participant's approval:

* author and committer were set to `Isaac Lee Kumar <windshift@noreply.invalid>`
  (`.invalid` is a reserved top-level domain, so the address cannot belong to
  anyone or receive mail; at the participant's request it contains no account
  name);
* the rewrite used `git filter-branch --env-filter` on `main`, `a8-validation`
  and `phases-a2-to-a5`, changing identity fields only;
* the repository-local Git configuration now uses the same identity; global
  Git settings were not touched.

**Verification against a private audit record made before the rewrite:**

| Check | Result |
| --- | --- |
| Commit count | 6 before, 6 after |
| File trees | Identical for all six commits (tree hashes compared) |
| Full commit messages | Identical |
| Author and committer dates | Identical |
| Author and committer identity | All six: `Isaac Lee Kumar <windshift@noreply.invalid>` |
| Personal e-mail anywhere in `main`'s history (metadata and patches) | Absent |
| Branches | `main`, `a8-validation` and `phases-a2-to-a5` point to rewritten history |

**Backups**, outside the repository and never published: a verified Git
bundle of the original history and an audit file of the original commit,
tree, dates and subjects, in a private folder beside the project; and a local
`refs/backup/` reference. Only `main` is pushed.

**What a rewrite cannot undo.** The first repository was public from about
15:24 to the deletion. Anyone who looked, any cache, and any archive of public
GitHub activity may have kept the original commits. No forks, stars or
watchers were recorded, and the repository's public event feed was empty when
checked.

**Remaining mention.** The old Git author name (the account name without its
`-hub` suffix) appears once as text in an earlier version of
`a9_release_report.md` inside the history; the current file no longer has
it. Removing it from history would change file contents, which the release
brief asked to preserve. The GitHub account name itself is part of the
repository URL and cannot be removed without another account or an
organisation.

## E. Apache-2.0 licence

* `LICENSE`: the standard Apache License 2.0 text from GitHub's licence API,
  unmodified (202 lines).
* `NOTICE`: "Copyright 2026 Isaac Lee Kumar", the licence, the NASA POWER
  attribution and "not endorsed by NASA".
* README: copyright line and links to `LICENSE` and `NOTICE`.
* Third-party licences unchanged and listed in `compliance.md`; no
  incompatible content (all 46 packages permissive; nothing copied from other
  projects; knowledge data holds cited facts, no long quotations).

## F. Privacy and security audit

| Check | Result |
| --- | --- |
| Secrets in history, working tree or index | None (API-key, token and private-key patterns) |
| `.env` files | Only `.env.example`, with empty key values |
| Personal e-mail in files or history to be published | None |
| Local paths, scratch or backup files | None tracked; backups live outside the repository |
| Browser tool and caches | `.gstack/`, `.venv/`, `.pytest_cache/`, `data/cache/`, logs, `.claude/` ignored |
| Screenshots and deck | App screens only; the deck names the team and participant by approval |
| NASA data | Unmodified POWER response with full attribution in README, NOTICE, app and `data/demo/README.md` |
| Public names | Team WindShift and Isaac Lee Kumar, as approved |

## G. Final test results

| Run | Result |
| --- | --- |
| `.venv/bin/python -m pytest` on `b276ed4` | **905 passed, 1 skipped** (the live NASA test, run on request) |
| App on `--server.address localhost` | About tab: "Development stage A9 of A9"; OpenAI and Manus disabled; no errors. All six tabs checked earlier in A9 with no errors |
| Scientific results | Unchanged: no code changed after the A9 About-tab correction; the identity rewrite kept every file tree identical |

## H. Public accessibility verification

Checked on 15 November 2026 without credentials (plain HTTP requests and a
signed-out headless browser):

| Check | Result |
| --- | --- |
| Old repository | Gone: API and page return 404 |
| Visibility, licence, default branch | Public, Apache-2.0, `main` |
| Branches and tags pushed | `main` only; no tags; no backup or old-history refs |
| Commit identities (7 commits) | All `Isaac Lee Kumar <windshift@noreply.invalid>` for author and committer |
| Personal e-mail or old author name in any public commit patch | None |
| Old commit hashes | 404 in the new repository |
| README | Renders; all six screenshots load; NASA attribution, "not endorsed by NASA", limitations and the copyright line present |
| `LICENSE`, `NOTICE`, source, NASA data file | HTTP 200 |
| Demo PDF and its GitHub page | HTTP 200 |

## I. Presentation status

* Seven slides; title slide names CropShift RESILIENCE, team WindShift and
  Isaac Lee Kumar; last slide gives the repository URL.
* Editable source: the private claude.ai Slides artifact.
* Public copy: `docs/presentation/CropShift_RESILIENCE_demo.pdf`, seven
  1920 × 1080 pages rendered from the deck's own slide files and checked page
  by page. Same file name, so the demo link is unchanged.
* Look (updated 15 Nov 2026, at the participant's request): every slide sits
  on the participant's AI-generated painting of a wheat field under a swirling
  night sky, watermarked "AI-generated image (SI) · imaginary landscape, not
  the pilot site" on every slide. The cover writes the title, tagline and team
  directly on the painting (an edgeless shade and a letter halo keep it above
  4.5:1 contrast); the other slides keep text on solid dark panels. A second
  image the participant offered for the cover was not used because it showed
  a child, which the Project Submission Guide does not allow in demos. Content,
  numbers and the real app screenshots are unchanged. The AI-use disclosures
  in the README, `provenance.md` and the submission text say so.

## J. Submission text status

`docs/a9_submission_text.md` is ready to paste: project, team and participant
names, the repository link and the demo link are filled in, the AI disclosure
separates development assistance from the deterministic app and the disabled
OpenAI and Manus integrations, and no external review or farmer testing is
claimed. One bracketed note asks the participant to add any other SI tools
used outside the repository.

## K. Remaining participant actions

1. ~~Delete the old repository~~ (done).
2. Paste the submission text into the Project page; check both links in a
   private browser window.
3. Tick the two boxes and press "Submit for Judging"; confirm the banner.

## L. Deadline

Sunday 15 November 2026, 23:59 Singapore time (the Local Event's time zone).

## M. A6 and A7

Both stay deferred and switched off. Revisit A6 (grounded, multilingual or
conversational explanations) only after user testing shows the six-part
explanations are not enough; revisit A7 (deeper, verified research workflows)
after the competition, once the China-affiliation question (compliance C4) is
settled. Their placeholders and settings are unchanged.
