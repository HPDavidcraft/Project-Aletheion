"""Generate GeoServer SLD 1.0 raster styles from explicit source metadata."""

from __future__ import annotations

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


_SLD = "http://www.opengis.net/sld"
_XSI = "http://www.w3.org/2001/XMLSchema-instance"
_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")
_COLOR = re.compile(r"#[A-Fa-f0-9]{6}\Z")

ET.register_namespace("", _SLD)
ET.register_namespace("xsi", _XSI)


class SLDValidationError(ValueError):
    """Raised when an SLD style definition is invalid."""


@dataclass(frozen=True, slots=True)
class RasterClass:
    value: int | float
    label: str
    color: str


@dataclass(frozen=True, slots=True)
class RasterColorStop:
    value: int | float
    color: str


def build_categorical_sld(
    *,
    name: str,
    title: str,
    classes: Sequence[RasterClass],
) -> bytes:
    """Build a classified-raster SLD without assuming dataset class codes."""
    _validate_style_header(name, title)
    if not isinstance(classes, Sequence) or isinstance(classes, (str, bytes)) or not classes:
        raise SLDValidationError("At least one raster class is required")
    if any(not isinstance(item, RasterClass) for item in classes):
        raise SLDValidationError("classes must contain RasterClass values")
    values = [_finite_number(item.value, "class value") for item in classes]
    if len(set(values)) != len(values):
        raise SLDValidationError("Raster class values must be unique")

    color_map = _create_color_map("values")
    for item in sorted(classes, key=lambda value: value.value):
        _validate_color(item.color)
        label = _required_text(item.label, "class label")
        ET.SubElement(
            color_map,
            _tag("ColorMapEntry"),
            {
                "color": item.color.upper(),
                "quantity": _number_text(item.value),
                "label": label,
                "opacity": "1",
            },
        )
    return _serialize_sld(name, title, color_map)


def build_ramp_sld(
    *,
    name: str,
    title: str,
    stops: Sequence[RasterColorStop],
) -> bytes:
    """Build a continuous-raster color ramp from dataset-supplied breakpoints."""
    _validate_style_header(name, title)
    if not isinstance(stops, Sequence) or isinstance(stops, (str, bytes)) or len(stops) < 2:
        raise SLDValidationError("At least two color stops are required")
    if any(not isinstance(item, RasterColorStop) for item in stops):
        raise SLDValidationError("stops must contain RasterColorStop values")
    values = [_finite_number(item.value, "color-stop value") for item in stops]
    if any(left >= right for left, right in zip(values, values[1:])):
        raise SLDValidationError("Color-stop values must be strictly increasing")

    color_map = _create_color_map("ramp")
    for item in stops:
        _validate_color(item.color)
        ET.SubElement(
            color_map,
            _tag("ColorMapEntry"),
            {
                "color": item.color.upper(),
                "quantity": _number_text(item.value),
                "label": _number_text(item.value),
                "opacity": "1",
            },
        )
    return _serialize_sld(name, title, color_map)


def write_sld(path: str | Path, document: bytes) -> None:
    """Write generated SLD bytes to a destination file."""
    destination = Path(path)
    try:
        root = ET.fromstring(document)
    except ET.ParseError as exc:
        raise SLDValidationError("Generated SLD is not valid XML") from exc
    if root.tag != _tag("StyledLayerDescriptor"):
        raise SLDValidationError("Document root must be StyledLayerDescriptor")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(document)


def _create_color_map(color_map_type: str) -> ET.Element:
    symbolizer = ET.Element(_tag("RasterSymbolizer"))
    return ET.SubElement(
        symbolizer,
        _tag("ColorMap"),
        {"type": color_map_type, "extended": "true"},
    )


def _serialize_sld(name: str, title: str, color_map: ET.Element) -> bytes:
    root = ET.Element(
        _tag("StyledLayerDescriptor"),
        {
            "version": "1.0.0",
            f"{{{_XSI}}}schemaLocation": (
                "http://www.opengis.net/sld "
                "http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd"
            ),
        },
    )
    named_layer = ET.SubElement(root, _tag("NamedLayer"))
    ET.SubElement(named_layer, _tag("Name")).text = name
    user_style = ET.SubElement(named_layer, _tag("UserStyle"))
    ET.SubElement(user_style, _tag("Name")).text = name
    ET.SubElement(user_style, _tag("Title")).text = title
    feature_type_style = ET.SubElement(user_style, _tag("FeatureTypeStyle"))
    rule = ET.SubElement(feature_type_style, _tag("Rule"))
    ET.SubElement(rule, _tag("RasterSymbolizer")).append(color_map)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _validate_style_header(name: str, title: str) -> None:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise SLDValidationError("Style name must contain only letters, digits, dot, dash, or underscore")
    _required_text(title, "style title")


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SLDValidationError(f"{field} is required")
    return value.strip()


def _finite_number(value: object, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SLDValidationError(f"{field} must be finite numeric data")
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise SLDValidationError(f"{field} is outside the supported numeric range") from exc
    if not finite:
        raise SLDValidationError(f"{field} must be finite numeric data")
    return value


def _validate_color(value: object) -> None:
    if not isinstance(value, str) or not _COLOR.fullmatch(value):
        raise SLDValidationError("Colors must use #RRGGBB hexadecimal notation")


def _number_text(value: int | float) -> str:
    return str(value) if isinstance(value, int) else format(value, ".15g")


def _tag(name: str) -> str:
    return f"{{{_SLD}}}{name}"


def _load_definition(path: Path) -> dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SLDValidationError(f"Could not read style definition: {exc}") from exc
    if not isinstance(document, dict):
        raise SLDValidationError("Style definition root must be a JSON object")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a GeoServer SLD from explicit raster class or ramp values."
    )
    parser.add_argument("definition", type=Path, help="JSON style definition")
    parser.add_argument("output", type=Path, help="Output SLD file")
    arguments = parser.parse_args()
    definition = _load_definition(arguments.definition)
    mode = definition.get("mode")
    if mode == "categorical":
        classes = definition.get("classes")
        if not isinstance(classes, list):
            raise SLDValidationError("categorical definition requires a classes array")
        if any(not isinstance(item, dict) for item in classes):
            raise SLDValidationError("every categorical class must be a JSON object")
        document = build_categorical_sld(
            name=definition.get("name"),
            title=definition.get("title"),
            classes=tuple(
                RasterClass(
                    value=item.get("value"),
                    label=item.get("label"),
                    color=item.get("color"),
                )
                for item in classes
            ),
        )
    elif mode == "ramp":
        stops = definition.get("stops")
        if not isinstance(stops, list):
            raise SLDValidationError("ramp definition requires a stops array")
        if any(not isinstance(item, dict) for item in stops):
            raise SLDValidationError("every color stop must be a JSON object")
        document = build_ramp_sld(
            name=definition.get("name"),
            title=definition.get("title"),
            stops=tuple(
                RasterColorStop(value=item.get("value"), color=item.get("color"))
                for item in stops
            ),
        )
    else:
        raise SLDValidationError("mode must be categorical or ramp")
    write_sld(arguments.output, document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
