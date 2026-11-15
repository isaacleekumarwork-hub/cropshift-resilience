"""The "Starry Night" visual theme for the Streamlit interface (patch A9.UI.1).

Presentation only. Nothing here reads or changes NASA data, the knowledge base,
the evidence gate or any comparison result. The theme has three parts:

* colours, fonts and borders in ``.streamlit/config.toml`` (Streamlit's own
  theming), so widgets, tables and status words follow the dark palette;
* :func:`apply_starry_night_theme`, which adds one stylesheet: the
  participant's painting of a wheat field under a swirling night sky as the
  page background (wide or tall to suit the screen) under a canvas grain, a
  strip of the same painting as a banner, brushed frames, gold brushstroke
  underlines, painted dividers, hand-drawn edges for cards, expanders,
  buttons and chart frames, metric values that wrap instead of being cut
  short, visible keyboard focus and reduced-motion rules;
* :func:`theme_figure`, which restyles a finished Plotly figure for the dark
  panels without touching its data, units or category colours. Data marks
  stay exact; only the frame around a chart is painterly.

The painting (``static/theme/wheatfield_night_*.jpg``) is an AI-generated
image the participant created and supplied, in the style of Vincent van Gogh,
so every page carries a credit saying so. The landscape is imaginary, not the
pilot site, and shows no people. The brushstroke ornaments are SVG drawn by
``scripts/make_theme_artwork.py``. Everything is served by Streamlit's local
static file server (``server.enableStaticServing``): no external address, so
offline mode is unaffected. Text always sits on solid painted panels; the
textures stay outside them. If an asset is missing, a plain night-sky
gradient is used.

Set ``CROPSHIFT_THEME=classic`` to switch the stylesheet, the artwork and the
chart restyling off.

AI assistance: this module was drafted with Claude Code (Anthropic) under the
participant's direction during the 2026 NASA Space Apps Challenge. See
docs/provenance.md.
"""

from __future__ import annotations

import os
from pathlib import Path

import plotly.graph_objects as go

PALETTE = {
    "midnight": "#101B38",
    "cobalt": "#24477A",
    "swirl": "#527DA6",
    "gold": "#F3C94E",
    "moonlight": "#F4E8C8",
    "secondary_text": "#C8D6E9",
    "card": "#17294B",
    "card_border": "#54759B",
}

ASSET_DIR = Path(__file__).resolve().parent.parent / "static" / "theme"
ASSET_URL = "app/static/theme/"  # Streamlit serves ./static at /app/static/
ASSETS = {
    "background": "wheatfield_night_wide.jpg",  # the participant's AI-generated painting, wide version
    "background_tall": "wheatfield_night_tall.jpg",  # the same painting, tall version, for portrait screens
    "banner": "wheatfield_night_banner.jpg",  # a strip cut from the wide version
    "frame": "brush_frame.svg",
    "underline": "brush_underline.svg",
    "divider": "brush_divider.svg",
    "edge": "brush_edge.svg",
    "grain": "canvas_grain.svg",
}
ARTWORK_CREDIT = "Background: AI-generated image (SI) by the participant, in the style of Van Gogh; imaginary landscape, not the pilot site"
TAGLINE = "Finding clarity in changing seasons."

# Opacity of the painted panels that carry text. Checked in tests: ivory text
# stays above WCAG AA even over the brightest part of the artwork.
PANEL_OPACITY = 0.86
CARD_OPACITY = 0.94

# Chart colours on the dark panels. Data colours (dry, typical, wet and the
# temperature series) are kept; only colours that would vanish on navy change.
CHART_PAPER = "#17294B"
CHART_PLOT = "#13223F"
CHART_GRID = "rgba(200, 214, 233, 0.16)"
CHART_AXIS = "#54759B"
BAR_OUTLINE = {"color": "#F4E8C8", "width": 1}  # keeps every bar's edge at 3:1 or more on navy
REFERENCE_LINE = "#C8D6E9"  # dotted class boundaries and similar guides
BAND_LABEL = "#8FE3C5"  # the indicative water-use band's label, light bluish green
_DARK_LINE_COLOURS = {"#555555", "#4D4D4D", "#333333", "#4d4d4d"}

# Hand-drawn edges: unequal corner radii read as a brush-cut outline.
_PAINTED_CORNERS = "26px 10px 30px 12px / 12px 28px 10px 24px"
_SMALL_CORNERS = "16px 7px 18px 8px / 8px 17px 7px 15px"


def theme_enabled() -> bool:
    """False when the participant has switched the theme off."""
    return os.environ.get("CROPSHIFT_THEME", "starry-night").strip().lower() != "classic"


def asset_urls() -> dict[str, str | None]:
    """The URL of every artwork file that exists, or None for a missing one."""
    return {key: (ASSET_URL + name if (ASSET_DIR / name).is_file() else None) for key, name in ASSETS.items()}


def _layers(*pairs: tuple[str | None, str]) -> tuple[str, str]:
    """CSS background-image and background-size lists, skipping missing images."""
    images, sizes = [], []
    for image, size in pairs:
        if image is None:
            continue
        images.append(image)
        sizes.append(size)
    return ", ".join(images), ", ".join(sizes)


def theme_css(urls: dict[str, str | None] | None = None) -> str:
    """The stylesheet: CSS only, no script, no external address."""
    p = PALETTE
    u = urls if urls is not None else {key: None for key in ASSETS}

    def url(key: str) -> str | None:
        return f"url('{u[key]}')" if u.get(key) else None

    sky = f"radial-gradient(ellipse at 30% 20%, {p['cobalt']} 0%, {p['midnight']} 70%)"
    page_images, page_sizes = _layers(
        (url("grain"), "180px 180px"),
        ("linear-gradient(180deg, rgba(16, 27, 56, 0.28) 0%, rgba(16, 27, 56, 0.42) 55%, rgba(16, 27, 56, 0.58) 100%)", "cover"),
        (url("background") or sky, "cover"),
    )
    side_images, side_sizes = _layers(
        (url("edge"), "14px 100%"),
        (f"linear-gradient(rgba(13, 22, 49, {PANEL_OPACITY}), rgba(13, 22, 49, {PANEL_OPACITY}))", "auto"),
        (url("background_tall") or url("background"), "cover"),
    )
    tall_images, tall_sizes = _layers(
        (url("grain"), "180px 180px"),
        ("linear-gradient(180deg, rgba(16, 27, 56, 0.28) 0%, rgba(16, 27, 56, 0.42) 55%, rgba(16, 27, 56, 0.58) 100%)", "cover"),
        (url("background_tall") or url("background") or sky, "cover"),
    )
    underline = url("underline") or "none"
    divider = url("divider") or f"linear-gradient({p['swirl']}, {p['swirl']})"
    banner = url("banner") or "none"
    frame = (
        f"border: 22px solid transparent; border-image: {url('frame')} 30 round;"
        if u.get("frame")
        else f"border: 2px solid {p['card_border']}; border-radius: 18px;"
    )
    return f"""
<style>
/* CropShift RESILIENCE: Starry Night theme, Post-Impressionist edition (presentation only). */
[data-testid="stApp"] {{
  background-color: {p['midnight']};
  background-image: {page_images};
  background-size: {page_sizes};
  background-position: 0 0, center, center bottom;
  background-repeat: repeat, no-repeat, no-repeat;
  background-attachment: fixed;
}}
[data-testid="stHeader"] {{ background: rgba(13, 22, 49, 0.55); }}

/* The main canvas: a solid painted panel in a brushed frame, a painted strip on top. */
[data-testid="stMainBlockContainer"] {{
  position: relative;
  background-color: rgba(16, 27, 56, {PANEL_OPACITY});
  background-clip: padding-box;
  {frame}
  box-shadow: 0 18px 48px rgba(5, 10, 25, 0.55);
  margin-top: 1rem;
  margin-bottom: 2rem;
  padding-top: 176px;
  padding-left: 2.5rem;
  padding-right: 2.5rem;
}}

/* The painted strip across the top of the canvas: cropped to fit, never stretched. */
[data-testid="stMainBlockContainer"]::before {{
  content: ""; position: absolute; left: 0; right: 0; top: 0; height: 150px;
  background: {banner} center 62% / cover no-repeat;
  pointer-events: none;
}}

/* Sidebar: the night painting seen through a dark glaze, with a brushed edge. */
[data-testid="stSidebar"] {{
  background-color: #0D1631 !important;
  background-image: {side_images};
  background-size: {side_sizes};
  background-position: right top, 0 0, 30% center;
  background-repeat: no-repeat;
}}
[data-testid="stSidebar"] > div:first-child {{ background: transparent; }}

/* Headings: Georgia, ivory, with a gold brushstroke beneath section titles. */
[data-testid="stMain"] h1 {{ color: {p['moonlight']}; letter-spacing: 0.01em; }}
[data-testid="stMain"] h1::before {{
  content: "\\2726" / "";
  color: {p['gold']};
  margin-right: 0.45em;
  text-shadow: 0 0 14px rgba(243, 201, 78, 0.55);
}}
[data-testid="stMain"] h2, [data-testid="stMain"] h3, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
  color: {p['moonlight']};
  background: {underline} left bottom / 230px 12px no-repeat;
  padding-bottom: 14px;
}}
[data-testid="stMain"] h4 {{ color: {p['moonlight']}; }}
.cropshift-tagline {{
  font-family: Georgia, 'Times New Roman', serif; font-style: italic; font-size: 1.3rem;
  color: {p['gold']}; margin: -0.6rem 0 0.4rem 0;
}}
[data-testid="stCaptionContainer"] {{ color: {p['secondary_text']}; }}
[data-testid="stMetricValue"], [data-testid="stMarkdownContainer"] td {{ font-variant-numeric: tabular-nums; }}
/* Never cut a number or its label short: wrap instead of "20…". */
[data-testid="stMetricValue"] div, [data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] div {{
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}}
[data-testid="stMetricValue"] {{ font-size: clamp(1.6rem, 2.6vw, 2.25rem); }}

/* Navigation: the selected tab is underlined with a gold brushstroke. */
[data-testid="stTab"] {{ padding-bottom: 6px; }}
[data-testid="stTab"][aria-selected="true"] {{ background: {underline} center bottom / 92% 9px no-repeat; }}
[data-testid="stTab"][aria-selected="true"] p {{ color: {p['gold']}; font-weight: 600; }}

/* Painted dividers. */
[data-testid="stMain"] hr, [data-testid="stSidebar"] hr {{
  border: none !important; height: 14px; margin: 1.1rem 0;
  background: {divider} center / 100% 14px no-repeat;
}}

/* Cards: solid painted panels with brush-cut edges and a paint-layer shadow. */
[class*="st-key-painted-card"] {{
  background: rgba(23, 41, 75, {CARD_OPACITY}) !important;
  border: 2px solid {p['swirl']} !important;
  border-radius: {_PAINTED_CORNERS} !important;
  box-shadow: 3px 5px 0 rgba(6, 11, 26, 0.6), inset 0 0 0 1px rgba(243, 201, 78, 0.12);
}}

/* Expandable explanations. */
[data-testid="stExpander"] details {{
  background: rgba(16, 27, 56, 0.6);
  border: 1.5px solid #3E6E9E;
  border-radius: {_SMALL_CORNERS};
}}
[data-testid="stExpander"] summary:hover p, [data-testid="stExpander"] details[open] > summary p {{ color: {p['gold']}; }}

/* Alerts keep Streamlit's own colours and icons; only their outline is painterly. */
[data-testid="stAlertContainer"] {{ border-radius: {_SMALL_CORNERS}; }}

/* Buttons. */
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
  background: {p['cobalt']} !important; color: {p['moonlight']} !important;
  border: 2px solid {p['swirl']} !important; border-radius: {_SMALL_CORNERS} !important;
  box-shadow: 2px 3px 0 rgba(6, 11, 26, 0.55);
}}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondaryFormSubmit"]:hover {{ border-color: {p['gold']} !important; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: {p['gold']} !important; color: {p['midnight']} !important;
  border: 2px solid #E2B13C !important; border-radius: {_SMALL_CORNERS} !important;
  box-shadow: 2px 3px 0 #8C6A24;
}}
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p {{ color: {p['midnight']} !important; }}

/* Charts: exact Plotly marks inside a painted frame. */
[data-testid="stPlotlyChart"] {{
  padding: 10px; background: {CHART_PAPER};
  border: 2px solid #3E6E9E; border-radius: {_PAINTED_CORNERS};
  box-shadow: 3px 5px 0 rgba(6, 11, 26, 0.6);
  overflow: hidden;
}}

/* Keyboard focus is always visible. */
:focus-visible {{ outline: 3px solid {p['gold']} !important; outline-offset: 2px !important; }}

/* The AI-artwork credit, in the header strip where it covers no content. */
[data-testid="stApp"]::after {{
  content: "{ARTWORK_CREDIT}";
  position: fixed; top: 7px; left: 50%; transform: translateX(-50%); max-width: 62vw; z-index: 1000001;
  pointer-events: none; text-align: center;
  font: 11px/1.35 Georgia, 'Times New Roman', serif; color: {p['moonlight']};
  background: rgba(13, 22, 49, 0.9); padding: 2px 10px; border-radius: 6px; border: 1px solid rgba(243, 201, 78, 0.35);
}}

@media (max-aspect-ratio: 1/1) {{
  [data-testid="stApp"] {{ background-image: {tall_images}; background-size: {tall_sizes}; }}
}}
@media (max-width: 768px) {{
  [data-testid="stApp"] {{ background-attachment: scroll; }}
  [data-testid="stMainBlockContainer"] {{
    border-width: 12px; margin-top: 3rem; padding-top: 110px;
    padding-left: 0.9rem; padding-right: 0.9rem;
  }}
  [data-testid="stMainBlockContainer"]::before {{ height: 90px; }}
  [data-testid="stApp"]::after {{ font-size: 9.5px; top: 4px; left: 48px; transform: none; max-width: calc(100vw - 170px); text-align: left; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; scroll-behavior: auto !important; }}
}}
</style>
"""


def apply_starry_night_theme() -> bool:
    """Add the theme stylesheet to the page. Returns False if switched off."""
    if not theme_enabled():
        return False
    import streamlit as st

    # A style-only st.html block is applied to the page without taking space.
    st.html(theme_css(asset_urls()))
    return True


def tagline_html() -> str:
    """The hero line under the title (static text, no user input)."""
    return f'<p class="cropshift-tagline">{TAGLINE}</p>'


def card_key(index: int) -> str:
    """Key for a painted card; Streamlit turns it into the CSS class st-key-<key>."""
    return f"painted-card-{index}"


def theme_figure(figure: go.Figure) -> go.Figure:
    """A restyled copy of ``figure`` for the dark panels.

    Only colours of the paper, axes, text, guides and bar edges change. Every
    trace keeps its data, name, units, hover text and fill colour, so the
    dry, typical and wet colours mean what they meant before.
    """
    if not theme_enabled():
        return figure
    themed = go.Figure(figure)
    p = PALETTE
    themed.update_layout(
        paper_bgcolor=CHART_PAPER,
        plot_bgcolor=CHART_PLOT,
        font={"color": p["moonlight"]},
        title_font={"color": p["moonlight"], "family": "Georgia, 'Times New Roman', serif"},
        legend={"font": {"color": p["moonlight"]}, "bgcolor": "rgba(0,0,0,0)"},
        hoverlabel={"bgcolor": p["midnight"], "bordercolor": p["gold"], "font": {"color": p["moonlight"]}},
    )
    axis = {
        "gridcolor": CHART_GRID,
        "linecolor": CHART_AXIS,
        "zerolinecolor": CHART_AXIS,
        "tickfont": {"color": p["secondary_text"]},
        "title_font": {"color": p["secondary_text"]},
    }
    themed.update_xaxes(**axis)
    themed.update_yaxes(**axis)
    for trace in themed.data:
        if trace.type == "bar":
            trace.marker.line = BAR_OUTLINE
        elif trace.type == "scatter":
            if trace.line and trace.line.color in _DARK_LINE_COLOURS:
                trace.line.color = p["moonlight"]
            if trace.marker and trace.marker.line and trace.marker.line.color in _DARK_LINE_COLOURS:
                trace.marker.line.color = p["moonlight"]
    for shape in themed.layout.shapes:
        if shape.line and shape.line.color in _DARK_LINE_COLOURS:
            shape.line.color = REFERENCE_LINE
    for note in themed.layout.annotations:
        colour = note.font.color if note.font else None
        if colour and colour.lower() == "#006b4f":
            note.font.color = BAND_LABEL
        elif note.text and not colour:
            note.font = {"color": p["moonlight"]}
        elif colour in _DARK_LINE_COLOURS:
            note.font.color = p["moonlight"]
    return themed
