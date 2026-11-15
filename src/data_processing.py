"""Basic processing of validated NASA observations.

Responsibility
    Turn a validated dataset into tables and simple descriptive summaries that
    later phases and the interface can use. Only description: nothing here
    scores a crop, ranks a rotation, predicts a yield or forecasts weather.

Aggregation rules (daily to monthly)
    Different variables need different arithmetic, and the two are never
    interchangeable:

    * Precipitation is **summed**. A monthly total in millimetres is the sum
      of the daily rates (mm/day x 1 day). Its variable becomes
      ``precipitation_total`` so that mm and mm/day cannot be confused.
    * Temperature, solar irradiance and humidity are **averaged**. A monthly
      mean of daily maximum temperature is the average of the daily maxima,
      not the highest value of the month.

    Months with gaps:

    * A total is reported only when every day of the month is valid, because
      a sum over fewer days is biased low.
    * A mean is reported when at least 80 % of the month's days are valid.
    * Otherwise the month is marked "not reported" and its value is left
      empty. It is never estimated.

    Both thresholds are arguments of ``monthly_summary`` and can be changed.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import calendar
from typing import NamedTuple

import pandas as pd

from src.data_validation import EnvironmentalDataset
from src.models import Unit

MONTHLY_TOTAL_MIN_COMPLETENESS_PERCENT = 100.0
MONTHLY_MEAN_MIN_COMPLETENESS_PERCENT = 80.0


class AggregationRule(NamedTuple):
    """How one daily variable becomes a monthly value."""

    statistic: str  # "total" or "mean"
    output_variable: str
    output_unit: Unit
    method: str


AGGREGATION_RULES: dict[str, AggregationRule] = {
    "precipitation": AggregationRule(
        "total", "precipitation_total", Unit.MILLIMETRE,
        "Sum of daily precipitation over the month",
    ),
    "air_temperature_mean": AggregationRule(
        "mean", "air_temperature_mean", Unit.DEGREE_CELSIUS,
        "Mean of daily mean temperatures",
    ),
    "air_temperature_max": AggregationRule(
        "mean", "air_temperature_max", Unit.DEGREE_CELSIUS,
        "Mean of daily maximum temperatures",
    ),
    "air_temperature_min": AggregationRule(
        "mean", "air_temperature_min", Unit.DEGREE_CELSIUS,
        "Mean of daily minimum temperatures",
    ),
    "solar_irradiance": AggregationRule(
        "mean", "solar_irradiance", Unit.MEGAJOULE_PER_M2_PER_DAY,
        "Mean of daily irradiance",
    ),
    "relative_humidity": AggregationRule(
        "mean", "relative_humidity", Unit.PERCENT,
        "Mean of daily mean relative humidity",
    ),
}

DAILY_COLUMNS = ["date", "variable", "value", "unit", "missing", "quality", "kind", "source"]
MONTHLY_COLUMNS = [
    "year", "month", "variable", "statistic", "value", "unit", "output_variable",
    "days_expected", "days_valid", "completeness_percent", "reported", "method",
]
CLIMATOLOGY_COLUMNS = [
    "variable", "month", "statistic", "mean_value", "lowest", "highest", "unit", "years_used", "years_available",
]


def to_frame(dataset: EnvironmentalDataset) -> pd.DataFrame:
    """Long table: one row per variable and day. Gaps have an empty value and a reason."""
    rows = [
        (
            pd.Timestamp(item.period_start),
            item.variable,
            item.value,
            item.unit.value,
            item.missing.value,
            item.quality.value,
            item.provenance.kind.value,
            item.provenance.source_name,
        )
        for series in dataset.series
        for item in series.observations
    ]
    frame = pd.DataFrame(rows, columns=DAILY_COLUMNS)
    frame["value"] = frame["value"].astype("float64")
    return frame.sort_values(["variable", "date"], kind="stable").reset_index(drop=True)


def to_wide_frame(dataset: EnvironmentalDataset) -> pd.DataFrame:
    """Wide table: one row per day, one column per variable. Gaps stay empty."""
    frame = to_frame(dataset)
    wide = frame.pivot(index="date", columns="variable", values="value").sort_index()
    wide.columns.name = None
    return wide[[name for name in dataset.variables if name in wide.columns]]


def monthly_summary(
    dataset: EnvironmentalDataset,
    *,
    total_min_completeness_percent: float = MONTHLY_TOTAL_MIN_COMPLETENESS_PERCENT,
    mean_min_completeness_percent: float = MONTHLY_MEAN_MIN_COMPLETENESS_PERCENT,
) -> pd.DataFrame:
    """Monthly totals and means, with the completeness of every month.

    ``days_expected`` is the full length of the calendar month, so a month
    only partly covered by the request counts as incomplete.
    """
    for threshold in (total_min_completeness_percent, mean_min_completeness_percent):
        if not 0 <= threshold <= 100:
            raise ValueError("completeness thresholds must be between 0 and 100")

    daily = to_frame(dataset)
    rows = []
    for variable in dataset.variables:
        rule = AGGREGATION_RULES.get(variable)
        if rule is None:
            raise ValueError(f"no monthly aggregation rule is defined for '{variable}'")
        threshold = (
            total_min_completeness_percent if rule.statistic == "total" else mean_min_completeness_percent
        )
        subset = daily[daily["variable"] == variable]
        grouped = subset.groupby([subset["date"].dt.year, subset["date"].dt.month])["value"]
        for (year, month), values in grouped:
            days_expected = calendar.monthrange(int(year), int(month))[1]
            valid = values.dropna()
            completeness = 100.0 * len(valid) / days_expected
            reported = len(valid) > 0 and completeness >= threshold
            if not reported:
                value = float("nan")
            elif rule.statistic == "total":
                value = float(valid.sum())
            else:
                value = float(valid.mean())
            rows.append(
                (
                    int(year), int(month), variable, rule.statistic, value, rule.output_unit.value,
                    rule.output_variable, days_expected, len(valid), round(completeness, 2), reported,
                    rule.method,
                )
            )
    return pd.DataFrame(rows, columns=MONTHLY_COLUMNS)


def monthly_climatology(monthly: pd.DataFrame) -> pd.DataFrame:
    """Average of each calendar month across the years on record.

    Only reported months contribute. ``years_used`` shows how many did, so a
    thin average is visible as such.
    """
    rows = []
    for (variable, month), group in monthly.groupby(["variable", "month"], sort=True):
        reported = group[group["reported"]]
        values = reported["value"]
        rows.append(
            (
                variable,
                int(month),
                group["statistic"].iloc[0],
                float(values.mean()) if len(values) else float("nan"),
                float(values.min()) if len(values) else float("nan"),
                float(values.max()) if len(values) else float("nan"),
                group["unit"].iloc[0],
                int(len(values)),
                int(len(group)),
            )
        )
    return pd.DataFrame(rows, columns=CLIMATOLOGY_COLUMNS)


def quality_table(dataset: EnvironmentalDataset) -> pd.DataFrame:
    """Completeness and simple statistics for each variable, as a table."""
    return pd.DataFrame(
        [
            {
                "variable": item.variable,
                "nasa_parameter": item.power_parameter,
                "unit": item.unit.value,
                "kind": item.kind.value,
                "days_expected": item.expected_count,
                "days_valid": item.valid_count,
                "days_missing": item.missing_count,
                "suspect": item.suspect_count,
                "completeness_percent": item.completeness_percent,
                "first_valid": item.first_valid_date,
                "last_valid": item.last_valid_date,
                "minimum": item.minimum,
                "mean": item.mean,
                "maximum": item.maximum,
            }
            for item in dataset.quality.variables
        ]
    )
