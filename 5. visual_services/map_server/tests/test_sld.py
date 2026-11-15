import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from sld import (
    RasterClass,
    RasterColorStop,
    SLDValidationError,
    build_categorical_sld,
    build_ramp_sld,
    write_sld,
)


SLD = "{http://www.opengis.net/sld}"


class SLDTests(unittest.TestCase):
    def test_builds_categorical_style_from_explicit_codes(self):
        document = build_categorical_sld(
            name="paleokoppen",
            title="Configured paleoclimate classes",
            classes=(
                RasterClass(2, "Class B", "#aabbcc"),
                RasterClass(1, "Class A", "#112233"),
            ),
        )
        root = ET.fromstring(document)
        entries = root.findall(f".//{SLD}ColorMapEntry")
        self.assertEqual(root.attrib["version"], "1.0.0")
        self.assertEqual([entry.attrib["quantity"] for entry in entries], ["1", "2"])
        self.assertEqual(entries[0].attrib["color"], "#112233")

    def test_builds_continuous_ramp_from_explicit_breakpoints(self):
        document = build_ramp_sld(
            name="temperature",
            title="Temperature in degrees Celsius",
            stops=(
                RasterColorStop(-20, "#2c7bb6"),
                RasterColorStop(0, "#ffffbf"),
                RasterColorStop(40, "#d7191c"),
            ),
        )
        root = ET.fromstring(document)
        color_map = root.find(f".//{SLD}ColorMap")
        self.assertEqual(color_map.attrib["type"], "ramp")
        self.assertEqual(len(color_map.findall(f"{SLD}ColorMapEntry")), 3)

    def test_rejects_duplicate_values_and_invalid_palette(self):
        with self.assertRaisesRegex(SLDValidationError, "unique"):
            build_categorical_sld(
                name="classes",
                title="Classes",
                classes=(
                    RasterClass(1, "A", "#112233"),
                    RasterClass(1, "B", "#445566"),
                ),
            )
        with self.assertRaisesRegex(SLDValidationError, "strictly increasing"):
            build_ramp_sld(
                name="ramp",
                title="Ramp",
                stops=(
                    RasterColorStop(0, "#112233"),
                    RasterColorStop(0, "#445566"),
                ),
            )
        with self.assertRaisesRegex(SLDValidationError, "RRGGBB"):
            build_categorical_sld(
                name="classes",
                title="Classes",
                classes=(RasterClass(1, "A", "red"),),
            )

    def test_writes_parseable_sld(self):
        document = build_categorical_sld(
            name="classes",
            title="Classes",
            classes=(RasterClass(1, "A", "#112233"),),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "classes.sld"
            write_sld(path, document)
            self.assertEqual(
                ET.parse(path).getroot().tag,
                f"{SLD}StyledLayerDescriptor",
            )


if __name__ == "__main__":
    unittest.main()
