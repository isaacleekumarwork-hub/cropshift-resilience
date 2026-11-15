"""Historical environmental scenarios (phase A4.4).

Responsibility
    Summarise the validated NASA record over each rainy-season window, year by
    year, and classify the complete seasons as dry, typical or wet relative to
    one another. Every number describes a season that actually happened at the
    site's NASA grid cells; nothing here is synthetic, averaged across unrelated
    years, or a forecast.

Method
    1. For every season window and every year, take the daily NASA values
       between the window's first and last day (UTC days, as NASA POWER
       delivers them).
    2. A season's rainfall total is reported only when every day has a valid
       value (``SEASON_TOTAL_MIN_COMPLETENESS_PERCENT`` = 100), because a total
       over fewer days is biased low. Temperature summaries need 80 % of days.
       Seasons that are incomplete, or fall partly outside the observation
       period, are listed with the reason and left out of the classification.
    3. The complete seasons of one window are ranked by rainfall total, lowest
       first; equal totals are ordered by year, so the ranking is reproducible.
       With *n* seasons and *k* = floor(*n* / 3), the *k* lowest are **dry**,
       the *k* highest are **wet**, and the rest are **typical**. With 25
       seasons that is 8 dry, 9 typical and 8 wet. At least
       ``MIN_SEASONS_FOR_CLASSIFICATION`` complete seasons are required.
       Terciles are this project's choice of method, not a cited standard.
    4. The representative season of a category is its median-ranked member
       (the lower of the two middle seasons when the count is even). It is a
       real season, not a composite.

Rainfall and temperature descriptors
    Wet days, dry spells and heavy-rain days use the definitions of the ETCCDI
    climate indices (wet day: at least 1 mm; CDD: longest run of days below
    1 mm; R10mm, R20mm; Rx1day; SDII). Frost days use ETCCDI index FD: daily
    minimum temperature below 0 °C. ETCCDI defines these for station records
    over a year; applying them within a season window to a reanalysis
    grid-cell average is an adaptation, recorded as a limitation.

What this does not do
    It does not model a water balance, predict anything or say whether any crop
    would have succeeded. Rainfall totals are not the water available to a
    crop. Crop comparisons are made in ``comparison_engine``.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

import pandas as pd
from pydantic import Field, model_validator

from src.data_processing import MONTHLY_MEAN_MIN_COMPLETENESS_PERCENT, to_wide_frame
from src.data_validation import EnvironmentalDataset
from src.models import (
    Contract,
    DataKind,
    GeoLocation,
    HistoricalScenario,
    ProvenanceRecord,
    ScenarioCategory,
    Slug,
    Text,
)
from src.season_config import SeasonWindow

ENGINE_VERSION = "0.4.0"
ENGINE_SOURCE_ID = "cropshift-scenario-engine"

WET_DAY_THRESHOLD_MM = 1.0  # ETCCDI wet day and CDD threshold
HEAVY_RAIN_THRESHOLDS_MM = (10.0, 20.0)  # ETCCDI R10mm and R20mm
FROST_THRESHOLD_C = 0.0  # ETCCDI FD: daily minimum below 0 °C
SEASON_TOTAL_MIN_COMPLETENESS_PERCENT = 100.0
TEMPERATURE_MIN_COMPLETENESS_PERCENT = MONTHLY_MEAN_MIN_COMPLETENESS_PERCENT
MIN_SEASONS_FOR_CLASSIFICATION = 9

REQUIRED_VARIABLES = ("precipitation", "air_temperature_mean", "air_temperature_max", "air_temperature_min")

CLASSIFICATION_METHOD = (
    "Complete seasons of one window ranked by NASA rainfall total, lowest first (ties ordered by year). "
    "With n seasons and k = floor(n / 3): the k lowest are dry, the k highest are wet, the rest typical. "
    "Terciles are this project's choice, not a cited standard."
)

SCENARIO_LIMITATIONS = (
    "Dry, typical and wet describe past seasons relative to each other at this site, 2001 to 2025. They are "
    "not forecasts and say nothing about future seasons.",
    "Rainfall is NASA POWER's MERRA-2 reanalysis estimate for a grid cell about 55 km by 70 km, not a gauge on "
    "a farm. Daily rain-day counts for a grid-cell average can differ from those at a single point.",
    "A rainfall total is not the water available to a crop: runoff, evaporation, soil storage and irrigation all "
    "intervene. No water balance is modelled.",
    "Season windows are fixed calendar windows. Real rainy seasons start and end on different dates each year.",
    "The ETCCDI index definitions are for station records over a year; here they are applied within a season "
    "window to a reanalysis grid-cell average.",
)


class ScenarioEngineError(ValueError):
    """The dataset cannot support the requested scenarios."""


# --------------------------------------------------------------------------- #
# Result contracts
# --------------------------------------------------------------------------- #


class MonthRainfall(Contract):
    year: int
    month: int = Field(ge=1, le=12)
    total_mm: float | None
    days_valid: int
    days_expected: int


class SeasonClimate(Contract):
    """What one past season was like at the site, from the NASA record."""

    season_id: Slug
    window_id: Slug
    season_year: int
    label: Text
    start: date
    end: date
    days_expected: int = Field(gt=0)
    precipitation_days_valid: int = Field(ge=0)
    temperature_days_valid: int = Field(ge=0)
    precipitation_completeness_percent: float = Field(ge=0, le=100)
    temperature_completeness_percent: float = Field(ge=0, le=100)
    within_observation_period: bool
    complete: bool = Field(description="True when the rainfall total meets the completeness threshold.")

    rainfall_total_mm: float | None = None
    monthly_rainfall: tuple[MonthRainfall, ...] = ()
    wet_days: int | None = None
    dry_days: int | None = None
    longest_dry_spell_days: int | None = None
    max_daily_rainfall_mm: float | None = None
    heavy_rain_days_10mm: int | None = None
    heavy_rain_days_20mm: int | None = None
    mean_wet_day_rainfall_mm: float | None = None

    mean_temperature_c: float | None = None
    mean_daily_max_c: float | None = None
    mean_daily_min_c: float | None = None
    lowest_daily_min_c: float | None = None
    highest_daily_max_c: float | None = None
    frost_days: int | None = None

    daily_precipitation_mm: tuple[float | None, ...] = ()
    daily_mean_temperature_c: tuple[float | None, ...] = ()
    daily_min_temperature_c: tuple[float | None, ...] = ()
    daily_max_temperature_c: tuple[float | None, ...] = ()

    category: ScenarioCategory | None = None
    rank: int | None = Field(default=None, ge=1, description="1 is the driest complete season of the window.")
    percentile_rank: float | None = Field(default=None, ge=0, le=100)
    scenario: HistoricalScenario | None = None
    issues: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def _check_season(self) -> "SeasonClimate":
        if self.end < self.start:
            raise ValueError("a season cannot end before it starts")
        if self.days_expected != (self.end - self.start).days + 1:
            raise ValueError("days_expected must match the season dates")
        if self.complete and self.rainfall_total_mm is None:
            raise ValueError("a complete season needs a rainfall total")
        if self.category is not None and not self.complete:
            raise ValueError("only complete seasons are classified")
        if self.category is not None and self.scenario is None:
            raise ValueError("a classified season carries its historical scenario record")
        return self


class WindowScenarios(Contract):
    """All past seasons of one window, and their classification."""

    window: SeasonWindow
    seasons: tuple[SeasonClimate, ...]
    classified_count: int = Field(ge=0)
    excluded: tuple[Text, ...] = Field(default=(), description="Seasons left out, each with the reason.")
    dry_upper_mm: float | None = Field(default=None, description="Rainfall of the wettest dry season.")
    wet_lower_mm: float | None = Field(default=None, description="Rainfall of the driest wet season.")
    representative: dict[ScenarioCategory, Slug] = {}
    rainfall_mean_mm: float | None = None
    rainfall_median_mm: float | None = None
    rainfall_min_mm: float | None = None
    rainfall_max_mm: float | None = None
    rainfall_cv_percent: float | None = Field(
        default=None, description="Year-to-year variability: sample standard deviation over mean."
    )

    def by_category(self, category: ScenarioCategory) -> tuple[SeasonClimate, ...]:
        return tuple(item for item in self.seasons if item.category == category)

    def classified(self) -> tuple[SeasonClimate, ...]:
        return tuple(item for item in self.seasons if item.category is not None)

    def season(self, season_id: str) -> SeasonClimate:
        for item in self.seasons:
            if item.season_id == season_id:
                return item
        raise KeyError(f"no season '{season_id}'")


class AnnualRainfall(Contract):
    year: int
    total_mm: float | None
    days_valid: int
    days_expected: int
    complete: bool


class ScenarioSet(Contract):
    """Historical scenarios for one site, with the paperwork to trace every number."""

    engine_version: Text
    dataset_id: Text
    payload_sha256: Text
    site_name: Text | None
    location: GeoLocation
    returned_location: GeoLocation
    observation_start: date
    observation_end: date
    first_valid_day: date | None
    last_valid_day: date | None
    windows: tuple[WindowScenarios, ...] = Field(min_length=1)
    annual_rainfall: tuple[AnnualRainfall, ...] = ()
    complete_years: int = Field(ge=0, description="Calendar years with every day of rainfall valid.")
    thresholds: dict[str, float]
    method: tuple[Text, ...]
    limitations: tuple[Text, ...]
    dataset_citations: tuple[Text, ...] = Field(min_length=1)
    method_source_ids: tuple[Slug, ...]
    provenance: ProvenanceRecord

    def window(self, season_id: str) -> WindowScenarios:
        for item in self.windows:
            if item.window.season_id == season_id:
                return item
        raise KeyError(f"no window '{season_id}' in the scenario set")

    def season(self, season_id: str) -> SeasonClimate:
        for item in self.windows:
            for season in item.seasons:
                if season.season_id == season_id:
                    return season
        raise KeyError(f"no season '{season_id}' in the scenario set")


# --------------------------------------------------------------------------- #
# Calculation
# --------------------------------------------------------------------------- #


def _rounded(value: float | None, digits: int = 2) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def _values(frame: pd.DataFrame, column: str) -> tuple[float | None, ...]:
    return tuple(None if pd.isna(item) else round(float(item), 2) for item in frame[column].tolist())


def _longest_run(flags: list[bool]) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def _season(
    window: SeasonWindow,
    season_year: int,
    wide: pd.DataFrame,
    observed: tuple[date, date],
    location: GeoLocation,
    min_completeness: float,
) -> SeasonClimate | None:
    start, end = window.dates_for(season_year)
    first, last = observed
    if end < first or start > last:
        return None  # entirely outside the record: not a season of this dataset
    days_expected = (end - start).days + 1
    inside = first <= start and end <= last
    days = pd.date_range(start, end, freq="D")
    frame = wide.reindex(days)
    rain = frame["precipitation"]
    mean_t = frame["air_temperature_mean"]
    rain_valid = int(rain.notna().sum())
    temp_valid = int(mean_t.notna().sum())
    rain_pct = round(100.0 * rain_valid / days_expected, 2)
    temp_pct = round(100.0 * temp_valid / days_expected, 2)
    complete = inside and rain_valid > 0 and rain_pct >= min_completeness
    issues = []
    if not inside:
        issues.append("Part of the window lies outside the observation period, so the season is incomplete.")
    if rain_valid < days_expected:
        issues.append(f"{days_expected - rain_valid} of {days_expected} days have no valid rainfall value.")
    if complete and rain_valid < days_expected:
        issues.append("The rainfall total covers fewer days than the window and is biased low.")

    fields: dict = dict(
        season_id=f"{window.season_id}-{season_year}",
        window_id=window.season_id,
        season_year=season_year,
        label=window.label_for(season_year),
        start=start,
        end=end,
        days_expected=days_expected,
        precipitation_days_valid=rain_valid,
        temperature_days_valid=temp_valid,
        precipitation_completeness_percent=rain_pct,
        temperature_completeness_percent=temp_pct,
        within_observation_period=inside,
        complete=complete,
        daily_precipitation_mm=_values(frame, "precipitation"),
        daily_mean_temperature_c=_values(frame, "air_temperature_mean"),
        daily_min_temperature_c=_values(frame, "air_temperature_min"),
        daily_max_temperature_c=_values(frame, "air_temperature_max"),
    )
    if complete:
        valid = rain.dropna()
        wet = valid >= WET_DAY_THRESHOLD_MM
        fields.update(
            rainfall_total_mm=round(float(valid.sum()), 2),
            wet_days=int(wet.sum()),
            dry_days=int((~wet).sum()),
            longest_dry_spell_days=_longest_run([bool(item < WET_DAY_THRESHOLD_MM) for item in valid.tolist()]),
            max_daily_rainfall_mm=round(float(valid.max()), 2),
            heavy_rain_days_10mm=int((valid >= HEAVY_RAIN_THRESHOLDS_MM[0]).sum()),
            heavy_rain_days_20mm=int((valid >= HEAVY_RAIN_THRESHOLDS_MM[1]).sum()),
            mean_wet_day_rainfall_mm=_rounded(valid[wet].mean()) if bool(wet.any()) else None,
        )
        months = []
        for (year, month), group in rain.groupby([rain.index.year, rain.index.month], sort=True):
            group_valid = group.dropna()
            months.append(
                MonthRainfall(
                    year=int(year), month=int(month),
                    total_mm=round(float(group_valid.sum()), 2) if len(group_valid) == len(group) else None,
                    days_valid=int(len(group_valid)), days_expected=int(len(group)),
                )
            )
        fields["monthly_rainfall"] = tuple(months)
    if inside and temp_pct >= TEMPERATURE_MIN_COMPLETENESS_PERCENT:
        tmin, tmax = frame["air_temperature_min"].dropna(), frame["air_temperature_max"].dropna()
        fields.update(
            mean_temperature_c=_rounded(mean_t.dropna().mean()),
            mean_daily_max_c=_rounded(tmax.mean()),
            mean_daily_min_c=_rounded(tmin.mean()),
            lowest_daily_min_c=_rounded(tmin.min()),
            highest_daily_max_c=_rounded(tmax.max()),
            frost_days=int((tmin < FROST_THRESHOLD_C).sum()),
        )
        if temp_valid < days_expected:
            issues.append(f"Temperature summaries cover {temp_valid} of {days_expected} days.")
    elif inside:
        issues.append("Too few valid temperature days for temperature summaries.")
    fields["issues"] = tuple(issues)
    return SeasonClimate(**fields)


def _classify(
    window: SeasonWindow,
    seasons: list[SeasonClimate],
    location: GeoLocation,
    baseline: tuple[date, date],
) -> WindowScenarios:
    complete = sorted((item for item in seasons if item.complete), key=lambda item: (item.rainfall_total_mm, item.season_year))
    excluded = tuple(
        f"{item.label}: {' '.join(item.issues) or 'incomplete'}" for item in seasons if not item.complete
    )
    n = len(complete)
    if n < MIN_SEASONS_FOR_CLASSIFICATION:
        return WindowScenarios(
            window=window, seasons=tuple(seasons), classified_count=0,
            excluded=excluded + (
                f"Only {n} complete seasons; at least {MIN_SEASONS_FOR_CLASSIFICATION} are needed to classify "
                "dry, typical and wet seasons.",
            ),
        )
    k = n // 3
    updated: dict[str, SeasonClimate] = {}
    for rank, item in enumerate(complete, start=1):
        if rank <= k:
            category = ScenarioCategory.DRY
        elif rank > n - k:
            category = ScenarioCategory.WET
        else:
            category = ScenarioCategory.TYPICAL
        percentile = round(100.0 * (rank - 0.5) / n, 1)
        scenario = HistoricalScenario(
            scenario_id=item.season_id,
            category=category,
            label=f"{item.label} ({category.value})",
            location=location,
            period_start=item.start,
            period_end=item.end,
            baseline_start=baseline[0],
            baseline_end=baseline[1],
            classification_variable="precipitation_total",
            classification_method=CLASSIFICATION_METHOD,
            percentile_rank=percentile,
            source_ids=("nasa-power",),
            limitations=SCENARIO_LIMITATIONS,
        )
        updated[item.season_id] = item.model_copy(
            update={"category": category, "rank": rank, "percentile_rank": percentile, "scenario": scenario}
        )
    final = tuple(updated.get(item.season_id, item) for item in seasons)
    totals = [item.rainfall_total_mm for item in complete]  # type: ignore[misc]
    series = pd.Series(totals, dtype="float64")
    representative = {}
    for category in ScenarioCategory:
        members = sorted(
            (item for item in final if item.category is category), key=lambda item: (item.rank or 0)
        )
        if members:
            representative[category] = members[(len(members) - 1) // 2].season_id
    mean = float(series.mean())
    return WindowScenarios(
        window=window,
        seasons=final,
        classified_count=n,
        excluded=excluded,
        dry_upper_mm=totals[k - 1],
        wet_lower_mm=totals[n - k],
        representative=representative,
        rainfall_mean_mm=round(mean, 2),
        rainfall_median_mm=round(float(series.median()), 2),
        rainfall_min_mm=round(float(series.min()), 2),
        rainfall_max_mm=round(float(series.max()), 2),
        rainfall_cv_percent=round(100.0 * float(series.std(ddof=1)) / mean, 1) if mean > 0 else None,
    )


def _annual(wide: pd.DataFrame, observed: tuple[date, date]) -> tuple[AnnualRainfall, ...]:
    rows = []
    for year in range(observed[0].year, observed[1].year + 1):
        days = pd.date_range(date(year, 1, 1), date(year, 12, 31), freq="D")
        rain = wide.reindex(days)["precipitation"]
        valid = rain.dropna()
        inside = observed[0] <= date(year, 1, 1) and date(year, 12, 31) <= observed[1]
        complete = inside and len(valid) == len(days)
        rows.append(
            AnnualRainfall(
                year=year,
                total_mm=round(float(valid.sum()), 2) if complete else None,
                days_valid=int(len(valid)),
                days_expected=int(len(days)),
                complete=complete,
            )
        )
    return tuple(rows)


def build_scenarios(
    dataset: EnvironmentalDataset,
    windows: Sequence[SeasonWindow],
    *,
    min_completeness_percent: float = SEASON_TOTAL_MIN_COMPLETENESS_PERCENT,
) -> ScenarioSet:
    """Summarise and classify every past season of every window in the dataset."""
    if not 0 < min_completeness_percent <= 100:
        raise ScenarioEngineError("min_completeness_percent must be above 0 and at most 100")
    if not windows:
        raise ScenarioEngineError("at least one season window is needed")
    dataset.require_accepted()
    missing = [name for name in REQUIRED_VARIABLES if dataset.get(name) is None]
    if missing:
        raise ScenarioEngineError(f"the dataset lacks variables needed for scenarios: {', '.join(missing)}")
    for item in REQUIRED_VARIABLES:
        series = dataset.get(item)
        if series is not None and series.observations[0].provenance.kind not in (
            DataKind.REANALYSIS, DataKind.SATELLITE_RETRIEVAL, DataKind.GROUND_MEASUREMENT
        ):
            raise ScenarioEngineError(f"'{item}' is not an observation-based series; scenarios use observed data only")

    wide = to_wide_frame(dataset)
    wide.index = pd.DatetimeIndex(wide.index)
    observed = (dataset.provenance.requested_start, dataset.provenance.requested_end)
    location = dataset.location

    results = []
    for window in windows:
        seasons = []
        for year in range(observed[0].year - 1, observed[1].year + 1):
            season = _season(window, year, wide, observed, location, min_completeness_percent)
            if season is not None:
                seasons.append(season)
        results.append(_classify(window, seasons, location, observed))

    annual = _annual(wide, observed)
    method = (
        f"Daily NASA POWER values are taken between each window's first and last day (UTC days).",
        f"A season's rainfall total requires {min_completeness_percent:g} % of days valid; temperature "
        f"summaries require {TEMPERATURE_MIN_COMPLETENESS_PERCENT:g} %.",
        CLASSIFICATION_METHOD,
        "The representative season of each category is its median-ranked member, a real season.",
        f"Wet day: at least {WET_DAY_THRESHOLD_MM:g} mm (ETCCDI). Longest dry spell: the longest run of days below "
        f"{WET_DAY_THRESHOLD_MM:g} mm within the window (ETCCDI CDD, applied to a season).",
        f"Heavy-rain days: at least {HEAVY_RAIN_THRESHOLDS_MM[0]:g} mm and {HEAVY_RAIN_THRESHOLDS_MM[1]:g} mm (ETCCDI "
        "R10mm, R20mm). Frost day: daily minimum below 0 °C (ETCCDI FD).",
        "Year-to-year variability is the sample standard deviation of seasonal totals divided by their mean.",
    )
    return ScenarioSet(
        engine_version=ENGINE_VERSION,
        dataset_id=dataset.dataset_id,
        payload_sha256=dataset.provenance.payload_sha256,
        site_name=dataset.site_name,
        location=location,
        returned_location=dataset.provenance.returned_location,
        observation_start=observed[0],
        observation_end=observed[1],
        first_valid_day=dataset.provenance.returned_start,
        last_valid_day=dataset.provenance.returned_end,
        windows=tuple(results),
        annual_rainfall=annual,
        complete_years=sum(1 for item in annual if item.complete),
        thresholds={
            "wet_day_mm": WET_DAY_THRESHOLD_MM,
            "heavy_rain_10mm": HEAVY_RAIN_THRESHOLDS_MM[0],
            "heavy_rain_20mm": HEAVY_RAIN_THRESHOLDS_MM[1],
            "frost_below_c": FROST_THRESHOLD_C,
            "season_total_min_completeness_percent": min_completeness_percent,
            "temperature_min_completeness_percent": TEMPERATURE_MIN_COMPLETENESS_PERCENT,
        },
        method=method,
        limitations=SCENARIO_LIMITATIONS,
        dataset_citations=dataset.provenance.citations,
        method_source_ids=("etccdi-indices", "fao-giews-kenya"),
        provenance=ProvenanceRecord(
            kind=DataKind.DERIVED,
            source_id=ENGINE_SOURCE_ID,
            source_name="CropShift historical scenario engine",
            source_version=ENGINE_VERSION,
            transformations=method,
        ),
    )
