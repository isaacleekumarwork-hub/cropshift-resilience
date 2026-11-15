# Compliance review

Completed on 14 November 2026 as the gate for phase A2, before the NASA data
layer was written. It covers the official Terms & Conditions, licensing,
attribution and the conditions attached to the NASA data this project uses.

**Outcome: no blocker.** Retrieving and caching NASA POWER data is permitted.
Six items need the participant's attention; they are listed at the end.

This is a careful reading by a non-lawyer, not legal advice.

## Sources read

| Document | Address | Read |
| --- | --- | --- |
| 2026 NASA Space Apps Participant Terms and Conditions (updated 7 August 2026) | https://www.spaceappschallenge.org/legal/ | In full |
| NASA Earth science Data and Information Guidance | https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-information-guidance | In full |
| NASA POWER Referencing Guide | https://power.larc.nasa.gov/docs/referencing/ | In full |
| NASA POWER Daily API documentation | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ | In full |
| NASA POWER methodology: meteorological and energy-flux data sources | https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/ and `.../sources_fluxes/` | Relevant sections |

The NASA Privacy Policy linked from the Space Apps site was not read; it
concerns the participant's own account data rather than this project.

## 1. Terms and Conditions

| Topic | What the terms say | Where this project stands |
| --- | --- | --- |
| Licence of original work | Original content must be "freely available without restriction or ... licensed as open source as defined by the Open Source Initiative". "If you do not specify a specific OSI compliant license, NASA will distribute your original content under an Apache 2.0 license." | **Met (C1, 15 Nov 2026).** The participant approved Apache-2.0; `LICENSE` holds the standard text. |
| Third-party materials | Non-NASA materials must be "freely and publicly available without restriction or, at a minimum ... licensed as open source". Their licences "must be identified in the documentation that you submit". | Met. All 46 installed packages are under permissive open-source licences (section 3). Nothing else from a third party is used. |
| Citing sources | "You must cite every source that is used in the creation of your project, even if it is open source or freely available." NASA may remove awards from teams that do not. | Met so far. `provenance.md` is the running list for the References field. |
| Addressing a challenge | Solutions "shall directly address one or more" challenges. | Met. |
| Prohibited content | No promotion of "commercial services or products"; no proprietary information; no personally identifiable information; nothing the participant lacks the rights to. | Met. See C3 on how optional paid services are described, and C5 on the commit e-mail address. |
| Minors | "Recognizable names, voices, and likenesses of persons under the age of 18 should not be included." | Met. No people appear anywhere. |
| China affiliation | Participants "may not participate, collaborate, or coordinate with China or any Chinese-owned entity in relation to their participation". | **Check needed (C4)** before the optional Manus integration. Nothing in A1 or A2 is affected. |
| Participation | In a personal capacity, under one's own name; registered before the start. | Participant's responsibility. |
| Export control | No export-controlled information. | Met. Open weather data and general-purpose code only. |
| Publicity and media | Submitting grants NASA permission to display and distribute the solution and to use the participant's name and likeness for the event. | For the participant to be aware of. |

## 2. NASA data: use, caching and attribution

**Use and caching are permitted.** NASA's stated policy is that it "promotes
the full and open sharing of data with the research and applications
communities, private industry, academia, and the general public", with no
period of exclusive access and non-discriminatory access for all users. Nothing
in the POWER documentation restricts storing responses locally. Caching is in
fact what POWER asks for:

> "with the 0.5° x 0.5° global grid you only need to submit one request per
> cell. If your application persists in requesting the same relative location,
> it will potentially be blocked."

How this project complies: every verified response is cached and reused, an
identical request is never sent twice while its cache entry is valid, retries
are bounded, and phase A2 requests exactly one location.

**Attribution.** The POWER Referencing Guide asks for two statements whenever
its data is used, naming the service, version and access date:

> The data was obtained from National Aeronautics and Space Administration
> (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources
> (POWER) project funded through the NASA Earth Science Division.

> The data was obtained from the POWER Project's Hourly 2.x.x version on
> YYYY/MM/DD.

How this project complies: both statements are generated automatically for
every dataset, with the real service name ("Daily"), version and access date,
and stored in `DatasetProvenance.citations`. They are shown in the app, printed
in `data/demo/README.md` and repeated in `data_sources.md`. This corrects the
wording drafted in A1, which named a different funding programme.

**Requests from the POWER project (courtesy, not conditions).** The guide also
"kindly requests" a reference or brief description of any use of POWER data,
and "requests notification if POWER data is transmitted to other researchers",
both to `larc-power-project@mail.nasa.gov`. This project bundles one real POWER
response in `data/demo/` and will be published, so a short notification would
honour both requests. See **C2**. No message has been sent.

**Special conditions on the data used.** None found beyond the above. MERRA-2
and CERES SYN1deg, the products behind the POWER parameters used here, are NASA
products under the same open policy and are cited in `data_sources.md`.

**No implied endorsement.** NASA "does not endorse any non-U.S. Government
entity" (official challenge Resources page). The app footer, every dataset's
caveats and the README state that the project is not endorsed by NASA. No NASA
logo, insignia or mission identifier is used.

## 3. Third-party software licences

Read from the metadata of the packages installed on 14 November 2026.

### Direct dependencies

| Package | Version | Licence |
| --- | --- | --- |
| Streamlit | 1.67.0 | Apache-2.0 |
| pandas | 3.1.1 | BSD-3-Clause |
| NumPy | 2.5.4 | BSD-3-Clause (bundles components under 0BSD, MIT, Zlib and CC0-1.0) |
| Plotly | 6.9.0 | MIT |
| Pydantic | 2.14.3 | MIT |
| pydantic-settings | 2.16.3 | MIT |
| HTTPX | 0.28.1 | BSD-3-Clause |
| pytest | 9.2.0 | MIT |

### All installed packages, including indirect ones

46 packages in total: 19 MIT, 16 BSD (2- or 3-clause), 7 Apache-2.0 (one of
them dual Apache-2.0 or BSD-2-Clause), 1 MPL-2.0, 1 PSF-2.0, 1 MIT-CMU and
NumPy as above. All are permissive licences that allow use, modification and
redistribution. None is copyleft in a way that would constrain this project's
own licence, and none is proprietary.

Two notes for completeness: CC0-1.0 (inside NumPy) is a public-domain
dedication rather than an OSI-approved licence, which satisfies the terms'
"freely and publicly available without restriction" alternative; and MIT-CMU
(Pillow, installed by Streamlit) is a permissive licence whose OSI listing was
not checked.

The project redistributes none of these packages. They are installed by the
user from the Python Package Index.

### Tools used to build the project

uv (Apache-2.0 or MIT) for the Python environment, and Claude Code (Anthropic),
a commercial AI coding assistant, used as a development tool. Neither is part
of the solution or needed to run it. AI use is disclosed in `provenance.md`.

## 4. Items needing the participant's attention

| ID | Item | Why it matters | Suggested action |
| --- | --- | --- | --- |
| C1 | ~~Choose a licence for the project.~~ **Resolved in A9.** | Required by the terms. | Apache-2.0 approved by the participant on 15 Nov 2026 and added as `LICENSE`. |
| C2 | **Notify the NASA POWER project.** | POWER asks to hear about uses of its data and about redistribution. | Send a short note to `larc-power-project@mail.nasa.gov` once the project is public. A draft can be prepared in A9. |
| C3 | **Describe optional paid services neutrally.** | The terms exclude "material that promotes commercial services or products" and require third-party materials to be free or open source where the solution *requires* them. | OpenAI and Manus stay optional and off by default, and the solution works fully without them. In the submission, describe them as optional integrations, or leave A6 and A7 out. |
| C4 | **Check the Manus service against the China-affiliation rule before A7.** | The terms forbid collaborating or coordinating with "any Chinese-owned entity" in relation to participation. Whether a commercial tool falls under this, and who owns Manus today, was not verified. | Confirm with your Local Lead, or skip A7. |
| C5 | **Your e-mail address is in the Git history.** | The terms exclude personally identifiable information from submissions. An author e-mail in commit metadata is ordinary for public repositories and you chose it, but it becomes public on publication. | Keep it, or switch to a no-reply address before publishing. |
| C6 | ~~Pilot-site background is not yet cited.~~ **Resolved in A3.** | The terms require every source to be cited. | The description in `src/pilot_sites.py` was rewritten so that each factual statement rests on a registered source or on the NASA record; uncited statements were removed, and the two inferences it relies on are declared. |
| C7 | **Thirteen agronomic sources must go into the References field.** | "You must cite every source that is used in the creation of your project." | Copy the citations from `evidence_registry.md`. Feedipedia's terms of reuse were not located: only facts and short quotations are used, with attribution, which is ordinary citation. |
| C8 | **The pilot site is still not approved.** | The A4 brief uses Katumani provisionally; every comparison report says so, and the site must not be presented as final until approved. | Approve the Katumani site, or name another, before A9. |
| C9 | **Two sources added in A4 must be cited.** | The ETCCDI index definitions define wet days, dry spells, heavy-rain days and frost days; OpenStreetMap Nominatim was used once to check that the pilot coordinates lie in Machakos County. OpenStreetMap data is © OpenStreetMap contributors under the ODbL and needs that attribution wherever it is shown. | Add both to the References field (`provenance.md` lists them). Nominatim's usage policy allows occasional single requests; it is not used by the app. |
