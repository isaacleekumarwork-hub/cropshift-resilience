"""A9.UI.1: the Starry Night theme is presentation only, accessible, offline and honest.

The theme must not change a single number, label or qualification; its text
must meet WCAG AA contrast over the brightest part of the artwork; it must load
nothing from outside the app; its AI-generated artwork must be watermarked and
disclosed; and it must be possible to switch it off.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib

import pytest
from streamlit.testing.v1 import AppTest

from src import ui_theme
from src import visualizations as viz
from src.config import PROJECT_ROOT
from src.scenario_engine import build_scenarios
from src.season_config import pilot_configuration

APP_FILE = str(PROJECT_ROOT / "app.py")
BRIGHTEST_ARTWORK = "#FFFFFF"  # the painting has near-white strokes, so assume pure white beneath a panel


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(colour: str) -> tuple[float, float, float]:
    colour = colour.lstrip("#")
    return tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (_channel(round(v)) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground: str | tuple, background: str | tuple) -> float:
    fg = _rgb(foreground) if isinstance(foreground, str) else foreground
    bg = _rgb(background) if isinstance(background, str) else background
    high, low = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def over(colour: str, alpha: float, underneath: str) -> tuple[float, float, float]:
    top, bottom = _rgb(colour), _rgb(underneath)
    return tuple(alpha * t + (1 - alpha) * b for t, b in zip(top, bottom))  # type: ignore[return-value]


@pytest.fixture(scope="module")
def theme_config() -> dict:
    return tomllib.loads((PROJECT_ROOT / ".streamlit" / "config.toml").read_text())


@pytest.fixture(scope="module")
def window(pilot_dataset):
    return build_scenarios(pilot_dataset, pilot_configuration().windows).window("long-rains")


# --- Safe, local, CSS only -------------------------------------------------------------------------


def test_stylesheet_is_css_only_and_loads_nothing_from_outside():
    css = ui_theme.theme_css(ui_theme.asset_urls())
    lowered = css.lower()
    for forbidden in ("<script", "javascript:", "@import", "http://", "https://", "expression("):
        assert forbidden not in lowered
    assert css.strip().startswith("<style>") and css.strip().endswith("</style>")
    urls = re.findall(r"url\('([^']+)'\)", css)
    assert urls and all(url.startswith("app/static/theme/") for url in urls)


def test_every_artwork_file_is_local_small_and_script_free():
    for name in ui_theme.ASSETS.values():
        path = ui_theme.ASSET_DIR / name
        assert path.stat().st_size < 400_000, name
        if name.endswith(".svg"):
            text = path.read_text(encoding="utf-8")
            assert "<script" not in text and "javascript:" not in text and "foreignObject" not in text
            assert set(re.findall(r"https?://[^\s\"')]+", text)) <= {"http://www.w3.org/2000/svg"}
        else:
            assert name.endswith(".jpg") and path.read_bytes()[:3] == b"\xff\xd8\xff", name  # a plain JPEG


def test_the_painting_fits_the_screen_without_stretching():
    from PIL import Image

    wide = Image.open(ui_theme.ASSET_DIR / ui_theme.ASSETS["background"])
    tall = Image.open(ui_theme.ASSET_DIR / ui_theme.ASSETS["background_tall"])
    assert wide.width > wide.height and tall.height > tall.width
    css = ui_theme.theme_css(ui_theme.asset_urls())
    assert "@media (max-aspect-ratio: 1/1)" in css and ui_theme.ASSETS["background_tall"] in css
    # The banner strip is its own layer, cropped to fit ("cover"), never forced to a fixed width and height.
    banner_rule = css[css.index('[data-testid="stMainBlockContainer"]::before'):]
    assert "/ cover" in banner_rule.split("}")[0]


def test_numbers_wrap_instead_of_being_cut_short():
    css = ui_theme.theme_css(ui_theme.asset_urls())
    rule = css[css.index('[data-testid="stMetricValue"] div'):].split("}")[0]
    assert "text-overflow: clip" in rule and "white-space: normal" in rule


def test_artwork_is_regenerated_exactly_by_its_script():
    spec = importlib.util.spec_from_file_location("make_theme_artwork", PROJECT_ROOT / "scripts" / "make_theme_artwork.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, painter in module.ARTWORK.items():
        assert painter() == (ui_theme.ASSET_DIR / name).read_text(encoding="utf-8"), name


def test_static_serving_dark_theme_and_offline_fonts(theme_config):
    assert theme_config["server"]["enableStaticServing"] is True
    assert theme_config["client"]["showErrorDetails"] == "none"
    theme = theme_config["theme"]
    p = ui_theme.PALETTE
    assert theme["base"] == "dark"
    assert (theme["backgroundColor"], theme["secondaryBackgroundColor"], theme["textColor"], theme["primaryColor"]) == (
        p["midnight"], p["card"], p["moonlight"], p["gold"]
    )
    assert theme["font"] == "sans-serif"  # Streamlit's bundled font: nothing to download
    assert theme["headingFont"].startswith("Georgia")


def test_missing_artwork_falls_back_to_a_plain_night_sky(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_theme, "ASSET_DIR", tmp_path)
    urls = ui_theme.asset_urls()
    assert all(url is None for url in urls.values())
    css = ui_theme.theme_css(urls)
    assert "url(" not in css
    assert "radial-gradient" in css


# --- Honest about AI-generated artwork ---------------------------------------------------------------


def test_artwork_is_labelled_as_ai_generated_on_every_page():
    credit = ui_theme.ARTWORK_CREDIT
    assert "AI-generated image (SI)" in credit and "by the participant" in credit
    assert "imaginary landscape" in credit and "not the pilot site" in credit
    css = ui_theme.theme_css(ui_theme.asset_urls())
    assert credit in css  # shown in the header strip of every page
    provenance = (PROJECT_ROOT / "docs" / "provenance.md").read_text(encoding="utf-8")
    assert "wheatfield_night" not in provenance or "AI-generated" in provenance
    assert "app's page background" in provenance and "AI image-generation tool" in provenance


# --- Readable and accessible -------------------------------------------------------------------------


def test_text_meets_wcag_aa_over_the_brightest_artwork(theme_config):
    p = ui_theme.PALETTE
    theme = theme_config["theme"]
    backgrounds = {
        "panel over a star": over(p["midnight"], ui_theme.PANEL_OPACITY, BRIGHTEST_ARTWORK),
        "card over a star": over(p["card"], ui_theme.CARD_OPACITY, BRIGHTEST_ARTWORK),
        "midnight": p["midnight"],
        "card": p["card"],
    }
    texts = {
        "body": p["moonlight"],
        "secondary": p["secondary_text"],
        "gold accents": p["gold"],
        "Supported": theme["blueTextColor"],
        "Conditional": theme["orangeTextColor"],
        "Unavailable": theme["grayTextColor"],
    }
    for bg_name, background in backgrounds.items():
        for text_name, colour in texts.items():
            assert contrast(colour, background) >= 4.5, (text_name, bg_name, round(contrast(colour, background), 2))
    assert contrast(p["midnight"], p["gold"]) >= 4.5  # primary button label


def test_chart_text_and_marks_are_readable_on_the_dark_frame():
    p = ui_theme.PALETTE
    for colour in (p["moonlight"], p["secondary_text"], ui_theme.BAND_LABEL):
        assert contrast(colour, ui_theme.CHART_PLOT) >= 4.5
        assert contrast(colour, ui_theme.CHART_PAPER) >= 4.5
    assert contrast(ui_theme.REFERENCE_LINE, ui_theme.CHART_PLOT) >= 3
    assert contrast(ui_theme.BAR_OUTLINE["color"], ui_theme.CHART_PLOT) >= 3


def test_focus_is_visible_and_motion_is_respected():
    css = ui_theme.theme_css(ui_theme.asset_urls())
    assert ":focus-visible" in css and f"outline: 3px solid {ui_theme.PALETTE['gold']}" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@keyframes" not in css  # no continuous animation at all


# --- Presentation only -------------------------------------------------------------------------------


def _same_data(original, themed):
    assert len(original.data) == len(themed.data)
    for before, after in zip(original.data, themed.data):
        assert before.type == after.type and before.name == after.name
        assert tuple(before.x if before.x is not None else ()) == tuple(after.x if after.x is not None else ())
        assert tuple(before.y if before.y is not None else ()) == tuple(after.y if after.y is not None else ())
        assert before.hovertemplate == after.hovertemplate
        if before.type == "bar":
            assert before.marker.color == after.marker.color


def test_charts_keep_their_data_units_and_category_colours(window):
    original = viz.seasonal_rainfall_figure(window)
    themed = ui_theme.theme_figure(original)
    _same_data(original, themed)
    assert len(original.layout.shapes) == len(themed.layout.shapes)
    assert [a.text for a in original.layout.annotations] == [a.text for a in themed.layout.annotations]
    assert themed.layout.yaxis.title.text == original.layout.yaxis.title.text
    for trace in themed.data:
        if trace.type == "bar":
            assert trace.marker.line.color == ui_theme.BAR_OUTLINE["color"]  # edges stay visible on navy
    # The original figure is not modified.
    assert all(t.marker.line.color == viz.OUTLINE["color"] for t in original.data if t.type == "bar")
    assert themed.layout.paper_bgcolor == ui_theme.CHART_PAPER


def test_dark_temperature_line_is_recoloured_but_keeps_its_values(window):
    original = viz.temperature_figure(window)
    themed = ui_theme.theme_figure(original)
    _same_data(original, themed)
    mean = [t for t in themed.data if t.name == "Mean of daily mean"][0]
    assert mean.line.color == ui_theme.PALETTE["moonlight"]


def test_card_keys_become_css_classes():
    assert ui_theme.card_key(7) == "painted-card-7"
    assert '[class*="st-key-painted-card"]' in ui_theme.theme_css(ui_theme.asset_urls())


# --- Can be switched off -------------------------------------------------------------------------


def test_theme_can_be_switched_off(monkeypatch, window):
    monkeypatch.setenv("CROPSHIFT_THEME", "classic")
    assert ui_theme.theme_enabled() is False
    assert ui_theme.apply_starry_night_theme() is False
    figure = viz.seasonal_rainfall_figure(window)
    assert ui_theme.theme_figure(figure) is figure


@pytest.mark.parametrize("mode", ["starry-night", "classic"])
def test_app_runs_with_and_without_the_theme(monkeypatch, tmp_path, mode):
    monkeypatch.setenv("OFFLINE_DEMO_MODE", "true")
    monkeypatch.setenv("NASA_CACHE_DIRECTORY", str(tmp_path / "cache"))
    monkeypatch.setenv("CROPSHIFT_THEME", mode)
    app = AppTest.from_file(APP_FILE, default_timeout=120).run()
    assert not app.exception
    markdown = " ".join(item.value for item in app.markdown)
    captions = " ".join(item.value for item in app.caption)
    if mode == "classic":
        assert ui_theme.TAGLINE not in markdown
        assert ui_theme.ARTWORK_CREDIT not in captions
    else:
        assert ui_theme.TAGLINE in markdown
        assert ui_theme.ARTWORK_CREDIT in captions
    assert app.title[0].value == "CropShift RESILIENCE"
    assert len(app.get("plotly_chart")) >= 5
