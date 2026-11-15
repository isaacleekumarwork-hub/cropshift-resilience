"""CropShift RESILIENCE — Streamlit application (phase A5).

Six sections, as tabs: Overview, Climate Explorer, Rotation Comparison, Soil &
Farm Inputs, Scientific Evidence, About & Methodology.

Every number on screen comes from the validated NASA dataset (A2), the cited
knowledge base (A3) or the A4 engine's ``ComparisonReport``. This file only
arranges and labels them: it calculates no indicator, scores nothing, ranks
nothing and recommends nothing. The engine never imports Streamlit.

Run from the repository root with the project's environment:

    .venv/bin/python -m streamlit run app.py

AI assistance: drafted with Claude Code (Anthropic) under the participant's
direction. See docs/provenance.md.
"""

from __future__ import annotations

import calendar
import hashlib
import logging
from datetime import date

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from src import CHALLENGE_NAME, CURRENT_PHASE, EVENT_NAME, MODULES, PHASES, PROJECT_NAME, __version__
from src.comparison_engine import (
    INDICATORS,
    ComparisonReport,
    ConstraintOutcome,
    IndicatorResult,
    IndicatorStatus,
    PrioritySelection,
    compare_strategies,
)
from src.config import PROJECT_ROOT, Settings, get_settings
from src.crop_knowledge import KnowledgeBase, KnowledgeBaseError, load_knowledge_base
from src.data_processing import monthly_climatology, monthly_summary, to_wide_frame
from src.data_service import load_pilot_dataset
from src.data_validation import EnvironmentalDataset, IssueSeverity
from src.evidence_audit import EvidenceGate, load_evidence_gate
from src.models import DEFAULT_DISCLAIMER, DataOrigin, PriorityDimension, ScenarioCategory
from src.nasa_client import NasaDataError
from src.report_service import comparison_result_json, report_json, summary_markdown
from src.scenario_engine import ScenarioSet, build_scenarios
from src.season_config import CANDIDATE_STRATEGIES, PilotConfiguration, pilot_configuration
from src.soil_inputs import SoilProfileInput
from src import ui_state as ui
from src import visualizations as viz

LOG = logging.getLogger("cropshift.app")

VARIABLE_LABELS = {
    "precipitation": "Rainfall",
    "air_temperature_mean": "Mean temperature",
    "air_temperature_max": "Daily maximum temperature",
    "air_temperature_min": "Daily minimum temperature",
    "solar_irradiance": "Sunshine energy",
    "relative_humidity": "Relative humidity",
}
KIND_LABELS = {
    "reanalysis": "NASA reanalysis (weather model constrained by observations)",
    "satellite_retrieval": "Satellite-based estimate",
}
ORIGIN_LABELS = {
    DataOrigin.NETWORK: "retrieved from the NASA service just now",
    DataOrigin.CACHE: "read from this computer's cache of an earlier NASA request",
    DataOrigin.BUNDLED: "read from the real NASA response bundled with the project",
}
STATUS_LABELS = {
    IndicatorStatus.SUPPORTED: ":blue[**Supported**]",
    IndicatorStatus.CONDITIONAL: ":orange[**Conditional**: read the conditions]",
    IndicatorStatus.UNAVAILABLE: ":gray[**Unavailable**: evidence or input missing]",
}
OUTCOME_LABELS = {
    ConstraintOutcome.TRIGGERED: "Applies",
    ConstraintOutcome.NOT_TRIGGERED: "Did not occur",
    ConstraintOutcome.NOT_EVALUATED: "Not evaluated (information missing)",
    ConstraintOutcome.NOT_APPLIED: "Not applied (no supporting evidence)",
}
GROUPS = (
    ("Environmental exposure in past seasons", (
        "rainfall_vs_crop_water_use", "temperature_vs_documented_range", "frost_days",
        "growing_period_vs_window", "annual_rainfall_vs_documented_range",
    )),
    ("Agronomic characteristics of the sequence", ("crop_family_diversity", "legume_in_sequence", "crop_repetition")),
    ("Soil compatibility", ("soil_ph_vs_documented_range", "root_zone_available_water", "readily_available_water")),
)
DEFINITIONS = {item.indicator_id: item for item in INDICATORS}
PREVIEW_ROWS = 5
TAB_NAMES = ("Overview", "Climate Explorer", "Rotation Comparison", "Soil & Farm Inputs", "Scientific Evidence", "About & Methodology")


# --------------------------------------------------------------------------- #
# Cached loading. Immutable inputs only; keys name what each result depends on.
# --------------------------------------------------------------------------- #


@st.cache_resource(show_spinner="Loading NASA data for the pilot site…")
def _pilot_dataset(_settings: Settings, fingerprint: tuple[object, ...]) -> EnvironmentalDataset:
    return load_pilot_dataset(settings=_settings)


def _source_fingerprint() -> str:
    """A fingerprint of the code and knowledge files that every cached result depends on.

    Part of every cache key below, so a result made by older code or older knowledge
    files is never served after they change (for example after a hot reload).
    """
    digest = hashlib.sha256()
    paths = sorted([*(PROJECT_ROOT / "src").glob("*.py"), *(PROJECT_ROOT / "data" / "knowledge").glob("*.json")])
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


@st.cache_resource(show_spinner="Loading the knowledge base and evidence audit…")
def _knowledge(source_key: str) -> tuple[KnowledgeBase, EvidenceGate]:
    kb = load_knowledge_base()
    return kb, load_evidence_gate(kb)


@st.cache_resource(show_spinner="Ranking past seasons…")
def _scenarios(_dataset: EnvironmentalDataset, dataset_key: tuple[str, str, str]) -> ScenarioSet:
    return build_scenarios(_dataset, pilot_configuration().windows)


@st.cache_resource(show_spinner=False)
def _climatology(_dataset: EnvironmentalDataset, dataset_key: tuple[str, str, str]) -> pd.DataFrame:
    return monthly_climatology(monthly_summary(_dataset))


@st.cache_resource(show_spinner="Comparing rotations…", max_entries=32)
def _report(
    _scenarios: ScenarioSet, _kb: KnowledgeBase, _gate: EvidenceGate,
    key: tuple[str, str, str, str, str, tuple[str, ...]],
) -> ComparisonReport:
    """One report per code version, dataset, knowledge base, audit, soil input and priority order."""
    _, _, _, _, soil_json, priorities = key
    soil = None if soil_json == "no-soil" else SoilProfileInput.model_validate_json(soil_json)
    selection = PrioritySelection(dimensions=tuple(PriorityDimension(item) for item in priorities)) if priorities else None
    return compare_strategies(
        CANDIDATE_STRATEGIES, scenarios=_scenarios, kb=_kb, gate=_gate, config=pilot_configuration(),
        soil=soil, priorities=selection,
    )


def _guarded(section: str, render, *args) -> None:
    """Render one section; an unexpected problem is reported without a stack trace."""
    try:
        render(*args)
    except Exception:  # noqa: BLE001 - the public page must never show internals
        LOG.exception("section %s failed", section)
        st.error(
            f"The {section} section could not be shown because of an unexpected problem. "
            "The other sections still work. Details were written to the server log."
        )


# --------------------------------------------------------------------------- #
# Small display helpers
# --------------------------------------------------------------------------- #


def _label(variable: str, unit: str) -> str:
    return f"{VARIABLE_LABELS.get(variable, variable)} ({unit})"


def _chart(figure) -> None:
    st.plotly_chart(figure, width="stretch", config=viz.CHART_CONFIG)


def _confidence(result: IndicatorResult) -> str:
    return result.uncertainty.confidence.value.replace("_", " ")


def _category_line(result: IndicatorResult, category: ScenarioCategory | None) -> str | None:
    """The engine's summary for one class of past seasons, in words."""
    if category is None or not result.category_summaries:
        return None
    summary = next((item for item in result.category_summaries if item.category == category), None)
    if summary is None or summary.seasons == 0:
        return None
    count = lambda key: summary.positions.get(key, 0)  # noqa: E731
    lead = f"In the {summary.seasons} {category.value} {result.window_id.replace('-', ' ') if result.window_id else ''} seasons"
    if result.indicator_id == "rainfall_vs_crop_water_use":
        return (f"{lead}: rainfall below the range in {count('below')}, within it in {count('within')}, above it in "
                f"{count('above')}; median {summary.median_value:.0f} mm.")
    if result.indicator_id == "temperature_vs_documented_range":
        outside = count("below") + count("above")
        return (f"{lead}: season mean outside the range in {outside}; median share of days inside the range "
                f"{summary.median_value:g} %.")
    if result.indicator_id == "frost_days":
        return f"{lead}: at most {summary.highest_value:g} frost days in any season."
    return None


def _explanation(result: IndicatorResult, kb: KnowledgeBase) -> None:
    explanation = result.explanation
    st.markdown(
        f"1. **What it measures:** {explanation.what_was_calculated}\n"
        f"2. **What data it uses:** {explanation.data_and_evidence_used}\n"
        f"3. **What assumptions apply:** {explanation.assumptions}\n"
        f"4. **What the result means:** {explanation.what_it_means}\n"
        f"5. **What it does not prove:** {explanation.what_it_does_not_establish}\n"
        f"6. **What would improve confidence:** {explanation.how_to_improve_confidence}"
    )
    if result.conditions:
        st.markdown("**Conditions to read with this result**\n" + "\n".join(f"- {item}" for item in result.conditions))
    if result.missing:
        st.markdown("**What is missing**\n" + "\n".join(f"- {item}" for item in result.missing))
    if result.evidence:
        st.markdown(
            "**Evidence used**\n"
            + "\n".join(
                f"- {item.citation} — {item.locator or 'location not given'} "
                f"({item.status.value.replace('_', ' ')}, used as {item.use.value.replace('_', ' ')})"
                for item in result.evidence
            )
        )
    layers = ", ".join(item.value.replace("_", " ") for item in result.information_layers)
    st.caption(f"Information combined: {layers}. Confidence: {result.uncertainty.confidence_basis}")


def _indicator_card(result: IndicatorResult, category: ScenarioCategory | None, kb: KnowledgeBase, prioritised: bool) -> None:
    with st.container(border=True):
        star = " · ★ your priority" if prioritised else ""
        st.markdown(f"{STATUS_LABELS[result.status]} · confidence {_confidence(result)}{star}")
        st.markdown(result.headline)
        line = _category_line(result, category)
        if line:
            st.caption(line)
        if result.status is IndicatorStatus.CONDITIONAL and result.conditions:
            st.caption(f"Condition: {result.conditions[0]}")
        if result.status is IndicatorStatus.UNAVAILABLE and result.missing:
            st.caption(f"Why unavailable: {result.missing[0]}")
        with st.expander("How to read this result"):
            _explanation(result, kb)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #


def _sidebar(config: PilotConfiguration, kb: KnowledgeBase | None, settings: Settings, dataset: EnvironmentalDataset | None) -> None:
    st.header("Your view")
    st.session_state.setdefault(ui.WINDOW_KEY, config.windows[0].season_id)
    st.session_state.setdefault(ui.CATEGORY_KEY, ui.ALL_SEASONS)
    st.radio(
        "Rainy season",
        [item.season_id for item in config.windows],
        format_func=lambda item: f"{config.window(item).name} ({calendar.month_abbr[config.window(item).start_month]}-"
        f"{calendar.month_abbr[config.window(item).end_month]})",
        key=ui.WINDOW_KEY,
        help="Fixed calendar windows from FAO GIEWS, used for analysis. They are not sowing dates.",
    )
    st.radio(
        "Past seasons to highlight",
        ui.CATEGORY_CHOICES,
        format_func=lambda item: ui.CATEGORY_LABELS[item],
        key=ui.CATEGORY_KEY,
        help="Dry, typical and wet are thirds of the 25 past seasons, ranked by NASA rainfall. Historical, not a forecast.",
    )
    st.divider()
    st.subheader("Farmer priorities")
    if kb is not None:
        st.multiselect(
            "What matters most to you? Choose in order.",
            [item.value for item in PriorityDimension],
            format_func=lambda item: kb.priority(PriorityDimension(item)).label,
            key=ui.PRIORITIES_KEY,
            help="Priorities reorder and highlight the results. They have no weights and produce no ranking.",
        )
    st.caption("Priorities change what is shown first, never the results themselves.")
    st.divider()
    st.subheader("Status")
    st.markdown(f"**Pilot site:** {config.status.value}")
    if dataset is not None:
        st.markdown(f"**NASA data:** {ORIGIN_LABELS[dataset.provenance.origin]}")
    st.markdown(f"**Offline mode:** {'on' if settings.offline_demo_mode else 'off'}")
    for service, status in settings.integration_status().items():
        st.markdown(f"**{service}:** {status}")


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #


def _overview(config: PilotConfiguration, dataset: EnvironmentalDataset | None, scenarios: ScenarioSet | None,
              settings: Settings, data_error: str | None) -> None:
    site = config.site
    left, right = st.columns([3, 2])
    with left:
        st.subheader("The pilot site")
        st.markdown(
            f"**{site.name}** · latitude {site.location.latitude}, longitude {site.location.longitude}"
        )
        st.caption(site.agricultural_context)
        st.caption(f"Site status: {config.status.value}. " + " ".join(f"{item.result}" for item in config.location_checks[:1]))
        if dataset is None:
            st.error(f"NASA data could not be loaded. {data_error}")
            st.caption(
                "Nothing is shown in its place. Check the connection, or set OFFLINE_DEMO_MODE=true to use the "
                "bundled pilot dataset."
            )
            return
        provenance, quality = dataset.provenance, dataset.quality
        mode = "Offline mode is on. " if settings.offline_demo_mode else ""
        st.info(
            f"{mode}This data was {ORIGIN_LABELS[provenance.origin]}. "
            f"NASA supplied it on {provenance.retrieved_at:%d %B %Y at %H:%M} UTC.",
            icon="🛰️",
        )
        observations = quality.expected_days * len(quality.variables)
        st.markdown(
            f"- **Source:** {provenance.service_name} {provenance.service_version or ''} "
            f"({', '.join(provenance.upstream_products) or 'products not reported'})\n"
            f"- **Historical period:** {quality.requested_start:%d %B %Y} to {quality.requested_end:%d %B %Y} "
            f"({quality.expected_days:,} days, {provenance.time_standard.value} days)\n"
            f"- **Observations:** {observations:,} daily values of {len(quality.variables)} variables; "
            f"the least complete variable has values on {quality.lowest_completeness_percent:g}% of days\n"
            f"- **Area represented:** NASA grid cells tens of kilometres wide, with an average elevation of "
            f"{provenance.returned_location.elevation_m:,.0f} m. These are not measurements from an individual farm."
        )
    with right:
        st.subheader("The record at a glance")
        if scenarios is not None:
            first, second = st.columns(2)
            seasons = sum(item.classified_count for item in scenarios.windows)
            first.metric("Past rainy seasons", f"{seasons}", help="Complete seasons in the two windows, 2001-2025.")
            first.metric("Complete years", f"{scenarios.complete_years}", help="Calendar years with every day of rainfall valid.")
            for column, window in zip((second, second), scenarios.windows):
                column.metric(
                    f"{window.window.name}: median rainfall", f"{window.rainfall_median_mm:.0f} mm",
                    help=f"Half the past {window.window.name.lower()} seasons had less. Range "
                    f"{window.rainfall_min_mm:.0f}-{window.rainfall_max_mm:.0f} mm.",
                )
            st.caption("Descriptions of the past record, not forecasts and not scores.")
    if dataset is not None:
        climatology = _climatology(dataset, (dataset.dataset_id, dataset.provenance.payload_sha256, SOURCE_KEY))
        _chart(viz.monthly_rainfall_figure(climatology, [(item.start_month, item.end_month) for item in config.windows]))
    st.subheader("How to use CropShift")
    st.markdown(
        "1. **Climate Explorer**: see how much rain fell in each past rainy season, and which were dry, typical or wet.\n"
        "2. **Rotation Comparison**: set continuous maize, maize with cowpea and maize with pigeon pea side by side "
        "against those past seasons.\n"
        "3. **Soil & Farm Inputs**: add your soil information, if you have it, to see soil-related results.\n"
        "4. **Farmer priorities** (sidebar): choose what matters to you; the results you care about come first.\n"
        "5. **Scientific Evidence**: check every source, every limitation and what the tool does not estimate."
    )
    st.caption(
        "CropShift shows tradeoffs and uncertainty. It gives no overall score, ranks no rotation above another, and "
        "predicts no yields. It supports, and does not replace, farmer judgement and local agricultural advice."
    )


# --------------------------------------------------------------------------- #
# Climate Explorer
# --------------------------------------------------------------------------- #


def _climate_explorer(dataset: EnvironmentalDataset | None, scenarios: ScenarioSet | None, selections: ui.Selections) -> None:
    if dataset is None or scenarios is None:
        st.info("The climate explorer needs the NASA pilot dataset, which could not be loaded. See the Overview.")
        return
    window = scenarios.window(selections.window_id)
    category = selections.category
    start, end = window.window.dates_for(2001)
    st.markdown(
        f"Showing the **{window.window.name.lower()}** ({start:%d %B} to {end:%d %B} each year, the FAO GIEWS window) "
        f"with **{ui.CATEGORY_LABELS[category.value if category else ui.ALL_SEASONS].lower()}** highlighted. "
        "Change this in the sidebar. Every value is from the NASA record of past seasons; nothing is a forecast."
    )
    columns = st.columns(4)
    columns[0].metric("Seasons classified", window.classified_count)
    columns[1].metric("Dry seasons: up to", f"{window.dry_upper_mm:.0f} mm")
    columns[2].metric("Wet seasons: from", f"{window.wet_lower_mm:.0f} mm")
    columns[3].metric("Year-to-year variability", f"{window.rainfall_cv_percent:.0f} %", help="Standard deviation of seasonal totals divided by their mean.")
    _chart(viz.seasonal_rainfall_figure(window, highlight=category))
    with st.expander("How seasons are classified as dry, typical or wet"):
        st.markdown("\n".join(f"{index}. {item}" for index, item in enumerate(scenarios.method, start=1)))
        if window.excluded:
            st.markdown("**Seasons left out:**\n" + "\n".join(f"- {item}" for item in window.excluded))
        else:
            st.caption("No season of this window was left out: every day had a valid rainfall value.")

    st.subheader("Scenario explorer")
    members = window.by_category(category) if category else window.classified()
    members = sorted(members, key=lambda item: item.rank or 0)
    table = pd.DataFrame(
        [
            {
                "Season": item.label,
                "Class": item.category.value if item.category else "not classified",
                "Rank (1 = driest)": item.rank,
                "Rainfall (mm)": item.rainfall_total_mm,
                "Wet days (≥ 1 mm)": item.wet_days,
                "Longest dry spell (days)": item.longest_dry_spell_days,
                "Wettest day (mm)": item.max_daily_rainfall_mm,
                "Mean of daily mean (°C)": item.mean_temperature_c,
                "Lowest daily minimum (°C)": item.lowest_daily_min_c,
                "Highest daily maximum (°C)": item.highest_daily_max_c,
                "Frost days": item.frost_days,
                "Complete (%)": item.precipitation_completeness_percent,
            }
            for item in members
        ]
    )
    st.dataframe(table, hide_index=True, width="stretch")
    if not members:
        st.info("No past season falls in this class.")
        return
    default = window.representative.get(category) if category else None
    options = [item.season_id for item in members]
    chosen = st.selectbox(
        "Look at one past season day by day",
        options,
        index=options.index(default) if default in options else 0,
        format_func=lambda item: window.season(item).label
        + (" (representative season of its class)" if item in window.representative.values() else ""),
        key=f"season_detail_{window.window.season_id}_{category.value if category else 'all'}",
    )
    season = window.season(chosen)
    _chart(viz.season_daily_figure(season))
    if season.issues:
        for issue in season.issues:
            st.caption(issue)

    left, right = st.columns(2)
    with left:
        _chart(viz.rainfall_distribution_figure(scenarios))
    with right:
        _chart(viz.annual_rainfall_figure(scenarios))
    _chart(viz.temperature_figure(window))
    st.caption(
        "Daily mean, daily minimum and daily maximum are different statistics and are never used in place of each "
        "other. Frost days count days with a daily minimum below 0 °C (ETCCDI index FD)."
    )
    with st.expander("Limits of these historical scenarios"):
        st.markdown("\n".join(f"- {item}" for item in scenarios.limitations))
    with st.expander("Data quality and the raw NASA record"):
        _data_quality(dataset)


def _data_quality(dataset: EnvironmentalDataset) -> None:
    quality = dataset.quality
    units = {item.variable: item.unit.value for item in quality.variables}
    if quality.accepted:
        st.success(
            f"Accepted. The least complete variable has valid values on {quality.lowest_completeness_percent:g}% of days "
            f"(minimum required: {quality.min_completeness_percent:g}%).",
            icon="✅",
        )
    else:
        st.error(
            "Not accepted. At least one variable is less complete than the required "
            f"{quality.min_completeness_percent:g}%. This data must not be used for analysis.",
            icon="⛔",
        )
    st.caption(
        "These checks cover structure, units, physical limits and completeness. "
        "They do not show that the values are accurate for a particular farm."
    )
    st.dataframe(
        [
            {
                "Variable": VARIABLE_LABELS.get(item.variable, item.variable),
                "NASA parameter": item.power_parameter,
                "Unit": item.unit.value,
                "Kind of evidence": KIND_LABELS.get(item.kind.value, item.kind.value),
                "Valid days": item.valid_count,
                "Missing days": item.missing_count,
                "Complete (%)": item.completeness_percent,
                "Lowest": item.minimum,
                "Mean": item.mean,
                "Highest": item.maximum,
            }
            for item in quality.variables
        ],
        hide_index=True,
        width="stretch",
    )
    notable = [issue for issue in quality.issues if issue.severity is not IssueSeverity.INFO]
    if notable:
        for issue in notable:
            (st.error if issue.severity is IssueSeverity.ERROR else st.warning)(issue.message)
    else:
        st.caption("No quality warnings or errors for this dataset.")
    wide = to_wide_frame(dataset)
    wide.index = wide.index.strftime("%Y-%m-%d")
    wide.index.name = "Date (UTC)"
    wide = wide.rename(columns={name: _label(name, units[name]) for name in wide.columns})
    st.markdown(f"**First {PREVIEW_ROWS} days**")
    st.dataframe(wide.head(PREVIEW_ROWS), width="stretch")
    st.markdown(f"**Last {PREVIEW_ROWS} days**")
    st.dataframe(wide.tail(PREVIEW_ROWS), width="stretch")
    climatology = _climatology(dataset, (dataset.dataset_id, dataset.provenance.payload_sha256, SOURCE_KEY))
    table = climatology.pivot(index="month", columns="variable", values="mean_value")
    table = table[[name for name in dataset.variables if name in table.columns]]
    monthly_units = climatology.drop_duplicates("variable").set_index("variable")["unit"]
    table = table.rename(columns={name: _label(name, monthly_units[name]) for name in table.columns})
    table.index = [calendar.month_abbr[month] for month in table.index]
    table.index.name = "Month"
    st.markdown("**Average month across the record (descriptive only)**")
    st.dataframe(table.round(1), width="stretch")
    st.caption(
        f"Averages over {quality.requested_start.year} to {quality.requested_end.year}. Rainfall is the monthly total "
        "(sum of daily values). Every other column is the mean of daily values. Months with gaps are left out, never "
        "estimated. This describes the past; it is not a forecast."
    )


# --------------------------------------------------------------------------- #
# Rotation Comparison
# --------------------------------------------------------------------------- #


def _comparison(report: ComparisonReport | None, report_error: str | None, kb: KnowledgeBase | None,
                scenarios: ScenarioSet | None, selections: ui.Selections) -> None:
    if report is None or kb is None or scenarios is None:
        st.info(report_error or "The comparison needs the NASA dataset and the knowledge base. See the Overview.")
        return
    window = scenarios.window(selections.window_id)
    category = selections.category
    st.markdown(
        "Three rotations grown in a cropping-systems experiment at Machakos from 1989 to 1996 (Rao and Mathuva, "
        "2000), set side by side against the past seasons of the NASA record. "
        "**No overall score is calculated and no rotation is recommended.**"
    )
    soil_note = {
        ui.SOIL_MODE_NONE: "No soil information has been given, so soil results are unavailable. Add it in Soil & Farm Inputs.",
        ui.SOIL_MODE_DEMO: "An illustrative soil profile is in use: invented for demonstration, not measured at Katumani.",
        ui.SOIL_MODE_ENTERED: "Your soil information is in use. It has not been verified by CropShift.",
    }[selections.soil_mode]
    if selections.soil_mode == ui.SOIL_MODE_ENTERED and selections.soil is None:
        soil_note = "No valid soil information has been applied yet, so soil results are unavailable."
    st.info(
        f"Showing the **{window.window.name.lower()}**"
        + (f", with the **{category.value}** seasons summarised" if category else "")
        + f". {soil_note}"
    )

    prioritised: set[str] = set()
    if report.priorities is not None:
        st.subheader("Your priorities")
        for section in report.priorities.sections:
            prioritised.update(section.indicator_ids)
            with st.container(border=True):
                st.markdown(f"**{section.order}. {section.label}** · evidence available: {section.evidence_available.replace('_', ' ')}")
                st.caption(section.why_it_matters)
                if section.unsupported_note:
                    st.warning(section.unsupported_note)
                else:
                    names = ", ".join(DEFINITIONS[item].name.lower() for item in section.indicator_ids)
                    st.markdown(f"Results brought forward: {names}. They are marked ★ below.")
                    for note in section.strategy_notes:
                        missing = [item for item in note.missing]
                        if missing:
                            name = report.strategy(note.strategy_id).strategy.name
                            st.caption(f"{name}: {len(missing)} of these results are unavailable for lack of evidence or input.")
        st.caption("Priorities have no weights. They change the order of what is shown, never the results.")

    st.subheader("What changes between these strategies?")
    for note in report.tradeoffs:
        st.markdown(f"- **{note.aspect}.** {note.statement}")

    columns = st.columns(len(report.strategies))
    for column, assessment in zip(columns, report.strategies):
        profile = assessment.profile
        with column:
            with st.container(border=True):
                st.markdown(f"### {profile.name}")
                st.markdown(f"**Sequence:** {' → '.join(crop.common_name for crop in profile.crops)} (repeating)")
                st.markdown(f"**Plant families:** {', '.join(profile.families)}")
                legumes = [crop.common_name for crop in profile.crops if crop.nitrogen_fixing]
                st.markdown(f"**Legume:** {', '.join(legumes) if legumes else 'none'}")
                st.markdown(f"**Evidence:** {profile.evidence.value.replace('_', ' ')} — grown at Machakos; season of each crop not reported")
                counts = assessment.completeness
                st.markdown(f"**Results:** {counts.supported} supported · {counts.conditional} conditional · {counts.unavailable} unavailable")
                with st.expander("Assumptions and study"):
                    if profile.documented_in:
                        st.caption(f"Documented in: {profile.documented_in}")
                    st.markdown("\n".join(f"- {item}" for item in (*profile.assumptions, *profile.limitations)))
                    for note in assessment.background:
                        st.caption(f"Background ({note.evidence.status.value.replace('_', ' ')}): {note.statement}")

    order = report.priorities.indicator_order if report.priorities else tuple(item.indicator_id for item in INDICATORS)
    for title, indicator_ids in GROUPS:
        st.subheader(title)
        ordered = sorted(indicator_ids, key=order.index)
        if title.startswith("Environmental"):
            st.caption("Past seasons only. Rainfall within a fixed window is compared with documented crop ranges; "
                       "this is a first indication, not a water balance and not a forecast.")
            _water_use_charts(report, window)
        for indicator_id in ordered:
            definition = DEFINITIONS[indicator_id]
            star = " ★" if indicator_id in prioritised else ""
            st.markdown(f"#### {definition.name}{star}")
            st.caption(definition.description)
            columns = st.columns(len(report.strategies))
            for column, assessment in zip(columns, report.strategies):
                results = [
                    item for item in assessment.indicator(indicator_id)
                    if item.window_id in (None, window.window.season_id)
                ]
                with column:
                    st.caption(f"**{assessment.strategy.name}**")
                    for result in results:
                        _indicator_card(result, category, kb, indicator_id in prioritised)

    st.subheader("Rotation considerations")
    st.caption("Stored rules from the knowledge base, each evaluated only as far as its evidence allows.")
    columns = st.columns(len(report.strategies))
    for column, assessment in zip(columns, report.strategies):
        with column:
            st.caption(f"**{assessment.strategy.name}**")
            for outcome in ConstraintOutcome:
                findings = [
                    item for item in assessment.constraints
                    if item.outcome is outcome and item.window_id in (None, window.window.season_id)
                ]
                if findings:
                    st.markdown(f"**{OUTCOME_LABELS[outcome]}**")
                    st.markdown("\n".join(f"- {item.finding}" for item in findings))

    st.subheader("Scientific confidence")
    columns = st.columns(len(report.strategies))
    for column, assessment in zip(columns, report.strategies):
        counts = assessment.completeness
        with column:
            st.caption(f"**{assessment.strategy.name}**")
            st.markdown(
                f"- Supported: {counts.supported}\n- Conditional: {counts.conditional}\n- Unavailable: {counts.unavailable}"
            )
            if counts.unavailable_reasons:
                with st.expander("Unavailable results"):
                    st.markdown("\n".join(f"- {item}" for item in counts.unavailable_reasons))
    st.caption("These counts describe how much evidence exists. They are not a score of the rotations.")

    st.subheader("Download this comparison")
    first, second, third = st.columns(3)
    first.download_button("Summary (Markdown)", summary_markdown(report), file_name="cropshift_comparison.md", mime="text/markdown")
    second.download_button("Full report (JSON)", report_json(report), file_name="cropshift_report.json", mime="application/json")
    third.download_button("Comparison record (JSON)", comparison_result_json(report), file_name="cropshift_comparison_result.json", mime="application/json")
    st.caption("Files are created in your browser on request; nothing you enter is stored by CropShift.")


def _water_use_charts(report: ComparisonReport, window) -> None:
    shown: set[str] = set()
    for assessment in report.strategies:
        for result in assessment.indicator("rainfall_vs_crop_water_use", window_id=window.window.season_id):
            if result.status is IndicatorStatus.UNAVAILABLE or result.crop_id in shown:
                continue
            shown.add(result.crop_id)
            crop = next(item for item in assessment.profile.crops if item.crop_id == result.crop_id)
            _chart(viz.water_use_figure(result, crop.common_name, window.window.name))


# --------------------------------------------------------------------------- #
# Soil & Farm Inputs
# --------------------------------------------------------------------------- #


def _clear_entered_soil() -> None:
    """Switching soil mode discards earlier entries, so nothing stale is applied."""
    st.session_state[ui.ENTERED_SOIL_KEY] = None
    st.session_state[ui.SOIL_ERRORS_KEY] = []


def _apply_soil_form() -> None:
    values = {key.removeprefix("soil_form_"): value for key, value in st.session_state.items() if key.startswith("soil_form_")}
    profile, errors = ui.soil_form_to_profile(values)
    st.session_state[ui.ENTERED_SOIL_KEY] = profile if not errors else None
    st.session_state[ui.SOIL_ERRORS_KEY] = errors


def _soil(report: ComparisonReport | None, selections: ui.Selections) -> None:
    st.markdown(
        "Soil information unlocks three soil results: soil pH against each crop's documented pH range, and the water "
        "the crop's root zone can hold and use (FAO-56 Equations 82 and 83). Everything you leave empty stays missing; "
        "nothing is filled in for you. Nothing you enter is stored."
    )
    st.session_state.setdefault(ui.SOIL_MODE_KEY, ui.SOIL_MODE_NONE)
    st.radio(
        "Soil information", list(ui.SOIL_MODE_LABELS), format_func=lambda item: ui.SOIL_MODE_LABELS[item],
        key=ui.SOIL_MODE_KEY, on_change=_clear_entered_soil,
    )
    mode = st.session_state[ui.SOIL_MODE_KEY]
    if mode == ui.SOIL_MODE_NONE:
        st.info("No soil information. Soil results stay unavailable; every other result is calculated as normal.")
    elif mode == ui.SOIL_MODE_DEMO:
        st.warning(
            "**Illustrative soil profile — not measured at Katumani.** pH 6.5, loam, well drained: values invented to "
            "show how the soil results work. They describe no real field, and every result built on them says so.",
            icon="🧪",
        )
    else:
        _soil_form()
    if report is None:
        return
    soil = report.soil
    st.subheader("Soil information in use")
    if soil.records:
        st.dataframe(
            [
                {
                    "Item": item.variable.replace("_", " "),
                    "Value": f"{item.value:g}" if item.value is not None else (item.category or "").replace("_", " "),
                    "Unit": item.unit.value if item.unit else "",
                    "Stated source": item.source_class.value.replace("_", " "),
                    "Verification": item.verification.value.replace("_", " "),
                    "Applies to": item.applies_to,
                    "Warnings": " ".join(item.warnings),
                }
                for item in soil.records
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("None.")
    if soil.water is not None:
        water = soil.water
        amount = (
            f"{water.available_water_min:g}" if water.available_water_min == water.available_water_max
            else f"{water.available_water_min:g} to {water.available_water_max:g}"
        )
        st.markdown(
            f"**Plant-available water used:** {amount} m³/m³ "
            f"({water.basis.value.replace('_', ' ')}; {water.verification.value.replace('_', ' ')})"
        )
        st.caption(" ".join(water.limitations))
    if soil.missing:
        st.markdown("**Still missing**")
        st.markdown("\n".join(f"- **{item.variable.replace('_', ' ')}:** {item.explanation} {item.how_to_obtain}" for item in soil.missing))


def _soil_form() -> None:
    errors = st.session_state.get(ui.SOIL_ERRORS_KEY) or []
    for message in errors:
        st.error(f"Not applied: {message}")
    sources = list(ui.SOURCE_LABELS)
    with st.form("soil_form"):
        st.markdown("**Where the values come from**")
        st.text_input("Field or place the values describe (optional)", key="soil_form_applies_to", placeholder="North field, top 30 cm")
        first, second, third = st.columns(3)
        first.number_input("Sample from depth (cm)", min_value=0.0, max_value=2000.0, value=0.0, step=5.0, key="soil_form_depth_top_cm")
        second.number_input("Sample to depth (cm)", min_value=1.0, max_value=2000.0, value=30.0, step=5.0, key="soil_form_depth_bottom_cm")
        third.date_input("Sample or test date (optional)", value=None, max_value=date.today(), key="soil_form_collected_on")
        st.text_input("Laboratory, report or dataset name (optional; required for a public dataset)", key="soil_form_source_identifier")

        st.markdown("**Soil pH**")
        first, second = st.columns(2)
        first.number_input("Soil pH (in water), 0 to 14; leave empty if not known", min_value=0.0, max_value=14.0, value=None, step=0.1, key="soil_form_ph")
        second.selectbox("Where the pH comes from", sources, format_func=lambda item: ui.SOURCE_LABELS[item], key="soil_form_ph_source")

        st.markdown("**Soil water**")
        st.radio("What do you know about how much water the soil holds?", list(ui.WATER_BASIS_LABELS), format_func=lambda item: ui.WATER_BASIS_LABELS[item], key="soil_form_water_basis", horizontal=True)
        first, second, third, fourth = st.columns(4)
        first.selectbox("Texture class", list(ui.TEXTURE_LABELS), format_func=lambda item: ui.TEXTURE_LABELS[item], index=None, placeholder="Choose", key="soil_form_texture")
        second.number_input("Field capacity (m³/m³, e.g. 0.30)", min_value=0.0, max_value=1.0, value=None, step=0.01, key="soil_form_field_capacity")
        third.number_input("Wilting point (m³/m³, e.g. 0.15)", min_value=0.0, max_value=1.0, value=None, step=0.01, key="soil_form_wilting_point")
        fourth.number_input("Available water capacity (mm per m)", min_value=0.0, max_value=500.0, value=None, step=5.0, key="soil_form_available_water_capacity")
        st.selectbox("Where the soil water information comes from", sources, format_func=lambda item: ui.SOURCE_LABELS[item], key="soil_form_water_source")
        st.caption("Only the values for the option chosen above are used. With only a texture class, typical FAO-56 values "
                   "for that class are used and labelled as typical, not measured.")

        st.markdown("**Drainage**")
        first, second = st.columns(2)
        first.selectbox("How quickly water drains after heavy rain", list(ui.DRAINAGE_LABELS), format_func=lambda item: ui.DRAINAGE_LABELS[item], key="soil_form_drainage")
        second.selectbox("Where the drainage description comes from", sources, format_func=lambda item: ui.SOURCE_LABELS[item], key="soil_form_drainage_source")
        st.form_submit_button("Use this soil information", on_click=_apply_soil_form, type="primary")
    if st.session_state.get(ui.ENTERED_SOIL_KEY) is not None:
        st.success("Your soil information is applied to the comparison. CropShift has not verified it.")


# --------------------------------------------------------------------------- #
# Scientific Evidence
# --------------------------------------------------------------------------- #


def _limitations_panel(report: ComparisonReport | None, scenarios: ScenarioSet | None, config: PilotConfiguration) -> None:
    st.subheader("Important scientific limitations")
    items = []
    if report is not None:
        maize = [
            item for assessment in report.strategies
            for item in assessment.indicator("growing_period_vs_window", crop_id="maize")
        ]
        if maize:
            items.append(f"**Maize rainfall comparison.** {maize[0].headline} Season rainfall totals are therefore not a "
                         "complete maize water balance: rain after the window and water stored in the soil are not counted.")
        cowpea = [
            item for assessment in report.strategies
            for item in assessment.indicator("temperature_vs_documented_range", crop_id="cowpea")
        ]
        if cowpea:
            items.append("**Cowpea temperature comparison.** The source gives 25-35 °C without saying which temperature it "
                         "means. A mismatch with NASA's daily mean does not prove that cowpea is unsuitable.")
        pigeon = [
            item for assessment in report.strategies
            for item in assessment.indicator("rainfall_vs_crop_water_use", crop_id="pigeon-pea")
            if item.status is IndicatorStatus.UNAVAILABLE
        ]
        if pigeon:
            items.append("**Pigeon pea water information.** No verified water requirement exists, so its water results stay "
                         "unavailable. Nothing is borrowed from another crop.")
    items.append("**Historical scenarios.** Dry, typical and wet describe past seasons from 2001 to 2025. They are not "
                 "predictions of future seasons.")
    items.append(f"**Pilot status.** {config.approval_note}")
    st.markdown("\n".join(f"- {item}" for item in items))


def _evidence(report: ComparisonReport | None, dataset: EnvironmentalDataset | None, kb: KnowledgeBase | None,
              gate: EvidenceGate | None, scenarios: ScenarioSet | None, config: PilotConfiguration) -> None:
    st.markdown(
        "CropShift shows where every number comes from and how far it can be trusted. Each result in the comparison "
        "also has its own six-part explanation under *How to read this result*."
    )
    _limitations_panel(report, scenarios, config)

    st.subheader("What CropShift does not estimate")
    outcomes = report.unsupported_outcomes if report is not None else ()
    for item in outcomes:
        st.markdown(f"- **{item.outcome}.** {item.reason} *Would need:* {item.what_would_be_needed}")

    st.subheader("NASA data")
    if dataset is None:
        st.caption("The NASA dataset could not be loaded.")
    else:
        provenance = dataset.provenance
        st.markdown("**How to cite this data**\n" + "\n".join(f"- {item}" for item in provenance.citations))
        st.markdown("**What was requested**")
        st.code(provenance.request_url, language=None)
        st.markdown(
            f"- Fingerprint of the original response (SHA-256): `{provenance.payload_sha256}`\n"
            f"- Observation period: {provenance.requested_start:%d %B %Y} to {provenance.requested_end:%d %B %Y}\n"
            f"- Spatial resolution: {provenance.spatial_resolution}\n"
            f"- Missing data: {provenance.missing_data_treatment}\n"
            "- Source: https://power.larc.nasa.gov/"
        )
        with st.expander("What was done to the data, and what to keep in mind"):
            st.markdown("\n".join(f"- {step}" for step in provenance.transformations))
            st.markdown("**Caveats**\n" + "\n".join(f"- {caveat}" for caveat in provenance.caveats))
            if provenance.source_messages:
                st.markdown("**Messages from the NASA service**\n" + "\n".join(f"- {item}" for item in provenance.source_messages))

    if kb is None or gate is None:
        st.error("The knowledge base could not be loaded, so crop evidence cannot be shown.")
        return
    _knowledge_summary(kb)
    st.subheader("Evidence audit")
    summary = gate.summary()
    st.markdown(
        f"Audit {gate.audit.audit_version} of {gate.audit.audited_on:%d %B %Y}, for knowledge base "
        f"{gate.audit.knowledge_base_version}. Of {len(gate.matrix())} cited claims: "
        f"{summary['status']['verified_direct']} verified as stated, {summary['status']['verified_conditional']} verified "
        f"under stated conditions, {summary['status']['abstract_only']} resting on an abstract (background only), "
        f"{summary['status']['unverified']} excluded from every calculation, {summary['status']['contradicted']} contradicted."
    )
    audits = {item.source_id: item for item in gate.audit.sources}
    st.dataframe(
        [
            {
                "Source": source.title,
                "Year": str(source.year) if source.year else "undated",
                "Read": source.review_status.value.replace("_", " "),
                "Access": audits[source.source_id].access.value.replace("_", " "),
                "Claims": count,
                "Link": source.url,
            }
            for source, count in ((source, gate.kb.claims_by_source()[source.source_id]) for source in kb.sources)
        ],
        hide_index=True,
        width="stretch",
        column_config={"Link": st.column_config.LinkColumn("Link")},
    )
    with st.expander("Full citations"):
        st.markdown("\n".join(f"- {source.citation}" for source in kb.sources))
        for source in gate.audit.method_sources:
            st.markdown(f"- {source.citation} (method source: index definitions)")
    st.caption("The full claim-by-claim audit is in docs/scientific_evidence_audit.md.")


def _knowledge_summary(knowledge: KnowledgeBase) -> None:
    st.subheader("Agronomic knowledge base (provisional)")
    st.caption(
        f"Version {knowledge.manifest.knowledge_base_version}. Provisional: the pilot site has not been approved, so "
        "nothing here says a crop suits that site. Values describe each species in general, under the conditions its "
        "source states."
    )
    st.dataframe(
        [
            {
                "Crop": crop.common_name,
                "Scientific name": crop.scientific_name,
                "Family": crop.botanical_family,
                "Sourced values": len(crop.requirements),
                "Sourced statements": len(crop.attributes),
                "Not established": len(crop.unknowns),
                "Evidence from Machakos": "yes" if crop.regional_evidence else "none found",
                "Record status": crop.data_quality.value,
            }
            for crop in knowledge.crops
        ],
        hide_index=True,
        width="stretch",
    )
    confidence = knowledge.confidence_summary()
    severities = [item.severity.value for item in knowledge.constraints]
    st.markdown(
        f"- **Evidence:** {len(knowledge.sources)} sources and {sum(confidence.values())} cited claims: "
        f"{confidence['directly_supported']} directly supported, {confidence['context_dependent']} context-dependent, "
        f"{confidence['provisional']} provisional, {confidence['insufficient_evidence']} marked as lacking evidence.\n"
        f"- **Rotation knowledge:** {len(knowledge.relationships)} relationships and {len(knowledge.constraints)} stored "
        f"constraints ({severities.count('hard')} hard, {severities.count('advisory')} advisory, "
        f"{severities.count('context_dependent')} context-dependent, {severities.count('unsupported')} recorded as unsupported).\n"
        f"- **Gaps:** {sum(len(crop.unknowns) for crop in knowledge.crops)} attributes are listed as not established by "
        "the sources read. None was filled with an estimate."
    )


# --------------------------------------------------------------------------- #
# About & Methodology
# --------------------------------------------------------------------------- #


def _about(settings: Settings, scenarios: ScenarioSet | None) -> None:
    st.markdown(
        f"**Development stage {CURRENT_PHASE} of A9: demonstration and submission.** The NASA data layer, the cited "
        "knowledge base, the comparison engine and this interface work, and were checked in an internal validation "
        "(A8). Optional AI explanations (A6) and research reports (A7) are deferred: not built, and switched off."
    )
    st.subheader("What CropShift does")
    st.markdown(
        "It helps a farmer explore crop-rotation options by comparing continuous maize with two legume rotations "
        "across **dry, typical and wet seasons from the historical record**, using NASA Earth data, the farmer's soil "
        "information, cited crop characteristics and the farmer's own priorities. It shows tradeoffs and uncertainty "
        "rather than a single answer."
    )
    st.subheader("Method in brief")
    if scenarios is not None:
        st.markdown("**Historical scenarios**\n" + "\n".join(f"- {item}" for item in scenarios.method))
    st.markdown("**Comparison indicators**")
    st.dataframe(
        [{"Indicator": item.name, "Scope": item.scope.value, "Method": item.method, "A3 mapping": item.mapping_id or ""} for item in INDICATORS],
        hide_index=True,
        width="stretch",
    )
    st.markdown(
        "**Evidence gate.** No literature value reaches a result unless it was re-checked against its source in the "
        "evidence audit. A context-dependent value is shown with its conditions; an abstract-only claim may explain a "
        "result but never calculate one; unsupported claims are excluded.\n\n"
        "**No score.** The indicators measure unlike things and no defensible method exists here to weigh them, so "
        "strategies are shown side by side."
    )
    st.caption(
        "Documentation in the repository: docs/rotation_comparison_methodology.md, docs/historical_scenarios.md, "
        "docs/scientific_evidence_audit.md, docs/soil_input_mapping.md, docs/uncertainty.md, docs/a5_application_guide.md."
    )
    st.subheader("Build status")
    st.dataframe([{"Phase": phase.code, "Scope": phase.title, "Status": phase.status} for phase in PHASES], hide_index=True, width="stretch")
    with st.expander("Modules and what each one does"):
        st.dataframe(
            [
                {
                    "Module": f"src/{module.name}.py",
                    "Phase": module.phase,
                    "Responsibility": module.responsibility,
                    "State": "working" if module.implemented else ("deferred" if module.deferred else "placeholder"),
                }
                for module in MODULES
            ],
            hide_index=True,
            width="stretch",
        )
    st.subheader("Current settings")
    run_mode = (
        "Offline demo: stored NASA responses only, no network requests"
        if settings.offline_demo_mode
        else "Live: NASA data is retrieved when it is not already cached"
    )
    st.markdown(f"- **Run mode:** {run_mode}")
    for service, status in settings.integration_status().items():
        st.markdown(f"- **{service}:** {status}")
    st.caption("External AI services are optional and off by default. The scientific calculations never depend on them.")
    st.subheader("AI assistance")
    st.caption(
        "Built during the hackathon with an AI coding assistant (Claude Code, by Anthropic) under the participant's "
        "direction. No AI-generated images, video, audio or scientific data are included; see docs/provenance.md."
    )


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

st.set_page_config(page_title=PROJECT_NAME, page_icon="🌾", layout="wide")

st.title(PROJECT_NAME)
st.markdown("**Explore historical climate conditions and compare evidence-backed crop rotations.**")
st.caption(f"{EVENT_NAME} · {CHALLENGE_NAME}")

try:
    settings = get_settings()
except ValidationError as error:
    # Show which settings are wrong without echoing their values.
    names = sorted({str(item["loc"][0]).upper() for item in error.errors() if item["loc"]})
    st.error(
        "The configuration is invalid, so the app has stopped. "
        f"Check these settings in your .env file: {', '.join(names)}. "
        "See .env.example for the allowed values."
    )
    st.stop()

SOURCE_KEY = _source_fingerprint()
config = pilot_configuration()
request = config.site.request()
fingerprint = (
    request.cache_key(),
    settings.offline_demo_mode,
    str(settings.nasa_cache_path),
    str(settings.nasa_demo_path),
    settings.nasa_min_completeness_percent,
    settings.nasa_power_base_url,
    SOURCE_KEY,
)
dataset: EnvironmentalDataset | None = None
data_error: str | None = None
try:
    dataset = _pilot_dataset(settings, fingerprint)
except NasaDataError as error:
    data_error = str(error)

kb: KnowledgeBase | None = None
gate: EvidenceGate | None = None
try:
    kb, gate = _knowledge(SOURCE_KEY)
except KnowledgeBaseError as error:
    LOG.warning("knowledge base not loaded: %s", error)

scenarios: ScenarioSet | None = None
if dataset is not None and dataset.quality.accepted:
    try:
        scenarios = _scenarios(dataset, (dataset.dataset_id, dataset.provenance.payload_sha256, SOURCE_KEY))
    except Exception:  # noqa: BLE001
        LOG.exception("scenarios could not be built")

with st.sidebar:
    _guarded("sidebar", _sidebar, config, kb, settings, dataset)

selections = ui.read_selections(st.session_state, window_ids=[item.season_id for item in config.windows])

report: ComparisonReport | None = None
report_error: str | None = None
if scenarios is not None and kb is not None and gate is not None:
    try:
        soil_json, priorities = selections.cache_key()
        report = _report(
            scenarios, kb, gate,
            (SOURCE_KEY, scenarios.payload_sha256, kb.manifest.knowledge_base_version, gate.audit.audit_version, soil_json, priorities),
        )
    except Exception:  # noqa: BLE001
        LOG.exception("comparison failed")
        report_error = "The comparison could not be calculated with these inputs. Try clearing the soil information."

st.warning(
    f"{config.approval_note} Dry, typical and wet seasons are past seasons, not forecasts. "
    "No rotation is scored, ranked or recommended.",
    icon="📍",
)

tabs = st.tabs(TAB_NAMES)
with tabs[0]:
    _guarded("Overview", _overview, config, dataset, scenarios, settings, data_error)
with tabs[1]:
    _guarded("Climate Explorer", _climate_explorer, dataset, scenarios, selections)
with tabs[2]:
    _guarded("Rotation Comparison", _comparison, report, report_error, kb, scenarios, selections)
with tabs[3]:
    _guarded("Soil & Farm Inputs", _soil, report, selections)
with tabs[4]:
    _guarded("Scientific Evidence", _evidence, report, dataset, kb, gate, scenarios, config)
with tabs[5]:
    _guarded("About & Methodology", _about, settings, scenarios)

st.divider()
st.caption(DEFAULT_DISCLAIMER)
st.caption(
    f"Version {__version__} · NASA data from the NASA POWER project; this project is not endorsed by NASA · "
    "Built during the hackathon with AI coding assistance; see docs/provenance.md."
)
