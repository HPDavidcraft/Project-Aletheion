"""Small strict GeoJSON helpers for WGS 84 spatial service payloads."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


class GeoJSONValidationError(ValueError):
    """Raised when a spatial payload is not a valid WGS 84 LineString."""


@dataclass(frozen=True, slots=True)
class GeoJSONLineString:
    coordinates: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.coordinates) < 2:
            raise GeoJSONValidationError("A LineString needs at least two positions")
        if not any(
            self.coordinates[index] != self.coordinates[index - 1]
            for index in range(1, len(self.coordinates))
        ):
            raise GeoJSONValidationError("A LineString must have non-zero length")
        for longitude, latitude in self.coordinates:
            if not isfinite(longitude) or not isfinite(latitude):
                raise GeoJSONValidationError("Coordinates must be finite")
            if not -180 <= longitude <= 180:
                raise GeoJSONValidationError("Longitude must be between -180 and 180")
            if not -90 <= latitude <= 90:
                raise GeoJSONValidationError("Latitude must be between -90 and 90")

    def as_geojson(self) -> dict[str, Any]:
        return {
            "type": "LineString",
            "coordinates": [list(position) for position in self.coordinates],
        }


def validate_linestring(value: object) -> GeoJSONLineString:
    if not isinstance(value, dict) or value.get("type") != "LineString":
        raise GeoJSONValidationError("Expected a GeoJSON LineString geometry")
    raw_coordinates = value.get("coordinates")
    if not isinstance(raw_coordinates, list):
        raise GeoJSONValidationError("LineString coordinates must be an array")

    coordinates: list[tuple[float, float]] = []
    for position in raw_coordinates:
        if not isinstance(position, list) or len(position) != 2:
            raise GeoJSONValidationError(
                "Each position must contain exactly longitude and latitude"
            )
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               for value in position):
            raise GeoJSONValidationError("Coordinates must be numeric")
        coordinates.append((float(position[0]), float(position[1])))
    return GeoJSONLineString(tuple(coordinates))
