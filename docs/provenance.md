# Provenance record

A running record of what was built, when, with what help and from which
external resources. It exists so that the submission's "Use of Super
Intelligence (SI)" and "References" fields can be filled in accurately, and so
that the project's originality can be shown if asked.

## Project facts

| | |
| --- | --- |
| Project | CropShift RESILIENCE |
| Event | NASA Space Apps Challenge 2026, 14–15 November 2026 |
| Local Event | Singapore |
| Challenge | Field Shift: Adapting Farms with NASA Data |
| Team | Solo participant |
| Repository started | 14 November 2026, from an empty folder |

## Work log

Times are Singapore time. Add a row for every phase.

| Date | Phase | What was done |
| --- | --- | --- |
| 14 Nov 2026, morning | A1 | Audited the empty working folder. Reviewed the official challenge page, Resources tab, Judging & Awards Guide, Project Submission Guide and Participant FAQs. Probed the NASA POWER API. Created the repository structure, typed configuration, scientific data contracts, placeholder modules, a minimal Streamlit page, 137 automated tests and the documentation in `docs/`. |

## State of the folder before work began

The working folder `CropShift` was created on 14 November 2026 and was empty.
It was not a Git repository. No credentials, configuration or tests existed.
No OpenAI, Manus, NASA or Earthdata environment variables were set in the
shell.

## Earlier practice project: not used

A separate practice project named "FarmLab-Practice" exists elsewhere on the
participant's computer, with files dated 5 to 11 November 2026, before the
hackathon began.

* It was checked for by listing file and folder **names only**.
* **No file in it was opened, read, copied or adapted.**
* Nothing in this repository derives from it.

Both projects use Streamlit with `src/`, `tests/` and `docs/` folders, which is
a common layout and was specified independently in the A1 brief.

The official FAQ states: "Teams are not allowed to begin working on the
challenges prior to the hackathon." Keeping the practice project entirely out
of this repository is the cautious course. Whether practice work on a related
theme needs to be mentioned to the Local Lead is the participant's call.

## Use of AI tools

The 2026 official materials call these tools "Super Intelligence (SI)".

| Tool | Used for | Not used for |
| --- | --- | --- |
| Claude Code (Anthropic), an AI coding assistant | Writing the code, tests and documentation in this repository under the participant's direction; reading the official challenge pages; probing the NASA POWER API | Generating images, video or audio; generating any scientific data or results |

How the work was directed: the participant supplied a written brief for the
phase, including the product concept, architecture, scope and acceptance
criteria. The assistant carried it out, and the participant reviews and
approves each phase before the next begins.

Marking of AI-assisted material, as the Project Submission Guide requires for
code ("descriptive text and metadata"):

* every Python module states it in its opening docstring;
* this file and `README.md` state it;
* the app's footer states it.

No AI-generated images, video or audio are in this project. If any are added,
they need a visible watermark. No NASA logos or mission identifiers are used.

The participant should complete the SI field of the submission form in their
own words, and add any other AI tools they used outside this repository.

## External resources

To be copied into the "References" field. Update whenever something is added.

### NASA data and resources

| Resource | Use so far | Link |
| --- | --- | --- |
| NASA POWER API (v2.10.3) | Six probe requests on 14 Nov 2026 to check availability; responses not stored. Planned as the main data source from A2. | https://power.larc.nasa.gov/ |
| GPM IMERG precipitation | Confirmed available through NASA POWER. Planned from A2. | https://gpm.nasa.gov/data |

### Official Space Apps pages consulted

Listed with addresses in `requirements_matrix.md`. Short passages are quoted
there to record requirements accurately.

### Software

All open source, installed from the Python Package Index. Versions are those
installed on 14 Nov 2026.

| Package | Version | Purpose | Licence |
| --- | --- | --- | --- |
| Python | 3.12.13 | Language | PSF |
| Streamlit | 1.67.0 | Web interface | Apache 2.0 |
| pandas | 3.1.1 | Tabular data | BSD 3-Clause |
| NumPy | 2.5.4 | Numerical arrays | BSD 3-Clause |
| Plotly | 6.9.0 | Charts | MIT |
| Pydantic | 2.14.3 | Typed data contracts | MIT |
| pydantic-settings | 2.16.3 | Typed configuration | MIT |
| HTTPX | 0.28.1 | HTTP requests (from A2) | BSD 3-Clause |
| pytest | 9.2.0 | Tests | MIT |
| uv | 0.11.32 | Environment and package installation | Apache 2.0 / MIT |

Licences are as commonly published for these projects and should be confirmed
before submission.

### Code, text and images from other projects

None. No code, text or image was copied from another project.

### Scientific references

None used yet. Dataset citations planned for A2 are drafted in
`data_sources.md`. Crop and soil references are added in A3.

## Data in the repository

None. No NASA data, crop data or results are stored in the repository at the
end of A1. Test files contain only made-up fixture values that are labelled as
such.
