"""Scientific data contracts for CropShift RESILIENCE.

Phase A1 defines the *shape* of every scientific value that later phases will
retrieve, calculate or display. Nothing in this module fetches data, performs
an agronomic calculation or contains a measured number.

Design rules that every contract follows:

* **One variable, one unit.** Each variable is declared once in a registry with
  a single canonical unit. Unit conversion happens at ingestion and is recorded
  as a transformation, so incompatible units can never be mixed downstream.
* **Missing is explicit.** A value is either a real number or ``None`` with a
  stated reason. Sentinel numbers such as -999 and NaN are rejected.
* **Every value carries its provenance.** What kind of evidence it is, where it
  came from, which version, when it was retrieved and how it was transformed.
* **Observed is never confused with modelled.** Satellite retrievals, model
  reanalysis, literature values, CropShift's own calculations and plain
  assumptions are different ``DataKind`` values and are checked where it
  matters.
* **Historical scenarios are not forecasts.** The contract cannot represent a
  scenario or an observation that lies in the future.

All models are immutable and reject unknown fields.

AI assistance: drafted with Claude Code (Anthropic) under the participant's
direction. See docs/provenance.md.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

# --------------------------------------------------------------------------- #
# Shared building blocks
# --------------------------------------------------------------------------- #

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_\-]*$", max_length=64)]
"""Lower-case identifier such as ``nasa-power`` or ``air_temperature_mean``."""

Text = Annotated[str, StringConstraints(min_length=1)]
"""Free text that must not be empty or whitespace only."""

_CLOCK_TOLERANCE = timedelta(minutes=5)
_DATE_TOLERANCE = timedelta(days=1)  # "today" differs by up to a day across time zones

TEXTURE_SUM_TOLERANCE_PERCENT = 2.0
"""Sand + silt + clay may differ from 100 % by this much (rounding in sources)."""

DEFAULT_DISCLAIMER = (
    "CropShift RESILIENCE supports exploration of crop-rotation options. It does not "
    "predict yields, prescribe inputs or replace farmer judgment and local "
    "agricultural expertise. Historical scenarios describe past conditions; they are "
    "not weather forecasts."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


class Contract(BaseModel):
    """Base class: immutable, strict about unknown fields, no NaN or infinity."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


# --------------------------------------------------------------------------- #
# Controlled vocabularies
# --------------------------------------------------------------------------- #


class Unit(StrEnum):
    """The only units a scientific value may use."""

    DEGREE_CELSIUS = "degC"
    MILLIMETRE = "mm"
    MILLIMETRE_PER_DAY = "mm/day"
    MILLIMETRE_PER_METRE = "mm/m"
    MEGAJOULE_PER_M2_PER_DAY = "MJ/m^2/day"
    PERCENT = "%"
    FRACTION = "fraction"  # dimensionless share from 0 to 1
    CUBIC_METRE_PER_CUBIC_METRE = "m^3/m^3"
    METRE_PER_SECOND = "m/s"
    METRE = "m"
    CENTIMETRE = "cm"
    DAY = "day"
    COUNT = "count"
    GRAM_PER_KILOGRAM = "g/kg"
    GRAM_PER_CUBIC_CENTIMETRE = "g/cm^3"
    PH = "pH"
    DIMENSIONLESS = "dimensionless"


class TemporalResolution(StrEnum):
    """The time span that one value represents."""

    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"
    ANNUAL = "annual"
    CLIMATOLOGY = "climatology"  # long-term average over many years
    STATIC = "static"  # does not vary in time (for example terrain)


class TimeStandard(StrEnum):
    """How a source defines the boundaries of a day."""

    UTC = "UTC"
    LOCAL_SOLAR_TIME = "LST"


class MissingStatus(StrEnum):
    """Why a value is present or absent. Absent values are always ``None``."""

    PRESENT = "present"
    MISSING_AT_SOURCE = "missing_at_source"  # the source returned its fill value
    NOT_YET_AVAILABLE = "not_yet_available"  # inside the source's latency window
    OUT_OF_COVERAGE = "out_of_coverage"  # outside the source's record or domain
    REJECTED_BY_VALIDATION = "rejected_by_validation"  # failed a quality check
    NOT_PROVIDED = "not_provided"  # the user or the reference did not supply it


class QualityFlag(StrEnum):
    """Outcome of quality checks applied to a value."""

    NOT_ASSESSED = "not_assessed"
    PASSED = "passed"
    SUSPECT = "suspect"
    FAILED = "failed"


class DataKind(StrEnum):
    """What kind of evidence a value is. Shown to the user next to the value."""

    SATELLITE_RETRIEVAL = "satellite_retrieval"  # estimated from satellite measurements
    REANALYSIS = "reanalysis"  # weather model constrained by observations
    GROUND_MEASUREMENT = "ground_measurement"  # measured in the field or by a station
    GRIDDED_MAP_PRODUCT = "gridded_map_product"  # interpolated or predicted map, e.g. soil maps
    USER_REPORTED = "user_reported"  # typed in or selected by the farmer
    LITERATURE_VALUE = "literature_value"  # published reference value
    DERIVED = "derived"  # calculated from the above by a documented formula
    MODELED = "modeled"  # output of CropShift's own scenario calculations
    ASSUMED = "assumed"  # a default chosen because nothing better was available


OBSERVATION_BASED_KINDS = frozenset(
    {DataKind.SATELLITE_RETRIEVAL, DataKind.REANALYSIS, DataKind.GROUND_MEASUREMENT}
)
"""Kinds that are retrieved from an external observing or reanalysis system."""

_ENVIRONMENT_KINDS = OBSERVATION_BASED_KINDS | {DataKind.DERIVED}
_INDICATOR_KINDS = frozenset({DataKind.MODELED, DataKind.DERIVED})


class EvidenceConfidence(StrEnum):
    """How firmly a cited source supports a claim. Words, not probabilities."""

    DIRECTLY_SUPPORTED = "directly_supported"  # the source states it for this crop or case
    CONTEXT_DEPENDENT = "context_dependent"  # stated, but for conditions that may not apply
    PROVISIONAL = "provisional"  # indirect, shared, ambiguous or interpreted from the source
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # no adequate source was found


class DataOrigin(StrEnum):
    """How a dataset reached the application on this occasion."""

    NETWORK = "network"  # requested from the source service just now
    CACHE = "cache"  # read from the local cache of an earlier request
    BUNDLED = "bundled"  # read from real responses shipped with the project


class VariableDomain(StrEnum):
    """Which part of the system a variable belongs to."""

    ENVIRONMENT = "environment"
    SOIL = "soil"
    CROP = "crop"
    INDICATOR = "indicator"


# --------------------------------------------------------------------------- #
# Variable registry: one variable, one unit, one set of physical limits
# --------------------------------------------------------------------------- #


class UnknownVariableError(ValueError):
    """Raised when a value names a variable that was never declared."""


class VariableDefinition(Contract):
    """Declares a variable: its unit and the limits no real value can exceed."""

    name: Slug
    domain: VariableDomain
    unit: Unit
    description: Text
    valid_min: float | None = None
    valid_max: float | None = None
    provisional: bool = Field(
        default=False,
        description="True while the definition awaits confirmation in a later phase.",
    )

    @model_validator(mode="after")
    def _check_limits(self) -> "VariableDefinition":
        if (
            self.valid_min is not None
            and self.valid_max is not None
            and self.valid_min > self.valid_max
        ):
            raise ValueError("valid_min must not be greater than valid_max")
        return self


_VARIABLES: dict[str, VariableDefinition] = {}


def register_variable(
    definition: VariableDefinition, *, replace: bool = False
) -> VariableDefinition:
    """Declare a variable. Later phases call this to add their own variables."""
    if definition.name in _VARIABLES and not replace:
        raise ValueError(f"variable '{definition.name}' is already registered")
    _VARIABLES[definition.name] = definition
    return definition


def unregister_variable(name: str) -> None:
    """Remove a variable declaration (used by tests to clean up)."""
    _VARIABLES.pop(name, None)


def get_variable(name: str) -> VariableDefinition:
    """Return a variable's definition or raise ``UnknownVariableError``."""
    try:
        return _VARIABLES[name]
    except KeyError:
        raise UnknownVariableError(
            f"unknown variable '{name}'; declare it with register_variable() first"
        ) from None


def registered_variables(domain: VariableDomain | None = None) -> tuple[VariableDefinition, ...]:
    """List declared variables, optionally for one domain, sorted by name."""
    items = sorted(_VARIABLES.values(), key=lambda definition: definition.name)
    return tuple(item for item in items if domain is None or item.domain is domain)


def _declare(
    name: str,
    domain: VariableDomain,
    unit: Unit,
    description: str,
    valid_min: float | None = None,
    valid_max: float | None = None,
    *,
    provisional: bool = False,
) -> None:
    register_variable(
        VariableDefinition(
            name=name,
            domain=domain,
            unit=unit,
            description=description,
            valid_min=valid_min,
            valid_max=valid_max,
            provisional=provisional,
        )
    )


_ENV, _SOIL, _CROP = VariableDomain.ENVIRONMENT, VariableDomain.SOIL, VariableDomain.CROP

# Environmental variables. Limits are physical impossibility bounds, not
# plausibility checks; plausibility screening belongs to data validation (A2).
_declare("air_temperature_mean", _ENV, Unit.DEGREE_CELSIUS, "Mean air temperature at 2 m", -90, 60)
_declare("air_temperature_max", _ENV, Unit.DEGREE_CELSIUS, "Maximum air temperature at 2 m", -90, 60)
_declare("air_temperature_min", _ENV, Unit.DEGREE_CELSIUS, "Minimum air temperature at 2 m", -90, 60)
_declare("precipitation", _ENV, Unit.MILLIMETRE_PER_DAY, "Precipitation rate at the surface", 0, 2000)
_declare(
    "precipitation_total",
    _ENV,
    Unit.MILLIMETRE,
    "Precipitation accumulated over a period longer than a day, such as a month",
    0,
    30000,
)
_declare(
    "solar_irradiance",
    _ENV,
    Unit.MEGAJOULE_PER_M2_PER_DAY,
    "All-sky shortwave irradiance reaching a horizontal surface",
    0,
    50,
)
_declare("relative_humidity", _ENV, Unit.PERCENT, "Relative humidity at 2 m", 0, 100)
_declare("wind_speed", _ENV, Unit.METRE_PER_SECOND, "Wind speed at 2 m", 0, 100)
_declare(
    "surface_soil_wetness",
    _ENV,
    Unit.FRACTION,
    "Wetness of the top 5 cm of soil: 0 is completely dry, 1 is saturated",
    0,
    1,
)
_declare(
    "root_zone_soil_wetness",
    _ENV,
    Unit.FRACTION,
    "Wetness of the root zone (about the top 1 m): 0 is completely dry, 1 is saturated",
    0,
    1,
)
_declare(
    "surface_soil_moisture",
    _ENV,
    Unit.CUBIC_METRE_PER_CUBIC_METRE,
    "Volumetric water content of the top 5 cm of soil",
    0,
    1,
    provisional=True,  # only needed if SMAP is added (stretch goal)
)
_declare(
    "reference_evapotranspiration",
    _ENV,
    Unit.MILLIMETRE_PER_DAY,
    "Reference crop evapotranspiration calculated from weather variables",
    0,
    30,
    provisional=True,  # method fixed in A2
)

# Soil variables.
_declare("soil_sand_content", _SOIL, Unit.PERCENT, "Sand share of the fine earth by mass", 0, 100)
_declare("soil_silt_content", _SOIL, Unit.PERCENT, "Silt share of the fine earth by mass", 0, 100)
_declare("soil_clay_content", _SOIL, Unit.PERCENT, "Clay share of the fine earth by mass", 0, 100)
_declare("soil_organic_carbon", _SOIL, Unit.GRAM_PER_KILOGRAM, "Soil organic carbon content", 0, 600)
_declare("soil_ph", _SOIL, Unit.PH, "Soil pH measured in water", 0, 14)
_declare("soil_bulk_density", _SOIL, Unit.GRAM_PER_CUBIC_CENTIMETRE, "Dry bulk density", 0, 2.7)
_declare(
    "soil_field_capacity",
    _SOIL,
    Unit.CUBIC_METRE_PER_CUBIC_METRE,
    "Volumetric water content at field capacity",
    0,
    1,
)
_declare(
    "soil_wilting_point",
    _SOIL,
    Unit.CUBIC_METRE_PER_CUBIC_METRE,
    "Volumetric water content at the permanent wilting point",
    0,
    1,
)
_declare(
    "soil_available_water_capacity",
    _SOIL,
    Unit.MILLIMETRE_PER_METRE,
    "Plant-available water the soil can hold per metre of depth",
    0,
    500,
)

# Crop parameters, fixed in phase A3. Each is a quantity that the cited sources
# in the knowledge base actually report; see docs/agronomic_knowledge.md.
_declare("crop_cycle_length", _CROP, Unit.DAY, "Days from sowing to harvest", 1, 730)
_declare("crop_max_rooting_depth", _CROP, Unit.METRE, "Maximum effective rooting depth", 0, 10)
_declare("crop_max_height", _CROP, Unit.METRE, "Mean maximum plant height", 0, 10)
_declare(
    "crop_coefficient_initial",
    _CROP,
    Unit.DIMENSIONLESS,
    "Ratio of crop to reference evapotranspiration in the initial growth stage",
    0,
    2,
)
_declare(
    "crop_coefficient_mid_season",
    _CROP,
    Unit.DIMENSIONLESS,
    "Ratio of crop to reference evapotranspiration at mid-season",
    0,
    2,
)
_declare(
    "crop_coefficient_end_season",
    _CROP,
    Unit.DIMENSIONLESS,
    "Ratio of crop to reference evapotranspiration at the end of the late season",
    0,
    2,
)
_declare(
    "crop_depletion_fraction",
    _CROP,
    Unit.FRACTION,
    "Share of available soil water a crop can use before water stress begins",
    0,
    1,
)
_declare(
    "crop_yield_response_factor",
    _CROP,
    Unit.DIMENSIONLESS,
    "Relative yield loss per unit of relative evapotranspiration deficit over the season",
    0,
    3,
)
_declare(
    "crop_seasonal_water_requirement",
    _CROP,
    Unit.MILLIMETRE,
    "Crop evapotranspiration over one growing period (water use, not rainfall needed)",
    0,
    5000,
)
_declare(
    "crop_temperature_requirement",
    _CROP,
    Unit.DEGREE_CELSIUS,
    "Air temperature a source associates with the crop; its basis is stated per record",
    -10,
    60,
)
_declare(
    "crop_annual_rainfall_requirement",
    _CROP,
    Unit.MILLIMETRE,
    "Annual rainfall of areas a source associates with the crop (mm per year)",
    0,
    10000,
)
_declare(
    "crop_soil_ph_requirement",
    _CROP,
    Unit.PH,
    "Soil pH a source associates with the crop",
    0,
    14,
)

# Indicator variables are declared by the scenario engine in phase A4.


# --------------------------------------------------------------------------- #
# 1. Geographic location
# --------------------------------------------------------------------------- #


class GeoLocation(Contract):
    """A point on Earth in WGS 84 decimal degrees."""

    latitude: float = Field(ge=-90, le=90, description="Degrees north; south is negative.")
    longitude: float = Field(ge=-180, le=180, description="Degrees east; west is negative.")
    elevation_m: float | None = Field(default=None, ge=-500, le=9000)
    name: Text | None = None
    country_code: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")] | None = Field(
        default=None, description="ISO 3166-1 alpha-2 country code."
    )
    coordinate_reference: Literal["EPSG:4326"] = "EPSG:4326"


# --------------------------------------------------------------------------- #
# 12. Provenance record (defined early because most contracts embed it)
# --------------------------------------------------------------------------- #


class ProvenanceRecord(Contract):
    """Where a value came from and what was done to it."""

    kind: DataKind
    source_id: Slug = Field(description="Identifier of the data source, reference or engine.")
    source_name: Text
    source_version: Text | None = None
    citation: Text | None = None
    url: Text | None = None
    retrieved_at: AwareDatetime | None = Field(
        default=None, description="When the value was retrieved, with time zone."
    )
    spatial_resolution: Text | None = Field(default=None, description="For example '0.5° x 0.625°'.")
    temporal_resolution: TemporalResolution | None = None
    time_standard: TimeStandard | None = None
    transformations: tuple[Text, ...] = Field(
        default=(), description="Ordered steps applied after retrieval, in plain words."
    )
    assumption: Text | None = Field(default=None, description="The assumption made, if any.")
    locator: Text | None = Field(
        default=None, description="Where in the source: chapter, table, section or page."
    )
    confidence: EvidenceConfidence | None = Field(
        default=None, description="How firmly the source supports this particular claim."
    )
    applicability: Text | None = Field(
        default=None, description="Crops, regions or conditions the source statement covers."
    )

    @model_validator(mode="after")
    def _check_evidence_is_documented(self) -> "ProvenanceRecord":
        if self.retrieved_at is not None and self.retrieved_at > _now() + _CLOCK_TOLERANCE:
            raise ValueError("retrieved_at cannot be in the future")
        if self.kind in OBSERVATION_BASED_KINDS or self.kind is DataKind.GRIDDED_MAP_PRODUCT:
            if self.retrieved_at is None:
                raise ValueError(f"{self.kind.value} values need a retrieval timestamp")
            if self.citation is None:
                raise ValueError(f"{self.kind.value} values need a citation")
        if self.kind is DataKind.LITERATURE_VALUE and self.citation is None:
            raise ValueError("literature values need a citation")
        if self.kind is DataKind.ASSUMED and self.assumption is None:
            raise ValueError("assumed values must state the assumption")
        if self.kind in (DataKind.DERIVED, DataKind.MODELED) and not self.transformations:
            raise ValueError(f"{self.kind.value} values must describe how they were calculated")
        return self

    @property
    def is_observation_based(self) -> bool:
        """True for satellite retrievals, reanalysis and ground measurements."""
        return self.kind in OBSERVATION_BASED_KINDS


class DatasetProvenance(Contract):
    """The full record of one retrieved dataset, kept with the data.

    ``ProvenanceRecord`` travels with each value. This record describes the
    retrieval as a whole so that it can be shown, exported and re-checked.
    """

    service_name: Text
    service_version: Text | None = None
    official_url: Text
    request_url: Text
    request_parameters: dict[str, str]
    requested_location: GeoLocation
    returned_location: GeoLocation = Field(
        description="Coordinates and grid-cell elevation echoed by the service."
    )
    requested_start: date
    requested_end: date
    returned_start: date | None = Field(description="First day with any valid value.")
    returned_end: date | None = Field(description="Last day with any valid value.")
    retrieved_at: AwareDatetime
    origin: DataOrigin
    payload_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] = Field(
        description="Fingerprint of the original response, to verify it was not altered."
    )
    upstream_products: tuple[Text, ...] = Field(
        default=(), description="Systems the service says supplied the values."
    )
    temporal_resolution: TemporalResolution
    spatial_resolution: Text
    time_standard: TimeStandard
    units: dict[str, Unit] = Field(description="Unit of each variable after normalisation.")
    transformations: tuple[Text, ...] = ()
    missing_data_treatment: Text
    citations: tuple[Text, ...] = Field(min_length=1)
    caveats: tuple[Text, ...] = Field(min_length=1)
    source_messages: tuple[str, ...] = Field(
        default=(), description="Messages the service returned with the data."
    )

    @model_validator(mode="after")
    def _check_dataset_provenance(self) -> "DatasetProvenance":
        if self.requested_end < self.requested_start:
            raise ValueError("requested_end must not be before requested_start")
        if (self.returned_start is None) != (self.returned_end is None):
            raise ValueError("give both returned_start and returned_end, or neither")
        if self.retrieved_at > _now() + _CLOCK_TOLERANCE:
            raise ValueError("retrieved_at cannot be in the future")
        for name in self.units:
            get_variable(name)
        return self


# --------------------------------------------------------------------------- #
# 2. NASA data source metadata
# --------------------------------------------------------------------------- #


class DataSourceMetadata(Contract):
    """Describes a data source so that every value can cite it consistently."""

    source_id: Slug
    name: Text
    provider: Text
    kind: DataKind
    version: Text | None = None
    description: Text
    url: Text
    citation: Text
    license: Text
    spatial_resolution: Text
    spatial_coverage: Text
    temporal_resolution: TemporalResolution
    time_standard: TimeStandard | None = None
    coverage_start: date
    coverage_end: date | None = Field(default=None, description="None means the record is ongoing.")
    latency: Text = Field(description="Typical delay before new data appears.")
    access_method: Text
    requires_authentication: bool
    variables: tuple[Slug, ...] = Field(default=(), description="Registered variables it supplies.")
    verified_on: date | None = Field(
        default=None, description="Date these facts were last checked against the source."
    )

    @model_validator(mode="after")
    def _check_source(self) -> "DataSourceMetadata":
        if self.coverage_end is not None and self.coverage_end < self.coverage_start:
            raise ValueError("coverage_end must not be before coverage_start")
        if self.coverage_start > _today() + _DATE_TOLERANCE:
            raise ValueError("coverage_start cannot be in the future")
        for name in self.variables:
            get_variable(name)
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("variables must not repeat")
        return self


# --------------------------------------------------------------------------- #
# Scientific value: the common core of observations, soil and crop properties
# --------------------------------------------------------------------------- #


class ScientificValue(Contract):
    """One number (or an explicit gap) with its unit, quality and provenance."""

    variable: Slug
    value: float | None
    unit: Unit
    missing: MissingStatus = MissingStatus.PRESENT
    quality: QualityFlag = QualityFlag.NOT_ASSESSED
    quality_note: Text | None = None
    provenance: ProvenanceRecord

    @model_validator(mode="after")
    def _check_against_registry(self) -> "ScientificValue":
        definition = get_variable(self.variable)
        if self.unit is not definition.unit:
            raise ValueError(
                f"'{self.variable}' must use unit '{definition.unit.value}', "
                f"not '{self.unit.value}'; convert at ingestion and record the conversion"
            )
        if self.missing is MissingStatus.PRESENT:
            if self.value is None:
                raise ValueError(
                    "a value marked 'present' needs a number; "
                    "use an explicit missing status for gaps"
                )
            if definition.valid_min is not None and self.value < definition.valid_min:
                raise ValueError(
                    f"{self.value} is below the physical minimum "
                    f"{definition.valid_min} for '{self.variable}'"
                )
            if definition.valid_max is not None and self.value > definition.valid_max:
                raise ValueError(
                    f"{self.value} is above the physical maximum "
                    f"{definition.valid_max} for '{self.variable}'"
                )
        elif self.value is not None:
            raise ValueError("a value flagged as missing must not carry a number")
        return self

    @property
    def is_missing(self) -> bool:
        return self.missing is not MissingStatus.PRESENT

    @property
    def domain(self) -> VariableDomain:
        return get_variable(self.variable).domain


def _require_domain(values: tuple[ScientificValue, ...], domain: VariableDomain, owner: str) -> None:
    for item in values:
        if item.domain is not domain:
            raise ValueError(f"'{item.variable}' is not a {domain.value} variable and cannot be stored in {owner}")


def _require_unique(names: tuple[str, ...] | list[str], what: str) -> None:
    if len(set(names)) != len(names):
        raise ValueError(f"{what} must not repeat")


# --------------------------------------------------------------------------- #
# 3. Environmental observation
# --------------------------------------------------------------------------- #


class EnvironmentalObservation(ScientificValue):
    """An environmental value for one place and one period in the past."""

    location: GeoLocation
    period_start: date
    period_end: date = Field(description="Last day covered, inclusive.")
    temporal_resolution: TemporalResolution

    @model_validator(mode="after")
    def _check_observation(self) -> "EnvironmentalObservation":
        if self.domain is not VariableDomain.ENVIRONMENT:
            raise ValueError(f"'{self.variable}' is not an environmental variable")
        if self.provenance.kind not in _ENVIRONMENT_KINDS:
            raise ValueError(
                "an environmental observation must be a satellite retrieval, reanalysis, "
                "ground measurement or a value derived from them, "
                f"not '{self.provenance.kind.value}'"
            )
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        if self.temporal_resolution is TemporalResolution.DAILY and self.period_end != self.period_start:
            raise ValueError("a daily observation must start and end on the same day")
        if self.period_end > _today() + _DATE_TOLERANCE:
            raise ValueError("observations cannot lie in the future; this tool does not forecast")
        return self


class ObservationSeries(Contract):
    """A time series that is guaranteed not to mix variables, units or resolutions."""

    observations: tuple[EnvironmentalObservation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_homogeneous(self) -> "ObservationSeries":
        first = self.observations[0]
        for item in self.observations[1:]:
            if item.variable != first.variable:
                raise ValueError("a series cannot mix variables")
            if item.temporal_resolution is not first.temporal_resolution:
                raise ValueError("a series cannot mix temporal resolutions")
            if item.location != first.location:
                raise ValueError("a series cannot mix locations")
            if item.provenance.source_id != first.provenance.source_id:
                raise ValueError("a series cannot mix data sources")
            if item.provenance.time_standard is not first.provenance.time_standard:
                raise ValueError("a series cannot mix time standards (UTC and local solar time)")
        for earlier, later in zip(self.observations, self.observations[1:]):
            if later.period_start <= earlier.period_end:
                raise ValueError("observations must be in chronological order without overlap")
        return self

    @property
    def variable(self) -> str:
        return self.observations[0].variable

    @property
    def unit(self) -> Unit:
        return self.observations[0].unit

    @property
    def missing_count(self) -> int:
        return sum(1 for item in self.observations if item.is_missing)


# --------------------------------------------------------------------------- #
# 4. Soil information
# --------------------------------------------------------------------------- #


class SoilTextureClass(StrEnum):
    """The twelve USDA soil texture classes."""

    SAND = "sand"
    LOAMY_SAND = "loamy_sand"
    SANDY_LOAM = "sandy_loam"
    LOAM = "loam"
    SILT_LOAM = "silt_loam"
    SILT = "silt"
    SANDY_CLAY_LOAM = "sandy_clay_loam"
    CLAY_LOAM = "clay_loam"
    SILTY_CLAY_LOAM = "silty_clay_loam"
    SANDY_CLAY = "sandy_clay"
    SILTY_CLAY = "silty_clay"
    CLAY = "clay"


class SoilDrainageClass(StrEnum):
    """How readily water leaves the soil. A simple input vocabulary chosen by
    this project for the user to describe a field; it is not a survey standard."""

    WELL_DRAINED = "well_drained"
    MODERATELY_DRAINED = "moderately_drained"
    POORLY_DRAINED = "poorly_drained"


class SoilEvidenceCategory(StrEnum):
    """Where a piece of soil information comes from. Never interchangeable."""

    MEASURED_LOCALLY = "measured_locally"  # A: measured in this field
    MAPPED_ESTIMATE = "mapped_estimate"  # B: read from an authoritative soil map
    USER_ENTERED = "user_entered"  # C: stated by the user, not measured here
    DEMONSTRATION_ASSUMPTION = "demonstration_assumption"  # D: assumed for a demo
    REFERENCE_VALUE = "reference_value"  # typical value for a soil type, from literature
    DERIVED = "derived"  # calculated from other soil values by a stated formula


_SOIL_CATEGORY_BY_KIND = {
    DataKind.GROUND_MEASUREMENT: SoilEvidenceCategory.MEASURED_LOCALLY,
    DataKind.GRIDDED_MAP_PRODUCT: SoilEvidenceCategory.MAPPED_ESTIMATE,
    DataKind.USER_REPORTED: SoilEvidenceCategory.USER_ENTERED,
    DataKind.ASSUMED: SoilEvidenceCategory.DEMONSTRATION_ASSUMPTION,
    DataKind.LITERATURE_VALUE: SoilEvidenceCategory.REFERENCE_VALUE,
    DataKind.DERIVED: SoilEvidenceCategory.DERIVED,
}
"""Kinds of evidence that may describe a soil. Satellite retrievals, reanalysis
and model output are deliberately absent: soil properties are never inferred
from NASA weather data."""


def soil_evidence_category(provenance: ProvenanceRecord) -> SoilEvidenceCategory:
    """Classify a soil value's provenance, or refuse a kind that cannot describe soil."""
    try:
        return _SOIL_CATEGORY_BY_KIND[provenance.kind]
    except KeyError:
        raise ValueError(
            f"soil information cannot come from '{provenance.kind.value}' data; "
            "soil properties are never inferred from weather or model output"
        ) from None


class SoilInformation(Contract):
    """Documented soil properties for one place and one depth interval."""

    location: GeoLocation
    depth_top_cm: float = Field(ge=0, le=2000)
    depth_bottom_cm: float = Field(gt=0, le=2000)
    texture_class: SoilTextureClass | None = None
    texture_provenance: ProvenanceRecord | None = None
    drainage_class: SoilDrainageClass | None = None
    drainage_provenance: ProvenanceRecord | None = None
    properties: tuple[ScientificValue, ...] = ()
    notes: Text | None = None

    @model_validator(mode="after")
    def _check_soil(self) -> "SoilInformation":
        if self.depth_bottom_cm <= self.depth_top_cm:
            raise ValueError("depth_bottom_cm must be greater than depth_top_cm")
        if self.texture_class is not None and self.texture_provenance is None:
            raise ValueError("a texture class needs provenance: who or what supplied it")
        if self.drainage_class is not None and self.drainage_provenance is None:
            raise ValueError("a drainage class needs provenance: who or what supplied it")
        _require_domain(self.properties, VariableDomain.SOIL, "soil information")
        _require_unique([item.variable for item in self.properties], "soil properties")
        for record in self._all_provenance():
            soil_evidence_category(record)

        fractions = [self.get(name) for name in ("soil_sand_content", "soil_silt_content", "soil_clay_content")]
        if all(item is not None and item.value is not None for item in fractions):
            total = sum(item.value for item in fractions)  # type: ignore[union-attr]
            if abs(total - 100.0) > TEXTURE_SUM_TOLERANCE_PERCENT:
                raise ValueError(f"sand + silt + clay must total 100 % (got {total:g} %)")

        capacity, wilting = self.get("soil_field_capacity"), self.get("soil_wilting_point")
        if (
            capacity is not None
            and wilting is not None
            and capacity.value is not None
            and wilting.value is not None
            and capacity.value <= wilting.value
        ):
            raise ValueError("field capacity must be greater than the wilting point")
        return self

    def get(self, variable: str) -> ScientificValue | None:
        """Return one soil property, or ``None`` if it was not supplied."""
        return next((item for item in self.properties if item.variable == variable), None)

    def _all_provenance(self) -> tuple[ProvenanceRecord, ...]:
        extra = [item for item in (self.texture_provenance, self.drainage_provenance) if item]
        return tuple(item.provenance for item in self.properties) + tuple(extra)

    def evidence_categories(self) -> dict[str, SoilEvidenceCategory]:
        """Say, item by item, what kind of soil information this is.

        Keys are variable names plus ``texture_class`` and ``drainage_class``.
        Measured, mapped, user-entered and assumed values stay distinguishable.
        """
        categories = {
            item.variable: soil_evidence_category(item.provenance) for item in self.properties
        }
        if self.texture_provenance is not None:
            categories["texture_class"] = soil_evidence_category(self.texture_provenance)
        if self.drainage_provenance is not None:
            categories["drainage_class"] = soil_evidence_category(self.drainage_provenance)
        return categories

    def unmeasured(self) -> tuple[str, ...]:
        """Items that are not local measurements, so a user can see what is unverified."""
        return tuple(
            name
            for name, category in self.evidence_categories().items()
            if category is not SoilEvidenceCategory.MEASURED_LOCALLY
        )


# --------------------------------------------------------------------------- #
# 5. Crop profile
# --------------------------------------------------------------------------- #


class CropFunctionalGroup(StrEnum):
    """Broad agronomic role of a crop within a rotation."""

    CEREAL = "cereal"
    LEGUME = "legume"
    OILSEED = "oilseed"
    ROOT_OR_TUBER = "root_or_tuber"
    BRASSICA = "brassica"
    FORAGE = "forage"
    COVER_CROP = "cover_crop"
    FIBRE = "fibre"
    VEGETABLE = "vegetable"
    OTHER = "other"


class CropLifeCycle(StrEnum):
    ANNUAL = "annual"
    SHORT_LIVED_PERENNIAL = "short_lived_perennial"
    PERENNIAL = "perennial"


class RequirementBasis(StrEnum):
    """What kind of threshold a requirement is. These are not interchangeable."""

    OPTIMAL = "optimal"  # the source calls it optimal or best
    SUITABLE = "suitable"  # conditions under which the source says the crop grows
    TOLERATED = "tolerated"  # outer limits: the crop withstands it, or growth stops beyond it
    STAGE_SPECIFIC = "stage_specific"  # applies to one named development stage
    TYPICAL = "typical"  # a typical value under the source's standard conditions


class KnowledgeStatus(StrEnum):
    """How far a knowledge-base record can be relied on."""

    REVIEWED = "reviewed"  # every value traced to a source that was read
    PROVISIONAL = "provisional"  # traced to sources, but not confirmed for the pilot region
    INCOMPLETE = "incomplete"  # important attributes are unknown


class Explanation(Contract):
    """A reviewable, plain-language explanation in five fixed parts."""

    what_is_known: Text
    why_it_matters: Text
    evidence_summary: Text
    what_is_uncertain: Text
    region_specific: bool = Field(description="True if the evidence is specific to a region.")
    region_note: Text | None = None

    @model_validator(mode="after")
    def _check_region(self) -> "Explanation":
        if self.region_specific and self.region_note is None:
            raise ValueError("a region-specific explanation must name the region")
        return self


def _require_cited(record: ProvenanceRecord, what: str) -> None:
    """Knowledge-base claims need a citation, a place in the source and a confidence."""
    if record.citation is None:
        raise ValueError(f"{what} needs a cited source")
    if record.locator is None:
        raise ValueError(f"{what} must say where in the source it is found")
    if record.confidence is None:
        raise ValueError(f"{what} needs a confidence classification")


class CropRequirement(Contract):
    """One sourced range or value for a crop, with the kind of threshold it is."""

    requirement_id: Slug
    variable: Slug
    minimum: float | None = None
    maximum: float | None = None
    unit: Unit
    basis: RequirementBasis
    growth_stage: Text | None = None
    statement: Text = Field(description="What the source says, kept close to its wording.")
    original_unit: Text | None = None
    limitation: Text = Field(description="What this value does not tell you.")
    provenance: ProvenanceRecord

    @model_validator(mode="after")
    def _check_requirement(self) -> "CropRequirement":
        definition = get_variable(self.variable)
        if definition.domain is not VariableDomain.CROP:
            raise ValueError(f"'{self.variable}' is not a crop variable")
        if self.unit is not definition.unit:
            raise ValueError(
                f"'{self.variable}' must use unit '{definition.unit.value}', not '{self.unit.value}'"
            )
        if self.minimum is None and self.maximum is None:
            raise ValueError("a requirement needs a minimum, a maximum or both; use an unknown entry otherwise")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not be greater than maximum")
        for number in (self.minimum, self.maximum):
            if number is None:
                continue
            if definition.valid_min is not None and number < definition.valid_min:
                raise ValueError(f"{number} is below the physical minimum for '{self.variable}'")
            if definition.valid_max is not None and number > definition.valid_max:
                raise ValueError(f"{number} is above the physical maximum for '{self.variable}'")
        if self.basis is RequirementBasis.STAGE_SPECIFIC and self.growth_stage is None:
            raise ValueError("a stage-specific requirement must name the growth stage")
        _require_cited(self.provenance, f"requirement '{self.requirement_id}'")
        return self

    @property
    def is_single_value(self) -> bool:
        return self.minimum is not None and self.minimum == self.maximum


class QualitativeAttribute(Contract):
    """A sourced statement about a crop that is not a number."""

    attribute: Slug = Field(description="For example 'waterlogging', 'drainage' or 'drought'.")
    statement: Text
    provenance: ProvenanceRecord

    @model_validator(mode="after")
    def _check_attribute(self) -> "QualitativeAttribute":
        _require_cited(self.provenance, f"attribute '{self.attribute}'")
        return self


class UnknownAttribute(Contract):
    """Something the sources read do not establish. Recorded so it is never guessed."""

    attribute: Slug
    reason: Text


class CropProfile(Contract):
    """Cited characteristics of one crop.

    ``requirements`` and ``attributes`` hold what is broadly true of the
    species. ``regional_evidence`` holds what a source reports for a named
    region. Cultivar-specific values are not stored at all.
    """

    crop_id: Slug
    common_name: Text
    scientific_name: Text | None = None
    botanical_family: Text = Field(description="Used to reason about pest and disease breaks.")
    functional_group: CropFunctionalGroup
    nitrogen_fixing: bool
    properties: tuple[ScientificValue, ...] = ()
    sources: tuple[ProvenanceRecord, ...] = Field(
        min_length=1, description="Evidence for the descriptive attributes above."
    )
    notes: Text | None = None

    # --- Added in phase A3; all optional so earlier uses keep working ----------
    life_cycle: CropLifeCycle | None = None
    life_cycle_basis: Text | None = Field(
        default=None, description="Whether the source states the life cycle or it was inferred."
    )
    requirements: tuple[CropRequirement, ...] = ()
    attributes: tuple[QualitativeAttribute, ...] = ()
    regional_evidence: tuple[QualitativeAttribute, ...] = Field(
        default=(), description="What a source reports for a named region."
    )
    unknowns: tuple[UnknownAttribute, ...] = ()
    assumptions: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ()
    data_quality: KnowledgeStatus = KnowledgeStatus.INCOMPLETE
    explanation: Explanation | None = None

    @model_validator(mode="after")
    def _check_crop(self) -> "CropProfile":
        _require_domain(self.properties, VariableDomain.CROP, "a crop profile")
        _require_unique([item.variable for item in self.properties], "crop properties")
        _require_unique([item.requirement_id for item in self.requirements], "requirement identifiers")
        _require_unique([item.attribute for item in self.unknowns], "unknown attributes")
        if self.life_cycle is not None and self.life_cycle_basis is None:
            raise ValueError("a life cycle needs its basis: stated by a source, or inferred and how")
        return self

    def get(self, variable: str) -> ScientificValue | None:
        """Return one crop parameter, or ``None`` if it is not documented."""
        return next((item for item in self.properties if item.variable == variable), None)

    def requirements_for(
        self, variable: str, basis: RequirementBasis | None = None
    ) -> tuple[CropRequirement, ...]:
        """All sourced requirements for one variable, optionally of one kind."""
        return tuple(
            item
            for item in self.requirements
            if item.variable == variable and (basis is None or item.basis is basis)
        )

    def is_unknown(self, attribute: str) -> bool:
        """True if the knowledge base records that this attribute is not established."""
        return any(item.attribute == attribute for item in self.unknowns)


# --------------------------------------------------------------------------- #
# 6. Crop rotation
# --------------------------------------------------------------------------- #


class RotationRole(StrEnum):
    """Whether a rotation is what the farmer does now or an option to explore."""

    CURRENT_PRACTICE = "current_practice"
    ALTERNATIVE = "alternative"


class RotationStep(Contract):
    """One slot in a rotation: a crop, or a fallow period when no crop is named."""

    position: int = Field(ge=1, description="Order within the cycle, starting at 1.")
    crop_id: Slug | None = Field(default=None, description="None means the field is fallow.")
    season_label: Text | None = Field(default=None, description="For example 'long rains'.")
    planting_month: int | None = Field(default=None, ge=1, le=12)
    harvest_month: int | None = Field(default=None, ge=1, le=12)

    @property
    def is_fallow(self) -> bool:
        return self.crop_id is None


class CropRotation(Contract):
    """An ordered, repeating sequence of crops and fallow periods."""

    rotation_id: Slug
    name: Text
    role: RotationRole
    steps: tuple[RotationStep, ...] = Field(min_length=1)
    cycle_years: float = Field(gt=0, le=20, description="Years to complete one full cycle.")
    description: Text | None = None

    @model_validator(mode="after")
    def _check_rotation(self) -> "CropRotation":
        positions = [step.position for step in self.steps]
        if positions != list(range(1, len(positions) + 1)):
            raise ValueError("step positions must run 1, 2, 3, ... in order without gaps")
        if all(step.is_fallow for step in self.steps):
            raise ValueError("a rotation needs at least one crop")
        return self

    @property
    def crop_ids(self) -> tuple[str, ...]:
        """Crops in order of appearance, without fallow periods."""
        return tuple(step.crop_id for step in self.steps if step.crop_id is not None)

    @property
    def distinct_crop_count(self) -> int:
        return len(set(self.crop_ids))

    @property
    def is_monoculture(self) -> bool:
        return self.distinct_crop_count == 1

    @property
    def includes_fallow(self) -> bool:
        return any(step.is_fallow for step in self.steps)


# --------------------------------------------------------------------------- #
# 7. Historical scenario
# --------------------------------------------------------------------------- #


class ScenarioCategory(StrEnum):
    """How a past period ranks against the long-term record."""

    DRY = "dry"
    TYPICAL = "typical"
    WET = "wet"


class HistoricalScenario(Contract):
    """A real period from the historical record, used to stress-test rotations.

    A scenario is always in the past. ``is_forecast`` is fixed to ``False`` so
    that no code path can present a scenario as a prediction.
    """

    scenario_id: Slug
    category: ScenarioCategory
    label: Text
    location: GeoLocation
    period_start: date
    period_end: date
    baseline_start: date
    baseline_end: date
    classification_variable: Slug = Field(description="Environmental variable used to rank the period.")
    classification_method: Text = Field(description="How dry, typical and wet were defined.")
    percentile_rank: float | None = Field(
        default=None, ge=0, le=100, description="Rank of the period within the baseline."
    )
    source_ids: tuple[Slug, ...] = Field(min_length=1)
    limitations: tuple[Text, ...] = ()
    is_forecast: Literal[False] = False

    @model_validator(mode="after")
    def _check_scenario(self) -> "HistoricalScenario":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        if self.baseline_end < self.baseline_start:
            raise ValueError("baseline_end must not be before baseline_start")
        latest = _today() + _DATE_TOLERANCE
        if self.period_end > latest or self.baseline_end > latest:
            raise ValueError("a historical scenario cannot extend into the future")
        if get_variable(self.classification_variable).domain is not VariableDomain.ENVIRONMENT:
            raise ValueError("scenarios must be classified with an environmental variable")
        _require_unique(self.source_ids, "source_ids")
        return self


# --------------------------------------------------------------------------- #
# 8. Farmer priority
# --------------------------------------------------------------------------- #


class PriorityDimension(StrEnum):
    """What a farmer may care about when comparing rotations.

    The first six come from the official challenge text. The rest are
    CropShift's own additions. What evidence each one needs before it can be
    assessed is recorded in the knowledge base (``data/knowledge``).
    """

    WATER_USE = "water_use"
    NITROGEN_FIXATION = "nitrogen_fixation"
    EROSION_REDUCTION = "erosion_reduction"
    ORGANIC_MATTER = "organic_matter"
    FORAGE_VALUE = "forage_value"
    MARKET_SUITABILITY = "market_suitability"
    PEST_CYCLE_DISRUPTION = "pest_cycle_disruption"
    CLIMATE_RESILIENCE = "climate_resilience"
    CROP_DIVERSITY = "crop_diversity"
    OPERATIONAL_SIMPLICITY = "operational_simplicity"


class FarmerPriority(Contract):
    """How much one dimension matters to the farmer, from 0 (not at all) to 1."""

    dimension: PriorityDimension
    weight: float = Field(ge=0, le=1)
    note: Text | None = None


class FarmerPriorityProfile(Contract):
    """The farmer's full set of priorities and stated constraints."""

    priorities: tuple[FarmerPriority, ...] = Field(min_length=1)
    constraints: tuple[Text, ...] = Field(
        default=(), description="For example limited irrigation water or equipment."
    )

    @model_validator(mode="after")
    def _check_profile(self) -> "FarmerPriorityProfile":
        _require_unique([item.dimension.value for item in self.priorities], "priority dimensions")
        if sum(item.weight for item in self.priorities) <= 0:
            raise ValueError("at least one priority needs a weight above zero")
        return self

    def normalised_weights(self) -> dict[PriorityDimension, float]:
        """Weights rescaled so that they add up to 1."""
        total = sum(item.weight for item in self.priorities)
        return {item.dimension: item.weight / total for item in self.priorities}


# --------------------------------------------------------------------------- #
# 11. Uncertainty and limitations
# --------------------------------------------------------------------------- #


class ConfidenceLevel(StrEnum):
    NOT_ASSESSED = "not_assessed"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class UncertaintyCategory(StrEnum):
    """Why a result is uncertain. Added in phase A4; see src/uncertainty.py."""

    DATA_MISSING = "data_missing"
    SOURCE_UNVERIFIED = "source_unverified"
    ABSTRACT_ONLY_EVIDENCE = "abstract_only_evidence"
    CONTEXT_DEPENDENT_EVIDENCE = "context_dependent_evidence"
    LOCATION_APPROXIMATION = "location_approximation"
    SEASON_ASSUMPTION = "season_assumption"
    SOIL_INPUT_UNVERIFIED = "soil_input_unverified"
    MODEL_LIMITATION = "model_limitation"
    INCOMPLETE_OBSERVATION_PERIOD = "incomplete_observation_period"
    UNSUPPORTED_INDICATOR = "unsupported_indicator"


class UncertaintyStatement(Contract):
    """What is uncertain about a result, in terms a user can act on."""

    confidence: ConfidenceLevel
    confidence_basis: Text = Field(description="Why this confidence level was assigned.")
    lower_bound: float | None = None
    upper_bound: float | None = None
    unit: Unit | None = None
    interval_method: Text | None = Field(default=None, description="How the range was obtained.")
    sources_of_uncertainty: tuple[Text, ...] = ()
    assumptions: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = Field(min_length=1)
    requires_local_review: bool = True
    categories: tuple[UncertaintyCategory, ...] = Field(
        default=(), description="Kinds of uncertainty that apply (added in phase A4)."
    )

    @model_validator(mode="after")
    def _check_interval(self) -> "UncertaintyStatement":
        if (self.lower_bound is None) != (self.upper_bound is None):
            raise ValueError("give both lower_bound and upper_bound, or neither")
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound > self.upper_bound:
                raise ValueError("lower_bound must not be greater than upper_bound")
            if self.unit is None or self.interval_method is None:
                raise ValueError("a range needs a unit and the method used to obtain it")
        return self


# --------------------------------------------------------------------------- #
# 9. Scenario result
# --------------------------------------------------------------------------- #


class ScenarioResult(Contract):
    """Indicators calculated for one rotation under one historical scenario."""

    rotation_id: Slug
    scenario_id: Slug
    indicators: tuple[ScientificValue, ...] = ()
    uncertainty: UncertaintyStatement
    engine_version: Text
    computed_at: AwareDatetime
    input_source_ids: tuple[Slug, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_result(self) -> "ScenarioResult":
        _require_domain(self.indicators, VariableDomain.INDICATOR, "a scenario result")
        _require_unique([item.variable for item in self.indicators], "indicators")
        for item in self.indicators:
            if item.provenance.kind not in _INDICATOR_KINDS:
                raise ValueError(
                    f"indicator '{item.variable}' must be labelled as modeled or derived, "
                    f"never as '{item.provenance.kind.value}'"
                )
        if self.computed_at > _now() + _CLOCK_TOLERANCE:
            raise ValueError("computed_at cannot be in the future")
        return self

    def get(self, variable: str) -> ScientificValue | None:
        return next((item for item in self.indicators if item.variable == variable), None)


# --------------------------------------------------------------------------- #
# 10. Comparison result
# --------------------------------------------------------------------------- #


class RotationAssessment(Contract):
    """The explanation the challenge asks for, for one rotation strategy."""

    rotation_id: Slug
    rationale: Text = Field(description="Why this rotation is being considered.")
    supporting_evidence: tuple[ProvenanceRecord, ...] = Field(min_length=1)
    potential_benefits: tuple[Text, ...] = ()
    information_gaps: tuple[Text, ...] = ()
    local_review_risks: tuple[Text, ...] = Field(
        default=(), description="Risks a farmer or local expert needs to check."
    )


class ComparisonResult(Contract):
    """Side-by-side results for several rotations across historical scenarios."""

    comparison_id: Slug
    location: GeoLocation
    rotation_ids: tuple[Slug, ...] = Field(min_length=2)
    scenario_ids: tuple[Slug, ...] = Field(min_length=1)
    current_practice_rotation_id: Slug | None = None
    results: tuple[ScenarioResult, ...] = ()
    assessments: tuple[RotationAssessment, ...] = ()
    priorities: FarmerPriorityProfile | None = None
    uncertainty: UncertaintyStatement
    generated_at: AwareDatetime
    disclaimer: Text = DEFAULT_DISCLAIMER

    @model_validator(mode="after")
    def _check_comparison(self) -> "ComparisonResult":
        _require_unique(self.rotation_ids, "rotation_ids")
        _require_unique(self.scenario_ids, "scenario_ids")
        if (
            self.current_practice_rotation_id is not None
            and self.current_practice_rotation_id not in self.rotation_ids
        ):
            raise ValueError("the current-practice rotation must be one of the compared rotations")
        pairs = [(item.rotation_id, item.scenario_id) for item in self.results]
        if len(set(pairs)) != len(pairs):
            raise ValueError("each rotation and scenario pair may appear only once")
        for rotation_id, scenario_id in pairs:
            if rotation_id not in self.rotation_ids or scenario_id not in self.scenario_ids:
                raise ValueError("every result must belong to a compared rotation and scenario")
        assessed = [item.rotation_id for item in self.assessments]
        _require_unique(assessed, "rotation assessments")
        if any(rotation_id not in self.rotation_ids for rotation_id in assessed):
            raise ValueError("every assessment must belong to a compared rotation")
        if self.generated_at > _now() + _CLOCK_TOLERANCE:
            raise ValueError("generated_at cannot be in the future")
        return self

    @property
    def missing_pairs(self) -> tuple[tuple[str, str], ...]:
        """Rotation and scenario combinations that have no result yet."""
        done = {(item.rotation_id, item.scenario_id) for item in self.results}
        return tuple(
            (rotation_id, scenario_id)
            for rotation_id in self.rotation_ids
            for scenario_id in self.scenario_ids
            if (rotation_id, scenario_id) not in done
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_pairs

    @property
    def follows_challenge_guidance(self) -> bool:
        """True when at least three rotations are compared, including the current one.

        The challenge suggests comparing "at least three rotation strategies,
        including the existing rotation".
        """
        return len(self.rotation_ids) >= 3 and self.current_practice_rotation_id is not None
