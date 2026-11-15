"""Validation and normalisation of NASA POWER responses.

Responsibility
    Turn an original response into typed observations, a quality report and a
    provenance record, or refuse it with a clear reason.

Three levels of validation
    1. Structural: required sections, data types, date format, requested
       parameters present, no date supplied twice. A failure here is fatal;
       the response is rejected as a whole.
    2. Physical and unit: units must match what the parameter is documented
       to use. Each value is then classed as valid, missing, physically
       impossible (discarded and flagged) or merely unusual (kept and flagged
       as suspect).
    3. Completeness: how many of the expected days hold a valid value. A
       dataset is accepted only if every variable meets the configured
       minimum. A rejected dataset is still returned so the reason can be
       shown, but ``require_accepted`` stops it being used further.

What validation does not establish
    Passing these checks shows that the response is well formed, physically
    possible and complete. It does not show that the values are accurate for
    any particular farm.

Rules that never bend
    * A gap stays a gap. Nothing is interpolated, filled or set to zero.
    * No value is invented or repaired.

AI assistance: drafted with Claude Code (Anthropic). See docs/provenance.md.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from pydantic import Field

from src.models import (
    Contract,
    DatasetProvenance,
    EnvironmentalObservation,
    GeoLocation,
    MissingStatus,
    ObservationSeries,
    ProvenanceRecord,
    QualityFlag,
    TemporalResolution,
    Text,
    Unit,
    DataKind,
    get_variable,
)
from src.nasa_client import (
    COORDINATE_DECIMALS,
    DOCUMENTATION_URL,
    OFFICIAL_URL,
    POWER_PARAMETERS,
    SERVICE_NAME,
    NasaDataError,
    PowerParameter,
    PowerRetrieval,
)

SOURCE_ID = "nasa-power"

# --- Documented thresholds ---------------------------------------------------

DEFAULT_MIN_COMPLETENESS_PERCENT = 90.0
"""A variable must have valid values on at least this share of expected days."""

PLAUSIBLE_RANGES: dict[str, tuple[float | None, float | None]] = {
    "air_temperature_mean": (-70.0, 50.0),
    "air_temperature_max": (-65.0, 55.0),
    "air_temperature_min": (-80.0, 45.0),
    "precipitation": (None, 500.0),
    "solar_irradiance": (None, 40.0),
    "relative_humidity": (None, None),
}
"""Values outside these ranges are possible but unusual: kept, flagged suspect.

They are screening limits chosen by this project, deliberately wide. The hard
physical limits live in the variable registry (``src/models.py``); a value
outside those is discarded.
"""

LATENCY_WINDOW_DAYS = 180
"""Trailing gaps this close to the retrieval date are 'not yet available'."""

COORDINATE_TOLERANCE_DEGREES = 0.01
"""The response must echo the requested coordinates within this margin."""

TEMPERATURE_ORDER_TOLERANCE = 0.05
"""Allowed slack, in degC, when checking minimum <= mean <= maximum."""

MAX_PROBLEMS_REPORTED = 5


# --- Errors --------------------------------------------------------------------


class DataValidationError(NasaDataError):
    """A response failed validation."""


class StructuralValidationError(DataValidationError):
    """The response does not have the structure a POWER response must have."""


class UnitMismatchError(DataValidationError):
    """The response reports a unit other than the documented one."""


class DatasetRejectedError(DataValidationError):
    """The dataset is too incomplete to be used."""


# --- Report types --------------------------------------------------------------


class ValidationLevel(StrEnum):
    STRUCTURAL = "structural"
    PHYSICAL = "physical"
    COMPLETENESS = "completeness"
    SERVICE = "service"  # how the data was obtained (cache, fallback, and so on)


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationIssue(Contract):
    """One thing a user should know about the quality of a dataset."""

    level: ValidationLevel
    severity: IssueSeverity
    code: str
    message: Text
    variable: str | None = None
    count: int = Field(default=1, ge=1)


class VariableQuality(Contract):
    """Completeness and simple descriptive statistics for one variable."""

    variable: str
    power_parameter: str
    unit: Unit
    kind: DataKind
    expected_count: int
    valid_count: int
    missing_count: int = Field(description="Expected days without a valid value.")
    rejected_count: int = Field(description="Values discarded as impossible or non-numeric.")
    suspect_count: int = Field(description="Valid values flagged as unusual.")
    completeness_percent: float
    first_valid_date: date | None
    last_valid_date: date | None
    minimum: float | None
    maximum: float | None
    mean: float | None


class QualityReport(Contract):
    """The outcome of validating one dataset."""

    requested_start: date
    requested_end: date
    expected_days: int
    variables: tuple[VariableQuality, ...]
    issues: tuple[ValidationIssue, ...] = ()
    min_completeness_percent: float
    accepted: bool

    @property
    def lowest_completeness_percent(self) -> float:
        return min((item.completeness_percent for item in self.variables), default=0.0)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity is IssueSeverity.WARNING)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity is IssueSeverity.ERROR)


class EnvironmentalDataset(Contract):
    """Validated observations for one place and period, with their paperwork."""

    dataset_id: str = Field(description="Cache key of the request that produced it.")
    site_name: str | None = None
    location: GeoLocation
    series: tuple[ObservationSeries, ...]
    quality: QualityReport
    provenance: DatasetProvenance

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(item.variable for item in self.series)

    def get(self, variable: str) -> ObservationSeries | None:
        """Return the series for one variable, or ``None`` if it is absent."""
        return next((item for item in self.series if item.variable == variable), None)

    def require_accepted(self) -> "EnvironmentalDataset":
        """Return the dataset, or raise if it failed the completeness check."""
        if not self.quality.accepted:
            reasons = "; ".join(item.message for item in self.quality.errors) or "see quality report"
            raise DatasetRejectedError(f"dataset not accepted: {reasons}")
        return self


# --- Level 1: structure --------------------------------------------------------


@dataclass
class _Structure:
    fill_value: float
    returned_longitude: float
    returned_latitude: float
    returned_elevation: float | None
    api_version: str | None
    upstream: tuple[str, ...]
    messages: tuple[str, ...]
    values: dict[str, dict[date, Any]]
    issues: list[ValidationIssue] = field(default_factory=list)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_date_key(key: Any) -> date | None:
    if not isinstance(key, str) or len(key) != 8 or not key.isdigit():
        return None
    try:
        return date(int(key[:4]), int(key[4:6]), int(key[6:8]))
    except ValueError:
        return None


def check_structure(retrieval: PowerRetrieval) -> _Structure:
    """Level 1. Raise ``StructuralValidationError`` unless the response is well formed."""
    payload, request = retrieval.payload, retrieval.request
    problems: list[str] = []
    issues: list[ValidationIssue] = []

    properties = payload.get("properties")
    blocks = properties.get("parameter") if isinstance(properties, dict) else None
    header = payload.get("header")
    if not isinstance(blocks, dict):
        raise StructuralValidationError("the response has no 'properties.parameter' section")
    if not isinstance(header, dict):
        raise StructuralValidationError("the response has no 'header' section")

    fill_value = header.get("fill_value")
    if not _is_number(fill_value):
        problems.append("header.fill_value is missing or not a number")

    reported_standard = header.get("time_standard")
    if reported_standard != request.time_standard.value:
        problems.append(
            f"the response uses time standard {reported_standard!r}, "
            f"not the requested {request.time_standard.value!r}"
        )

    geometry = payload.get("geometry")
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    longitude = latitude = float("nan")
    elevation: float | None = None
    if (
        not isinstance(coordinates, list)
        or len(coordinates) < 2
        or not all(_is_number(item) for item in coordinates[:3])
    ):
        problems.append("geometry.coordinates is missing or malformed")
    else:
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        if len(coordinates) >= 3:
            elevation = float(coordinates[2])
        if (
            abs(longitude - request.longitude) > COORDINATE_TOLERANCE_DEGREES
            or abs(latitude - request.latitude) > COORDINATE_TOLERANCE_DEGREES
        ):
            problems.append("the response is for different coordinates than requested")

    metadata = payload.get("parameters")
    if not isinstance(metadata, dict):
        problems.append("the 'parameters' metadata section is missing")
        metadata = {}

    values: dict[str, dict[date, Any]] = {}
    for name in request.parameters:
        expected_unit = POWER_PARAMETERS[name].power_unit
        entry = metadata.get(name)
        reported_unit = entry.get("units") if isinstance(entry, dict) else None
        if reported_unit is None:
            problems.append(f"no unit is given for {name}")
        elif reported_unit != expected_unit:
            raise UnitMismatchError(
                f"{name} is reported in '{reported_unit}' but '{expected_unit}' is documented; "
                "refusing to guess a conversion"
            )

        block = blocks.get(name)
        if not isinstance(block, dict) or not block:
            problems.append(f"requested parameter {name} is missing from the response")
            continue
        parsed: dict[date, Any] = {}
        outside = 0
        for key, raw in block.items():
            day = _parse_date_key(key)
            if day is None:
                problems.append(f"{name} has an invalid date key {key!r:.30}")
                continue
            if day in parsed:
                problems.append(f"{name} gives {day.isoformat()} more than once")
                continue
            if day < request.start or day > request.end:
                outside += 1
                continue
            parsed[day] = raw
        values[name] = parsed
        if outside:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.STRUCTURAL,
                    severity=IssueSeverity.INFO,
                    code="dates_outside_request",
                    message=f"{outside} value(s) for {name} fell outside the requested dates and were ignored.",
                    variable=POWER_PARAMETERS[name].variable,
                    count=outside,
                )
            )

    unexpected = sorted(set(blocks) - set(request.parameters))
    if unexpected:
        issues.append(
            ValidationIssue(
                level=ValidationLevel.STRUCTURAL,
                severity=IssueSeverity.WARNING,
                code="unexpected_parameters",
                message=f"The response included parameters that were not requested and were ignored: {', '.join(unexpected)}.",
                count=len(unexpected),
            )
        )

    if problems:
        shown = "; ".join(problems[:MAX_PROBLEMS_REPORTED])
        extra = len(problems) - MAX_PROBLEMS_REPORTED
        raise StructuralValidationError(shown + (f" (and {extra} more)" if extra > 0 else ""))

    api = header.get("api")
    sources = header.get("sources")
    messages = payload.get("messages")
    return _Structure(
        fill_value=float(fill_value),
        returned_longitude=longitude,
        returned_latitude=latitude,
        returned_elevation=elevation,
        api_version=str(api.get("version")) if isinstance(api, dict) and api.get("version") else None,
        upstream=tuple(str(item) for item in sources) if isinstance(sources, list) else (),
        messages=tuple(str(item) for item in messages) if isinstance(messages, list) else (),
        values=values,
        issues=issues,
    )


# --- Level 2: values -----------------------------------------------------------


@dataclass
class _Cell:
    day: date
    value: float | None
    missing: MissingStatus
    quality: QualityFlag
    note: str | None = None
    code: str | None = None


def classify_value(raw: Any, *, fill_value: float, variable: str, day: date) -> _Cell:
    """Level 2. Decide what one source value is. Never alters a valid number."""
    definition = get_variable(variable)
    if raw is None:
        return _Cell(day, None, MissingStatus.MISSING_AT_SOURCE, QualityFlag.NOT_ASSESSED,
                     "Null in the source response.", "null_value")
    if not _is_number(raw):
        return _Cell(day, None, MissingStatus.REJECTED_BY_VALIDATION, QualityFlag.FAILED,
                     f"Non-numeric source value {str(raw)[:30]!r} discarded.", "non_numeric_value")
    number = float(raw)
    if not math.isfinite(number):
        return _Cell(day, None, MissingStatus.REJECTED_BY_VALIDATION, QualityFlag.FAILED,
                     "Non-finite source value discarded.", "non_numeric_value")
    if number == fill_value:
        return _Cell(day, None, MissingStatus.MISSING_AT_SOURCE, QualityFlag.NOT_ASSESSED,
                     None, "fill_value")
    low, high = definition.valid_min, definition.valid_max
    if (low is not None and number < low) or (high is not None and number > high):
        return _Cell(day, None, MissingStatus.REJECTED_BY_VALIDATION, QualityFlag.FAILED,
                     f"Source value {number:g} is physically impossible for {variable}; discarded.",
                     "impossible_value")
    plausible_low, plausible_high = PLAUSIBLE_RANGES.get(variable, (None, None))
    if (plausible_low is not None and number < plausible_low) or (
        plausible_high is not None and number > plausible_high
    ):
        return _Cell(day, number, MissingStatus.PRESENT, QualityFlag.SUSPECT,
                     f"Value {number:g} is unusual for {variable}; kept and flagged.",
                     "suspicious_value")
    return _Cell(day, number, MissingStatus.PRESENT, QualityFlag.PASSED)


def _expected_days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _classify_parameter(structure: _Structure, name: str, days: list[date], retrieval: PowerRetrieval) -> list[_Cell]:
    variable = POWER_PARAMETERS[name].variable
    source = structure.values[name]
    cells: list[_Cell] = []
    for day in days:
        if day in source:
            cells.append(classify_value(source[day], fill_value=structure.fill_value, variable=variable, day=day))
        else:
            cells.append(
                _Cell(day, None, MissingStatus.MISSING_AT_SOURCE, QualityFlag.NOT_ASSESSED,
                      "Date absent from the source response.", "missing_date")
            )
    # Trailing gaps close to the retrieval date are data that has not arrived yet.
    retrieved_on = retrieval.retrieved_at.date()
    for cell in reversed(cells):
        if cell.value is not None:
            break
        if cell.code in ("fill_value", "missing_date") and (retrieved_on - cell.day).days <= LATENCY_WINDOW_DAYS:
            cell.missing = MissingStatus.NOT_YET_AVAILABLE
            cell.code = "not_yet_available"
    return cells


def _check_temperature_order(cells: dict[str, list[_Cell]]) -> int:
    """Flag days where minimum <= mean <= maximum does not hold. Returns the count."""
    if not all(name in cells for name in ("T2M_MIN", "T2M", "T2M_MAX")):
        return 0
    flagged = 0
    for low, mean, high in zip(cells["T2M_MIN"], cells["T2M"], cells["T2M_MAX"]):
        if low.value is None or mean.value is None or high.value is None:
            continue
        slack = TEMPERATURE_ORDER_TOLERANCE
        if low.value - slack <= mean.value <= high.value + slack:
            continue
        flagged += 1
        for cell in (low, mean, high):
            cell.quality = QualityFlag.SUSPECT
            cell.note = "Daily minimum, mean and maximum temperature are out of order on this day."
    return flagged


_ISSUE_TEXT: dict[str, tuple[IssueSeverity, str]] = {
    "fill_value": (IssueSeverity.WARNING, "{count} day(s) of {parameter} hold the source's missing-value marker and are kept as gaps."),
    "null_value": (IssueSeverity.WARNING, "{count} day(s) of {parameter} are null in the source and are kept as gaps."),
    "missing_date": (IssueSeverity.WARNING, "{count} expected day(s) of {parameter} are absent from the response and are kept as gaps."),
    "not_yet_available": (IssueSeverity.INFO, "{count} recent day(s) of {parameter} are not yet available from the source."),
    "non_numeric_value": (IssueSeverity.ERROR, "{count} value(s) of {parameter} were not numbers and were discarded."),
    "impossible_value": (IssueSeverity.ERROR, "{count} value(s) of {parameter} were physically impossible and were discarded."),
    "suspicious_value": (IssueSeverity.WARNING, "{count} value(s) of {parameter} are unusual; they are kept and flagged as suspect."),
}


def _value_issues(name: str, cells: list[_Cell]) -> list[ValidationIssue]:
    counts = Counter(cell.code for cell in cells if cell.code)
    issues = []
    for code, count in sorted(counts.items()):
        severity, template = _ISSUE_TEXT[code]
        issues.append(
            ValidationIssue(
                level=ValidationLevel.PHYSICAL,
                severity=severity,
                code=code,
                message=template.format(count=count, parameter=name),
                variable=POWER_PARAMETERS[name].variable,
                count=count,
            )
        )
    return issues


# --- Level 3: completeness -------------------------------------------------------


def summarise_variable(parameter: PowerParameter, cells: list[_Cell]) -> VariableQuality:
    """Level 3. Count what is there and what is not, for one variable."""
    valid = [cell for cell in cells if cell.value is not None]
    numbers = [cell.value for cell in valid if cell.value is not None]
    expected = len(cells)
    return VariableQuality(
        variable=parameter.variable,
        power_parameter=parameter.name,
        unit=parameter.unit,
        kind=parameter.kind,
        expected_count=expected,
        valid_count=len(valid),
        missing_count=expected - len(valid),
        rejected_count=sum(1 for cell in cells if cell.missing is MissingStatus.REJECTED_BY_VALIDATION),
        suspect_count=sum(1 for cell in valid if cell.quality is QualityFlag.SUSPECT),
        completeness_percent=round(100.0 * len(valid) / expected, 2) if expected else 0.0,
        first_valid_date=valid[0].day if valid else None,
        last_valid_date=valid[-1].day if valid else None,
        minimum=min(numbers) if numbers else None,
        maximum=max(numbers) if numbers else None,
        mean=round(sum(numbers) / len(numbers), 4) if numbers else None,
    )


# --- Provenance ------------------------------------------------------------------

POWER_REFERENCE = (
    "The data was obtained from National Aeronautics and Space Administration (NASA) "
    "Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project "
    "funded through the NASA Earth Science Division."
)
MERRA2_REFERENCE = (
    "Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and "
    "Applications, Version 2 (MERRA-2). Journal of Climate, 30(14), 5419-5454. "
    "https://doi.org/10.1175/JCLI-D-16-0758.1"
)
SOLAR_REFERENCE = (
    "Solar values: NASA CERES SYN1deg, as described in the NASA POWER methodology "
    "documentation (https://power.larc.nasa.gov/docs/methodology/data/sources_fluxes/)."
)
NOT_ENDORSED = "CropShift RESILIENCE is an independent hackathon project and is not endorsed by NASA."
NEAR_REAL_TIME_PRODUCTS = frozenset({"GEOSIT", "FLASHFLUX"})

MISSING_DATA_TREATMENT = (
    "Gaps are kept as gaps. The source's missing-value marker and nulls become 'missing at "
    "source'; dates absent from the response become 'missing at source'; trailing gaps "
    f"within {LATENCY_WINDOW_DAYS} days of retrieval become 'not yet available'. Values that "
    "are not numbers or are physically impossible are discarded and flagged. Nothing is "
    "interpolated, filled or replaced with zero."
)


def power_data_reference(version: str | None, retrieved_on: date) -> str:
    """POWER's requested data reference: service, version and date accessed."""
    label = version or "version not reported"
    return f"The data was obtained from the POWER Project's Daily {label} version on {retrieved_on:%Y/%m/%d}."


def _value_provenance(parameter: PowerParameter, retrieval: PowerRetrieval, structure: _Structure) -> ProvenanceRecord:
    return ProvenanceRecord(
        kind=parameter.kind,
        source_id=SOURCE_ID,
        source_name=f"{SERVICE_NAME}: {parameter.product}",
        source_version=structure.api_version,
        citation=POWER_REFERENCE,
        url=retrieval.url,
        retrieved_at=retrieval.retrieved_at,
        spatial_resolution=parameter.spatial_resolution,
        temporal_resolution=TemporalResolution.DAILY,
        time_standard=retrieval.request.time_standard,
        transformations=(
            f"NASA POWER parameter {parameter.name}; unit label '{parameter.power_unit}' "
            f"recorded as '{parameter.unit.value}' with no change to the number.",
            "Missing-value markers replaced by an explicit missing status.",
        ),
    )


def _dataset_provenance(
    retrieval: PowerRetrieval,
    structure: _Structure,
    qualities: list[VariableQuality],
    location: GeoLocation,
) -> DatasetProvenance:
    request = retrieval.request
    parameters = [POWER_PARAMETERS[name] for name in request.parameters]
    firsts = [item.first_valid_date for item in qualities if item.first_valid_date]
    lasts = [item.last_valid_date for item in qualities if item.last_valid_date]
    grids = sorted({f"{item.spatial_resolution} for {item.product}" for item in parameters})
    citations = [POWER_REFERENCE, power_data_reference(structure.api_version, retrieval.retrieved_at.date())]
    if any(item.kind is DataKind.REANALYSIS for item in parameters):
        citations.append(MERRA2_REFERENCE)
    if any(item.kind is DataKind.SATELLITE_RETRIEVAL for item in parameters):
        citations.append(SOLAR_REFERENCE)
    caveats = [
        "Values are averages over NASA grid cells tens of kilometres wide, at each cell's "
        "average elevation. They are not measurements from an individual farm.",
        "MERRA-2 is a reanalysis: a weather model constrained by observations, not a direct "
        "measurement. Its precipitation is a bias-corrected model estimate.",
        "This is a historical record. It is not a forecast and not a projection of future climate.",
        NOT_ENDORSED,
    ]
    if NEAR_REAL_TIME_PRODUCTS & {item.upper() for item in structure.upstream}:
        caveats.insert(
            3,
            "Part of this period comes from near-real-time systems (GEOS-IT, FLASHFlux) "
            "and may be revised by NASA later.",
        )
    return DatasetProvenance(
        service_name=SERVICE_NAME,
        service_version=structure.api_version,
        official_url=OFFICIAL_URL,
        request_url=retrieval.url,
        request_parameters=request.query_params(),
        requested_location=location,
        returned_location=GeoLocation(
            latitude=structure.returned_latitude,
            longitude=structure.returned_longitude,
            elevation_m=structure.returned_elevation,
        ),
        requested_start=request.start,
        requested_end=request.end,
        returned_start=min(firsts) if firsts else None,
        returned_end=max(lasts) if lasts else None,
        retrieved_at=retrieval.retrieved_at,
        origin=retrieval.origin,
        payload_sha256=retrieval.payload_sha256,
        upstream_products=structure.upstream,
        temporal_resolution=TemporalResolution.DAILY,
        spatial_resolution="; ".join(grids),
        time_standard=request.time_standard,
        units={item.variable: item.unit for item in parameters},
        transformations=(
            f"Coordinates rounded to {COORDINATE_DECIMALS} decimal places before the request.",
            f"Requested with time standard {request.time_standard.value}; each daily value "
            "covers one day in that standard.",
            "Unit labels recorded in CropShift's notation with no change to any number "
            "(for example 'C' recorded as 'degC').",
            "Source missing-value markers replaced by explicit missing statuses.",
            "Physically impossible values discarded and flagged; unusual values kept and "
            "flagged as suspect.",
        ),
        missing_data_treatment=MISSING_DATA_TREATMENT,
        citations=tuple(citations),
        caveats=tuple(caveats),
        source_messages=structure.messages,
    )


# --- Entry point -------------------------------------------------------------------


def build_dataset(
    retrieval: PowerRetrieval,
    *,
    site_name: str | None = None,
    min_completeness_percent: float = DEFAULT_MIN_COMPLETENESS_PERCENT,
    service_issues: tuple[ValidationIssue, ...] = (),
) -> EnvironmentalDataset:
    """Validate a response at all three levels and return the typed dataset.

    Raises ``StructuralValidationError`` or ``UnitMismatchError`` for a response
    that cannot be trusted at all. A dataset that is merely incomplete is
    returned with ``quality.accepted`` set to False.
    """
    if not 0 <= min_completeness_percent <= 100:
        raise ValueError("min_completeness_percent must be between 0 and 100")

    request = retrieval.request
    structure = check_structure(retrieval)
    days = _expected_days(request.start, request.end)
    location = GeoLocation(latitude=request.latitude, longitude=request.longitude, name=site_name)

    cells = {name: _classify_parameter(structure, name, days, retrieval) for name in request.parameters}
    out_of_order = _check_temperature_order(cells)

    issues: list[ValidationIssue] = list(service_issues) + structure.issues
    if out_of_order:
        issues.append(
            ValidationIssue(
                level=ValidationLevel.PHYSICAL,
                severity=IssueSeverity.WARNING,
                code="temperature_order",
                message=f"On {out_of_order} day(s) the minimum, mean and maximum temperature are out of order; those values are flagged as suspect.",
                count=out_of_order,
            )
        )

    series: list[ObservationSeries] = []
    qualities: list[VariableQuality] = []
    for name in request.parameters:
        parameter = POWER_PARAMETERS[name]
        provenance = _value_provenance(parameter, retrieval, structure)
        observations = [
            EnvironmentalObservation(
                variable=parameter.variable,
                value=cell.value,
                unit=parameter.unit,
                missing=cell.missing,
                quality=cell.quality,
                quality_note=cell.note,
                provenance=provenance,
                location=location,
                period_start=cell.day,
                period_end=cell.day,
                temporal_resolution=TemporalResolution.DAILY,
            )
            for cell in cells[name]
        ]
        series.append(ObservationSeries(observations=observations))
        quality = summarise_variable(parameter, cells[name])
        qualities.append(quality)
        issues.extend(_value_issues(name, cells[name]))
        if quality.completeness_percent < min_completeness_percent:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.COMPLETENESS,
                    severity=IssueSeverity.ERROR,
                    code="completeness_below_threshold",
                    message=f"{name} is {quality.completeness_percent:g}% complete, below the required {min_completeness_percent:g}%.",
                    variable=parameter.variable,
                )
            )

    report = QualityReport(
        requested_start=request.start,
        requested_end=request.end,
        expected_days=len(days),
        variables=tuple(qualities),
        issues=tuple(issues),
        min_completeness_percent=min_completeness_percent,
        accepted=all(item.completeness_percent >= min_completeness_percent for item in qualities),
    )
    return EnvironmentalDataset(
        dataset_id=request.cache_key(),
        site_name=site_name,
        location=location,
        series=tuple(series),
        quality=report,
        provenance=_dataset_provenance(retrieval, structure, qualities, location),
    )
