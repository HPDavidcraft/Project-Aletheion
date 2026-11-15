"""PostGIS-backed GeoJSON topology validation for WGS 84 geometries."""

from __future__ import annotations

import json
import math
from typing import Mapping, Protocol

from .common import ValidationIssue, ValidationReport


_GEOMETRY_TYPES = frozenset(
    {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    }
)

_POSTGIS_DETAIL_QUERY = """
WITH candidate AS (
    SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) AS geom
),
details AS (
    SELECT geom, ST_IsValidDetail(geom) AS detail
    FROM candidate
)
SELECT
    ST_IsEmpty(geom),
    (detail).valid,
    (detail).reason,
    ST_AsGeoJSON((detail).location),
    ST_GeometryType(geom),
    ST_Area(geom),
    ST_XMin(ST_Envelope(geom)),
    ST_XMax(ST_Envelope(geom)),
    ST_YMin(ST_Envelope(geom)),
    ST_YMax(ST_Envelope(geom))
FROM details
"""


class PostGISResult(Protocol):
    def fetchone(self) -> tuple[object, ...] | None:
        """Return the single validation result row."""


class PostGISConnection(Protocol):
    def execute(
        self, query: str, parameters: tuple[str]
    ) -> PostGISResult:
        """Execute a parameterized validation query."""


def validate_geojson_geometry(
    connection: PostGISConnection,
    geometry: Mapping[str, object],
    *,
    expected_type: str | None = None,
    require_positive_area: bool = False,
) -> ValidationReport:
    """Ask PostGIS for OGC validity and ST_IsValidDetail diagnostics."""
    if not isinstance(geometry, Mapping):
        return ValidationReport(
            (ValidationIssue("geometry.not_object", "GeoJSON geometry must be an object"),)
        )
    geometry_type_value = geometry.get("type")
    if (
        not isinstance(geometry_type_value, str)
        or geometry_type_value not in _GEOMETRY_TYPES
    ):
        return ValidationReport(
            (ValidationIssue("geometry.unsupported_type", "Unsupported GeoJSON geometry type"),)
        )
    if "crs" in geometry:
        return ValidationReport(
            (
                ValidationIssue(
                    "geometry.legacy_crs_member",
                    "GeoJSON input must use the WGS 84 axis convention and omit legacy crs members",
                ),
            )
        )
    if expected_type is not None and (
        not isinstance(expected_type, str) or expected_type not in _GEOMETRY_TYPES
    ):
        raise ValueError(f"Unsupported expected geometry type: {expected_type}")
    try:
        serialized = json.dumps(
            geometry, allow_nan=False, ensure_ascii=False, separators=(",", ":")
        )
    except (TypeError, ValueError):
        return ValidationReport(
            (ValidationIssue("geometry.invalid_json", "Geometry is not finite JSON data"),)
        )

    row = connection.execute(_POSTGIS_DETAIL_QUERY, (serialized,)).fetchone()
    if row is None or len(row) != 10:
        raise RuntimeError("PostGIS geometry validation returned an invalid result row")
    (
        is_empty,
        is_valid,
        reason,
        location,
        geometry_type,
        area,
        xmin,
        xmax,
        ymin,
        ymax,
    ) = row
    issues: list[ValidationIssue] = []
    if is_empty:
        issues.append(ValidationIssue("geometry.empty", "Geometry must not be empty"))
    if not is_valid:
        diagnostic = str(reason or "Geometry is topologically invalid")
        if location:
            diagnostic += f" at {location}"
        issues.append(ValidationIssue("geometry.topology", diagnostic))
    if expected_type is not None and geometry_type != f"ST_{expected_type}":
        issues.append(
            ValidationIssue(
                "geometry.type",
                f"Expected {expected_type}, received {geometry_type}",
            )
        )
    if not is_empty and (
        xmin < -180 or xmax > 180 or ymin < -90 or ymax > 90
    ):
        issues.append(
            ValidationIssue(
                "geometry.coordinate_range",
                "Geometry coordinates must be longitude/latitude within WGS 84 bounds",
            )
        )
    if require_positive_area and (
        isinstance(area, bool)
        or not isinstance(area, (int, float))
        or not math.isfinite(area)
        or area <= 0
    ):
        issues.append(
            ValidationIssue("geometry.area", "Polygonal geometry must have positive area")
        )
    return ValidationReport(tuple(issues))
