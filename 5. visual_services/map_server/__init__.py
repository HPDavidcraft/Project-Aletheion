"""GeoServer-facing styles and deployment configuration."""

from .sld import (
    RasterClass,
    RasterColorStop,
    SLDValidationError,
    build_categorical_sld,
    build_ramp_sld,
    write_sld,
)

__all__ = [
    "RasterClass",
    "RasterColorStop",
    "SLDValidationError",
    "build_categorical_sld",
    "build_ramp_sld",
    "write_sld",
]
