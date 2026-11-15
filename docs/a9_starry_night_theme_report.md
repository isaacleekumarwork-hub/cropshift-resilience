# A9.UI.1: Starry Night visual theme, Post-Impressionist edition

Team WindShift, CropShift RESILIENCE. Prepared on branch
`ui/starry-night-theme`, 15 November 2026. **Presentation only.**

## Update, 18:55: the participant's painting replaces the drawn background

At the participant's request the app now uses the same painting as the demo
deck: a wheat field under a swirling night sky in the style of Van Gogh, an
AI-generated image the participant created (no people; imaginary landscape,
not the pilot site).

* `static/theme/wheatfield_night_wide.jpg` is the page background on
  landscape screens; `wheatfield_night_tall.jpg` (the participant's tall
  version) is used on portrait screens and in the tall sidebar;
  `wheatfield_night_banner.jpg` is a strip cut from the wide version (sky,
  hills, the lit farmhouse, the edge of the wheat, the cypress), shown as its
  own layer and cropped to fit, never stretched.
* The SVG background and banner drawn by `scripts/make_theme_artwork.py` were
  removed; the script now draws only the brushstroke ornaments (frame,
  underline, divider, sidebar edge, canvas grain).
* Every page's credit now reads "Background: AI-generated image (SI) by the
  participant, in the style of Van Gogh; imaginary landscape, not the pilot
  site"; the About caption, README, provenance and submission text say the
  same.
* Metric values and labels now wrap instead of being cut short (a narrow
  window had shown "20…" for 209 mm).
* Contrast tests now assume pure white under every panel, since the painting
  has near-white strokes; all text still passes WCAG AA.
* Checked in a browser at 1440 px, 1018 px and 375 px: no errors, no
  horizontal overflow, no truncated metric; the wide painting on landscape
  screens and the tall one on the phone.

The sections below describe the first version and remain accurate except
where this update supersedes them.

## 1. What changed

The interface now reads as a scientific tool set inside a painted night
landscape rather than a dark dashboard with a wallpaper.

| Area | Treatment |
| --- | --- |
| Page background | An original painted night sky: about 2,000 short directional brushstrokes laid along a wind-and-vortex flow field, haloed stars made of loose dabs, a crescent moon, and below the horizon rolling fields (blue hills, green pasture, ochre stubble, golden wheat, olive foreground) with furrow and wheat strokes and a farmhouse. A canvas-grain tile sits over it. |
| Impasto | Every stroke has a thin pale copy offset up and left, so the paint seems to catch light. |
| Main canvas | A solid painted panel (86 % opaque) in a brushed frame, with a painted strip of wind, stars and wheat across its top. |
| Sidebar | The night painting under a dark glaze, with a brushed gold-and-cobalt edge. |
| Headings | Georgia, warm ivory, a gold brushstroke beneath section titles; a gold star before the title; the tagline "Finding clarity in changing seasons." in italic gold. |
| Navigation | The selected tab is underlined with a gold brushstroke. |
| Cards | Solid painted panels with brush-cut, unequal corners and an offset paint-layer shadow (not glassmorphism). |
| Expanders, alerts, buttons | Hand-drawn edges; buttons in cobalt or gold with paint-layer shadows; gold borders on hover. |
| Dividers | A long painted stroke of blues with a thread of gold. |
| Charts | Exact Plotly marks on dark navy inside a painted frame; ivory text and bar edges; light dotted guides. |
| Footer | Painted divider; the AI-artwork credit. |

Colours: midnight `#101B38`, cobalt `#24477A`, swirling blue `#527DA6`,
golden yellow `#F3C94E`, warm ivory `#F4E8C8`, with blue-green, olive and
ochre in the fields. Gold is an interface accent only; it never marks a result
as better.

## 2. Artwork, rights and disclosure

* **No reproduction was used.** *The Starry Night* (1889) is in the public
  domain, but its holder, MoMA, offers no open-licence image, so the brief's
  fallback applies: original artwork inspired by the painting. Nothing was
  downloaded.
* **How it was made.** `scripts/make_theme_artwork.py` paints every SVG in
  `static/theme/` deterministically (fixed seeds); a test regenerates them and
  checks they match byte for byte.
* **AI-generated, so watermarked.** The Project Submission Guide requires a
  visible watermark on SI-generated images. The background carries the text
  "Original AI-generated artwork (SI) · after Vincent van Gogh, The Starry
  Night (1889) · imaginary landscape"; every page also shows a credit in the
  header strip and in the footer.
* **Not the pilot site.** The landscape is imaginary; the image description
  and the credit say so.
* **Disclosures updated on this branch:** the app's About caption and footer,
  `README.md` (Media), `docs/provenance.md` and the SI field in
  `docs/a9_submission_text.md`. `main` still says "no AI-generated images",
  which is true for `main`.

## 3. Files changed

| File | Change |
| --- | --- |
| `src/ui_theme.py` | New: `apply_starry_night_theme()`, `theme_figure()`, `card_key()`, the stylesheet, palette and contrast constants |
| `scripts/make_theme_artwork.py` | New: paints the artwork |
| `static/theme/*.svg` | New: background (241 KB), banner (83 KB), frame, underline, divider, edge, canvas grain (under 10 KB each) |
| `.streamlit/config.toml` | Dark theme palette, fonts, borders, status-text colours; `enableStaticServing` |
| `app.py` | Applies the theme after page setup; tagline; charts pass through `theme_figure`; cards get keys; AI-artwork wording in two captions |
| `src/__init__.py`, `tests/test_imports.py` | Register the new module |
| `tests/test_ui_theme.py` | New: 17 tests |
| `README.md`, `docs/provenance.md`, `docs/a9_submission_text.md` | AI-artwork disclosure |
| `docs/screenshots/starry-night/` | Nine screenshots of the themed app |

**Not changed** (checked with `git diff main` on these paths): the comparison
engine, NASA client, cache, validation and processing, data service, soil
inputs, scenario engine, evidence audit, knowledge loader, uncertainty,
configuration code, chart construction (`src/visualizations.py`), UI state,
and everything in `data/`. OpenAI and Manus remain off.

## 4. Visual review

Screenshots: `docs/screenshots/starry-night/after-01` to `after-09` (six tabs,
the result cards, and two mobile views at 375 px). The questions from the
amendment, answered against them:

1. **Post-Impressionist oil painting?** Yes. The sky, banner, sidebar and
   frame all speak the same language of short, directional, layered strokes,
   haloed stars and swirling wind. It is vector paint, not a photograph of
   impasto, so up close it reads as stylised brushwork.
2. **Directional brushstrokes visible?** Yes: around the canvas, in the
   banner, through the sidebar glaze, and in the frame, underlines and
   dividers.
3. **Texture and movement?** Yes, through the stroke flow, the vortex and the
   offset highlights, with a faint canvas grain. There is no animation, by
   design (no distracting motion; reduced-motion users lose nothing).
4. **Expressive blues and yellows?** Yes: cobalt and ultramarine strokes
   against gold stars and wheat, with ochre and olive fields.
5. **Cohesive?** Largely. Headings, tabs, cards, expanders, buttons, dividers
   and chart frames share one painted vocabulary. Streamlit's own controls
   (radio buttons, select boxes, tables) follow the palette but keep their
   standard shapes, for usability.
6. **Agricultural connection?** Yes: rolling cultivated fields, golden wheat
   and a farmhouse in the background and the banner, labelled as imaginary.
7. **Every chart, label and qualification readable?** Yes. Text sits on solid
   panels; see section 5.
8. **Offline?** Yes. The artwork is served by the app itself; the browser
   made no request outside `localhost`; fonts are Streamlit's bundled font
   and the system's Georgia.
9. **Scientific outputs unchanged?** Yes. No engine or data file changed; all
   905 earlier tests still pass; new tests confirm every chart keeps its data,
   units, names, hover text and category colours.

## 5. Accessibility findings

| Check | Result |
| --- | --- |
| Body, secondary, gold and status text over the brightest artwork under a panel (and on cards) | All at least 4.5:1 (tested); measured in the browser: "Conditional" 9.7:1, "Unavailable" 9.8:1 |
| Primary button label (midnight on gold) | Above 4.5:1 |
| Chart text, band label | Above 4.5:1 on the chart paper and plot |
| Bar edges and dotted guides | At least 3:1 (ivory edges fix the wet-season blue, which would fall below 3:1 on navy) |
| Status meaning | Still carried by the words Supported, Conditional, Unavailable, never by colour alone |
| Keyboard focus | 3 px gold outline on every focusable element |
| Reduced motion | No animation; a reduced-motion rule also stops any transition |
| Decorative title star | Hidden from screen readers (empty alternative text) |
| Layout | No horizontal overflow on any tab at 1440 px or 375 px; metric labels no longer cut off |
| Not checked | Firefox and Safari (Chromium only); a screen-reader pass |

## 6. Tests

| Run | Result |
| --- | --- |
| `.venv/bin/python -m pytest` on the branch | **922 passed, 1 skipped** (905 earlier tests plus 17 new) |
| `tests/test_ui_theme.py` | CSS only, no script, no external address; artwork local, small, script-free and regenerated exactly; static serving and dark theme configured; fallback without artwork; watermark and credit present; WCAG AA contrast; chart data unchanged; dark lines recoloured; card classes; off switch; the app runs themed and classic |
| Browser (headless Chromium) | Six tabs: no errors, no overflow; charts 1, 5 and 1 on the chart tabs; 54 painted cards on the comparison tab |

## 7. Performance

About 340 KB of SVG, served once by the app and cached by the browser; no
script, no animation, no blur filter on large surfaces. The background is
fixed on desktop and scrolls on small screens. The theme adds one small
style block to each page run.

## 8. Reversion

* **Not merging** leaves `main` and the public repository exactly as they are.
* **After a merge:** `git revert <merge commit>` restores the earlier look.
* **At run time:** `CROPSHIFT_THEME=classic` switches off the stylesheet, the
  artwork and the chart restyling. The dark palette in
  `.streamlit/config.toml` remains; restore its previous `[theme]` block (one
  line, `primaryColor = "#0072B2"`) for the original light look.

## 9. Before you merge

Recommended: **submit the competition entry from `main` first.** Merging this
theme before submission would also mean:

* the README screenshots and the demo deck show the earlier look;
* the SI text on `main` must change, because the app would then contain an
  AI-generated image (this branch already carries the corrected text);
* a new push to the public repository, and a recheck without login.
