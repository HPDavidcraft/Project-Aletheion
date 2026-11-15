"""Coordinate reprojection helpers with explicit CRS axis-order handling."""

from __future__ import annotations

import math
from typing import Protocol


class CoordinateTransformError(ValueError):
    """Raised when a configured coordinate transformation cannot be performed."""


class CoordinateTransformer(Protocol):
    def transform(
        self, x: float, y: float, source_crs: str, target_crs: str
    ) -> tuple[float, float]:
        """Transform one x/y pair; geographic coordinates always use lon/lat."""


_WEB_MERCATOR_LIMIT = 20_037_508.342789244
_WEB_MERCATOR_MAX_LAT = 85.0511287798066
_EARTH_RADIUS_M = 6_378_137.0


def _crs_code(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoordinateTransformError("CRS must be a non-empty identifier")
    normalized = value.strip().upper()
    if normalized in {"CRS:84", "OGC:CRS84"}:
        return "EPSG:4326"
    return normalized


def _finite_pair(x: float, y: float) -> None:
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(
        x, (int, float)
    ) or not isinstance(y, (int, float)):
        raise CoordinateTransformError("Coordinates must be finite numbers")
    try:
        finite = math.isfinite(x) and math.isfinite(y)
    except OverflowError as exc:
        raise CoordinateTransformError("Coordinates must be finite numbers") from exc
    if not finite:
        raise CoordinateTransformError("Coordinates must be finite numbers")


def _check_lon_lat(longitude: float, latitude: float) -> None:
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise CoordinateTransformError("EPSG:4326 coordinates must be longitude/latitude")


class BasicCoordinateTransformer:
    """Dependency-free WGS 84 and Web Mercator transformations."""

    def transform(
        self, x: float, y: float, source_crs: str, target_crs: str
    ) -> tuple[float, float]:
        _finite_pair(x, y)
        source = _crs_code(source_crs)
        target = _crs_code(target_crs)
        if source == target:
            if target == "EPSG:4326":
                _check_lon_lat(x, y)
            return float(x), float(y)
        if source == "EPSG:4326" and target == "EPSG:3857":
            _check_lon_lat(x, y)
            if abs(y) > _WEB_MERCATOR_MAX_LAT:
                raise CoordinateTransformError(
                    "Latitude is outside the Web Mercator projection domain"
                )
            longitude_radians = math.radians(x)
            latitude_radians = math.radians(y)
            return (
                _EARTH_RADIUS_M * longitude_radians,
                _EARTH_RADIUS_M
                * math.log(math.tan(math.pi / 4 + latitude_radians / 2)),
            )
        if source == "EPSG:3857" and target == "EPSG:4326":
            if abs(x) > _WEB_MERCATOR_LIMIT or abs(y) > _WEB_MERCATOR_LIMIT:
                raise CoordinateTransformError(
                    "Coordinate is outside the Web Mercator projection domain"
                )
            longitude = math.degrees(x / _EARTH_RADIUS_M)
            latitude = math.degrees(
                2 * math.atan(math.exp(y / _EARTH_RADIUS_M)) - math.pi / 2
            )
            _check_lon_lat(longitude, latitude)
            return longitude, latitude
        raise CoordinateTransformError(
            f"Unsupported CRS transformation: {source} to {target}; "
            "configure PyProjCoordinateTransformer for other projections"
        )


class PyProjCoordinateTransformer:
    """Optional general-purpose transformer; requires the deployment's pyproj."""

    def transform(
        self, x: float, y: float, source_crs: str, target_crs: str
    ) -> tuple[float, float]:
        _finite_pair(x, y)
        try:
            from pyproj import Transformer

            transformer = Transformer.from_crs(
                source_crs, target_crs, always_xy=True
            )
            result_x, result_y = transformer.transform(x, y, errcheck=True)
        except ImportError as exc:
            raise CoordinateTransformError(
                "pyproj is required for this configured CRS transformation"
            ) from exc
        except (ValueError, RuntimeError) as exc:
            raise CoordinateTransformError(
                f"Could not transform coordinates from {source_crs} to {target_crs}"
            ) from exc
        _finite_pair(result_x, result_y)
        return float(result_x), float(result_y)
