"""Charts (phase A5).

Responsibility
    Build accessible Plotly figures from the engine's result objects. Every
    figure is drawn from values the A2 data layer and the A4 engines produced;
    nothing here calculates a new scientific quantity, smooths, interpolates or
    invents a value. A season without a value is left out and listed, never
    filled.

Design rules
    * Colour-blind-safe palette (Okabe and Ito). Dry, typical and wet use
      orange, grey and blue: rainfall classes, not verdicts. No red-for-bad,
      green-for-good colouring anywhere.
    * Units on every axis; the temperature statistic named on every line,
      because a daily mean, a daily minimum and a daily maximum are not
      interchangeable.
    * Titles say "past seasons" and subtitles carry the main caveat, so a
      chart copied out of the app still says what it is not.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.comparison_engine import IndicatorResult
from src.models import ScenarioCategory
from src.scenario_engine import ScenarioSet, SeasonClimate, WindowScenarios

CATEGORY_COLOURS = {
    ScenarioCategory.DRY: "#E69F00",  # orange
    ScenarioCategory.TYPICAL: "#8C8C8C",  # grey
    ScenarioCategory.WET: "#0072B2",  # blue
}
UNCLASSIFIED_COLOUR = "#CCCCCC"
TEMPERATURE_COLOURS = {"max": "#D55E00", "mean": "#4D4D4D", "min": "#56B4E9"}
BAND_COLOUR = "rgba(0, 158, 115, 0.12)"  # pale bluish green, a reference band only
BAND_LINE = "#009E73"
CHART_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _layout(figure: go.Figure, *, title: str, subtitle: str | None, x_title: str, y_title: str, height: int = 380) -> go.Figure:
    text = f"{title}<br><sup>{subtitle}</sup>" if subtitle else title
    figure.update_layout(
        title={"text": text, "x": 0, "xanchor": "left", "font": {"size": 16}},
        template="plotly_white",
        height=height,
        margin={"l": 50, "r": 20, "t": 80, "b": 50},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "right", "x": 1},
        hovermode="closest",
        font={"size": 13},
    )
    figure.update_xaxes(title_text=x_title)
    figure.update_yaxes(title_text=y_title, rangemode="tozero")
    return figure


def _category(season: SeasonClimate) -> str:
    return season.category.value if season.category else "not classified"


def seasonal_rainfall_figure(window: WindowScenarios, *, highlight: ScenarioCategory | None = None) -> go.Figure:
    """Rainfall total of every past season of one window, coloured by class."""
    figure = go.Figure()
    seasons = sorted(window.seasons, key=lambda item: item.season_year)
    for category in ScenarioCategory:
        members = [item for item in seasons if item.category is category]
        if not members:
            continue
        dimmed = highlight is not None and category is not highlight
        figure.add_bar(
            x=[item.season_year for item in members],
            y=[item.rainfall_total_mm for item in members],
            name=f"{category.value.title()} ({len(members)})",
            marker_color=CATEGORY_COLOURS[category],
            opacity=0.3 if dimmed else 1.0,
            customdata=[[item.label, item.rank, item.wet_days, item.longest_dry_spell_days] for item in members],
            hovertemplate=(
                "%{customdata[0]}<br>Rainfall %{y:.0f} mm<br>Rank %{customdata[1]} (1 = driest)"
                "<br>Wet days %{customdata[2]}<br>Longest dry spell %{customdata[3]} days<extra></extra>"
            ),
        )
    for value, label in ((window.dry_upper_mm, "dry up to"), (window.wet_lower_mm, "wet from")):
        if value is not None:
            figure.add_hline(
                y=value, line_dash="dot", line_color="#555555",
                annotation_text=f"{label} {value:.0f} mm", annotation_position="top left",
            )
    return _layout(
        figure,
        title=f"{window.window.name}: rainfall in each past season, {seasons[0].season_year}-{seasons[-1].season_year}" if seasons else window.window.name,
        subtitle="NASA POWER (MERRA-2 reanalysis), total over the window. Past seasons, not a forecast.",
        x_title="Season (year)",
        y_title="Rainfall over the window (mm)",
    )


def rainfall_distribution_figure(scenarios: ScenarioSet) -> go.Figure:
    """Spread of seasonal rainfall totals for each window, every season shown as a point."""
    figure = go.Figure()
    names = [window.window.name for window in scenarios.windows]
    for index, window in enumerate(scenarios.windows):
        classified = window.classified()
        figure.add_box(
            x=[index] * len(classified),
            y=[item.rainfall_total_mm for item in classified],
            name=window.window.name,
            boxpoints=False,
            line={"color": "#4D4D4D"},
            fillcolor="rgba(0,0,0,0)",
            hoverinfo="skip",
            showlegend=False,
        )
        for category in ScenarioCategory:
            members = [item for item in classified if item.category is category]
            # A fixed, deterministic horizontal spread so points do not overlap; no randomness.
            offsets = [((item.rank or 0) % 5 - 2) * 0.07 for item in members]
            figure.add_scatter(
                x=[index + offset for offset in offsets],
                y=[item.rainfall_total_mm for item in members],
                mode="markers",
                marker={"color": CATEGORY_COLOURS[category], "size": 9, "line": {"width": 0.5, "color": "#333333"}},
                name=category.value.title(),
                legendgroup=category.value,
                showlegend=index == 0,
                customdata=[[item.label] for item in members],
                hovertemplate="%{customdata[0]}<br>%{y:.0f} mm<extra></extra>",
            )
    figure.update_xaxes(tickvals=list(range(len(names))), ticktext=names)
    return _layout(
        figure,
        title="How much rain fell in past rainy seasons",
        subtitle="Each point is one past season. Box: the middle half of seasons; line: the median.",
        x_title="Season window",
        y_title="Rainfall over the window (mm)",
    )


def temperature_figure(window: WindowScenarios) -> go.Figure:
    """Season temperature statistics, each one labelled; they are not interchangeable."""
    seasons = sorted((item for item in window.seasons if item.mean_temperature_c is not None), key=lambda item: item.season_year)
    years = [item.season_year for item in seasons]
    figure = go.Figure()
    series = (
        ("Highest daily maximum", [item.highest_daily_max_c for item in seasons], TEMPERATURE_COLOURS["max"], "dot"),
        ("Mean of daily maximum", [item.mean_daily_max_c for item in seasons], TEMPERATURE_COLOURS["max"], "solid"),
        ("Mean of daily mean", [item.mean_temperature_c for item in seasons], TEMPERATURE_COLOURS["mean"], "solid"),
        ("Mean of daily minimum", [item.mean_daily_min_c for item in seasons], TEMPERATURE_COLOURS["min"], "solid"),
        ("Lowest daily minimum", [item.lowest_daily_min_c for item in seasons], TEMPERATURE_COLOURS["min"], "dot"),
    )
    for name, values, colour, dash in series:
        figure.add_scatter(
            x=years, y=values, name=name, mode="lines+markers",
            line={"color": colour, "dash": dash}, marker={"size": 5},
            hovertemplate=f"%{{x}}: {name.lower()} %{{y:.1f}} °C<extra></extra>",
        )
    figure.update_yaxes(rangemode="normal")
    return _layout(
        figure,
        title=f"{window.window.name}: air temperature in each past season",
        subtitle="NASA POWER air temperature at 2 m for a grid cell; each line is a different statistic.",
        x_title="Season (year)",
        y_title="Air temperature (°C)",
        height=400,
    )


def season_daily_figure(season: SeasonClimate) -> go.Figure:
    """The actual daily NASA values of one past season."""
    days = pd.date_range(season.start, season.end, freq="D")
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.45, 0.55])
    figure.add_bar(
        x=days, y=list(season.daily_precipitation_mm), name="Daily rainfall",
        marker_color=CATEGORY_COLOURS.get(season.category, UNCLASSIFIED_COLOUR) if season.category else UNCLASSIFIED_COLOUR,
        hovertemplate="%{x|%d %b %Y}: %{y:.1f} mm<extra></extra>", row=1, col=1,
    )
    for name, values, colour in (
        ("Daily maximum", season.daily_max_temperature_c, TEMPERATURE_COLOURS["max"]),
        ("Daily mean", season.daily_mean_temperature_c, TEMPERATURE_COLOURS["mean"]),
        ("Daily minimum", season.daily_min_temperature_c, TEMPERATURE_COLOURS["min"]),
    ):
        figure.add_scatter(
            x=days, y=list(values), name=name, mode="lines", line={"color": colour},
            hovertemplate=f"%{{x|%d %b %Y}}: {name.lower()} %{{y:.1f}} °C<extra></extra>", row=2, col=1,
        )
    figure.update_yaxes(title_text="Rainfall (mm/day)", row=1, col=1, rangemode="tozero")
    figure.update_yaxes(title_text="Air temperature (°C)", row=2, col=1)
    figure.update_xaxes(title_text="Date (UTC days)", row=2, col=1)
    category = f", {season.category.value}" if season.category else ""
    total = f"{season.rainfall_total_mm:.0f} mm in total" if season.rainfall_total_mm is not None else "total not available"
    figure.update_layout(
        title={"text": f"{season.label}{category}: daily NASA values<br><sup>{total}; values as delivered by NASA POWER, not smoothed.</sup>", "x": 0},
        template="plotly_white", height=480, margin={"l": 50, "r": 20, "t": 80, "b": 50},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "right", "x": 1}, font={"size": 13},
    )
    return figure


def monthly_rainfall_figure(climatology: pd.DataFrame, windows: Sequence[tuple[int, int]]) -> go.Figure:
    """Average monthly rainfall total across the record, with the season windows shaded."""
    rows = climatology[climatology["variable"] == "precipitation"].sort_values("month")
    figure = go.Figure()
    figure.add_bar(
        x=[calendar.month_abbr[int(month)] for month in rows["month"]],
        y=rows["mean_value"],
        marker_color="#0072B2",
        customdata=list(zip(rows["lowest"], rows["highest"], rows["years_used"])),
        hovertemplate="%{x}: mean %{y:.0f} mm (lowest %{customdata[0]:.0f}, highest %{customdata[1]:.0f}, %{customdata[2]} years)<extra></extra>",
        name="Mean monthly total",
    )
    for start, end in windows:
        figure.add_vrect(
            x0=calendar.month_abbr[start], x1=calendar.month_abbr[end], fillcolor="#E69F00", opacity=0.12, line_width=0,
        )
    return _layout(
        figure,
        title="The two rainy seasons in the NASA record",
        subtitle="Mean monthly rainfall total, 2001-2025. Shaded: the FAO GIEWS season windows used for analysis.",
        x_title="Month",
        y_title="Mean monthly rainfall (mm)",
        height=340,
    )


def water_use_figure(result: IndicatorResult, crop_name: str, window_name: str) -> go.Figure:
    """Past season rainfall beside a crop's indicative water-use range. Not a water balance."""
    findings = sorted(result.season_findings, key=lambda item: item.year)
    values = {item.label: item.value for item in result.values}
    low = values.get("Indicative seasonal water use, low end")
    high = values.get("Indicative seasonal water use, high end")
    figure = go.Figure()
    for category in ScenarioCategory:
        members = [item for item in findings if item.category is category]
        if members:
            figure.add_bar(
                x=[item.year for item in members], y=[item.value for item in members],
                name=f"{category.value.title()} seasons", marker_color=CATEGORY_COLOURS[category],
                customdata=[item.position for item in members],
                hovertemplate="%{x}: %{y:.0f} mm, %{customdata} the indicative range<extra></extra>",
            )
    if low is not None and high is not None:
        figure.add_hrect(y0=low, y1=high, fillcolor=BAND_COLOUR, line_width=1, line_color=BAND_LINE)
        figure.add_annotation(
            xref="paper", x=0, y=high, yanchor="bottom", xanchor="left", showarrow=False,
            text=f"Indicative {crop_name.lower()} water use, {low:.0f}-{high:.0f} mm (FAO)", font={"color": "#006B4F"},
        )
    return _layout(
        figure,
        title=f"{window_name}: past season rainfall and indicative {crop_name.lower()} water use",
        subtitle="Rain within the window only. Not a water balance: stored soil water and rain outside the window are not counted.",
        x_title="Season (year)",
        y_title="Millimetres",
        height=380,
    )


def annual_rainfall_figure(scenarios: ScenarioSet) -> go.Figure:
    years = [item for item in scenarios.annual_rainfall if item.complete]
    figure = go.Figure()
    figure.add_bar(
        x=[item.year for item in years], y=[item.total_mm for item in years], marker_color="#56B4E9", name="Annual total",
        hovertemplate="%{x}: %{y:.0f} mm<extra></extra>",
    )
    return _layout(
        figure,
        title="Annual rainfall, complete calendar years",
        subtitle="NASA POWER daily rainfall summed by calendar year. Past years only.",
        x_title="Year",
        y_title="Rainfall (mm per year)",
        height=320,
    )
