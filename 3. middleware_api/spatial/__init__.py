"""Spatial analysis and time-aware paleoclimate service components."""

from .geojson import GeoJSONLineString, validate_linestring
from .paleoclimate import ClimateLayer, PaleoclimateCatalog, GeoServerConfig

__all__ = [
    "ClimateLayer",
    "GeoJSONLineString",
    "GeoServerConfig",
    "PaleoclimateCatalog",
    "validate_linestring",
]
