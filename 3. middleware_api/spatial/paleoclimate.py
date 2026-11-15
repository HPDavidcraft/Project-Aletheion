"""Time-slice resolution and safe GeoServer WMS request construction."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit

from chronology.edtf import EDTFDate, parse_edtf


class ClimateCatalogError(ValueError):
    """Raised for invalid climate catalog entries or query limits."""


class TooManyClimateSlices(ClimateCatalogError):
    """Raised when an uncertain date expands to too many configured slices."""


@dataclass(frozen=True, slots=True)
class ClimateLayer:
    layer_id: str
    model: str
    variable: str
    year_start: int
    year_end_exclusive: int
    wms_time: str
    source_uri: str
    resolution_m: int
    unit: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+", self.layer_id):
            raise ClimateCatalogError("layer_id must be a workspace:layer identifier")
        if self.model not in {"CHELSA-TraCE21k", "PMIP4"}:
            raise ClimateCatalogError("Unsupported paleoclimate model")
        if not self.variable.strip():
            raise ClimateCatalogError("Climate variable is required")
        if self.year_start >= self.year_end_exclusive:
            raise ClimateCatalogError("Climate slice bounds must be non-empty")
        if not self.wms_time.strip() or any(ord(char) < 0x20 for char in self.wms_time):
            raise ClimateCatalogError("A valid GeoServer time value is required")
        parsed_source = urlsplit(self.source_uri)
        if (
            parsed_source.scheme not in {"http", "https"}
            or not parsed_source.hostname
            or parsed_source.username is not None
            or parsed_source.password is not None
        ):
            raise ClimateCatalogError("source_uri must be an HTTP(S) source URL")
        if (
            isinstance(self.resolution_m, bool)
            or not isinstance(self.resolution_m, int)
            or self.resolution_m <= 0
        ):
            raise ClimateCatalogError("resolution_m must be positive")
        if not self.unit.strip():
            raise ClimateCatalogError("Climate layer unit is required")

    def overlaps(self, date_value: EDTFDate) -> bool:
        date_intervals = date_value.intervals
        return any(
            (interval.end_year is None or self.year_start <= interval.end_year)
            and (interval.start_year is None or interval.start_year < self.year_end_exclusive)
            for interval in date_intervals
        )


class PaleoclimateCatalog:
    """Resolve canonical EDTF dates to only the configured time slices."""

    def __init__(self, layers: tuple[ClimateLayer, ...] | list[ClimateLayer]) -> None:
        identifiers = [layer.layer_id for layer in layers]
        if len(set(identifiers)) != len(identifiers):
            raise ClimateCatalogError("Climate layer identifiers must be unique")
        self._layers = tuple(layers)

    def resolve(
        self,
        date_expression: str,
        *,
        model: str | None = None,
        variables: frozenset[str] | None = None,
        max_slices: int = 100,
    ) -> tuple[ClimateLayer, ...]:
        if (
            isinstance(max_slices, bool)
            or not isinstance(max_slices, int)
            or max_slices <= 0
        ):
            raise ClimateCatalogError("max_slices must be a positive integer")
        date_value = parse_edtf(date_expression)
        matches = tuple(
            sorted(
                (
                    layer
                    for layer in self._layers
                    if layer.overlaps(date_value)
                    and (model is None or layer.model == model)
                    and (variables is None or layer.variable in variables)
                ),
                key=lambda layer: (
                    layer.model,
                    layer.variable,
                    layer.year_start,
                    layer.layer_id,
                ),
            )
        )
        if len(matches) > max_slices:
            raise TooManyClimateSlices(
                f"Date resolves to {len(matches)} slices; maximum is {max_slices}"
            )
        return matches


NUMERIC_CLIMATE_VARIABLES = frozenset(
    {
        "annual_mean_temperature",
        "annual_precipitation",
        "growing_degree_days",
    }
)


class RasterPointSampler(Protocol):
    def sample(self, layer: ClimateLayer, longitude: float, latitude: float) -> float:
        """Return a value from the configured raster cell at a WGS 84 point."""


@dataclass(frozen=True, slots=True)
class ClimateMetricReading:
    layer_id: str
    model: str
    variable: str
    value: float
    unit: str
    year_start: int
    year_end_exclusive: int


class PaleoclimateService:
    """Resolve and sample configured climate layers without inventing values."""

    def __init__(
        self, catalog: PaleoclimateCatalog, sampler: RasterPointSampler
    ) -> None:
        self._catalog = catalog
        self._sampler = sampler

    def extract_metrics(
        self,
        date_expression: str,
        longitude: float,
        latitude: float,
        *,
        model: str | None = None,
    ) -> tuple[ClimateMetricReading, ...]:
        if (
            isinstance(longitude, bool)
            or isinstance(latitude, bool)
            or not isinstance(longitude, (int, float))
            or not isinstance(latitude, (int, float))
            or not math.isfinite(longitude)
            or not math.isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError("Climate sample location must be a WGS 84 coordinate")
        layers = self._catalog.resolve(
            date_expression,
            model=model,
            variables=NUMERIC_CLIMATE_VARIABLES,
        )
        readings: list[ClimateMetricReading] = []
        for layer in layers:
            value = self._sampler.sample(layer, longitude, latitude)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ClimateCatalogError(
                    f"Raster sampler returned an invalid value for {layer.layer_id}"
                )
            readings.append(
                ClimateMetricReading(
                    layer_id=layer.layer_id,
                    model=layer.model,
                    variable=layer.variable,
                    value=float(value),
                    unit=layer.unit,
                    year_start=layer.year_start,
                    year_end_exclusive=layer.year_end_exclusive,
                )
            )
        return tuple(readings)


@dataclass(frozen=True, slots=True)
class GeoServerConfig:
    base_url: str
    allowed_hosts: frozenset[str]
    allow_http: bool = False

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        allowed_schemes = {"https", "http"} if self.allow_http else {"https"}
        hosts = frozenset(host.lower().rstrip(".") for host in self.allowed_hosts)
        if (
            parsed.scheme not in allowed_schemes
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.hostname.lower().rstrip(".") not in hosts
            or not hosts
        ):
            raise ValueError("GeoServer URL must use a trusted allowlisted host")
        object.__setattr__(self, "allowed_hosts", hosts)

    def get_map_url(
        self,
        layer: ClimateLayer,
        bbox: tuple[float, float, float, float],
        *,
        width: int = 1024,
        height: int = 768,
    ) -> str:
        west, south, east, north = bbox
        if (
            any(isinstance(value, bool) or not math.isfinite(value) for value in bbox)
            or not -180 <= west < east <= 180
            or not -90 <= south < north <= 90
        ):
            raise ValueError("bbox must be a valid WGS 84 west,south,east,north extent")
        if (
            isinstance(width, bool)
            or isinstance(height, bool)
            or not isinstance(width, int)
            or not isinstance(height, int)
            or not 1 <= width <= 2048
            or not 1 <= height <= 2048
        ):
            raise ValueError("WMS image dimensions must be between 1 and 2048 pixels")

        parsed = urlsplit(self.base_url)
        query = urlencode(
            {
                "service": "WMS",
                "version": "1.3.0",
                "request": "GetMap",
                "layers": layer.layer_id,
                "styles": "",
                "crs": "CRS:84",
                "bbox": ",".join(str(value) for value in bbox),
                "width": width,
                "height": height,
                "format": "image/png",
                "transparent": "true",
                "time": layer.wms_time,
            }
        )
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, query, "")
        )
