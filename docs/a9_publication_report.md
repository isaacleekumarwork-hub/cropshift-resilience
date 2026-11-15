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
| Old public repository (personal e-mail in its history) | Pending participant action: delete it on GitHub |
| New public repository from the rewritten history | Pending: created right after the deletion (section B) |
| Public access checked without login | Pending: after the new push (section H) |
| NASA Space Apps submission | Pending participant action; not authorised for the assistant |

## B. Public GitHub URL

`https://github.com/isaacleekumarwork-hub/cropshift-resilience`, the same name
as the first publication, so the links in the submission text and the deck
stay valid. Section H records the check after recreation.

## C. Git branch and final commit

Branch `main`. The final commit hash is the `main` head that is pushed; it is
recorded in section H after the push. Commit hashes before the rewrite are
obsolete and must not be used as release identifiers.

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

See section H for the run on the final commit. Expected and previously
observed: 905 passed, 1 skipped (the live NASA test, run on request).

## H. Public accessibility verification

Filled in after the new repository is pushed.

## I. Presentation status

* Seven slides; title slide names CropShift RESILIENCE, team WindShift and
  Isaac Lee Kumar; last slide gives the repository URL.
* Editable source: the private claude.ai Slides artifact.
* Public copy: `docs/presentation/CropShift_RESILIENCE_demo.pdf`, seven
  1920 × 1080 pages rendered from the deck's own slide files and checked page
  by page.

## J. Submission text status

`docs/a9_submission_text.md` is ready to paste: project, team and participant
names, the repository link and the demo link are filled in, the AI disclosure
separates development assistance from the deterministic app and the disabled
OpenAI and Manus integrations, and no external review or farmer testing is
claimed. One bracketed note asks the participant to add any other SI tools
used outside the repository.

## K. Remaining participant actions

1. Delete the old repository (step needed before the new push).
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
