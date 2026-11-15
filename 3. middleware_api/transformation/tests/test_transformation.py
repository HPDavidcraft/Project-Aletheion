import json
import unittest

from transformation.coordinates import (
    BasicCoordinateTransformer,
    CoordinateTransformError,
)
from transformation.csv_to_cidoc import (
    CRMMapping,
    CSVMappingProfile,
    CSVToCIDOCTransformer,
    CSVTransformationError,
    CoordinateMapping,
    FieldMapping,
    TransformationConfigurationError,
)


SITE_CLASS = "https://pleroma.example/ontology/Site"
NAME_PROPERTY = "https://pleroma.example/ontology/name"
DATE_PROPERTY = "https://pleroma.example/ontology/date"
TYPE_PROPERTY = "https://pleroma.example/ontology/objectType"
GEOMETRY_PROPERTY = "https://pleroma.example/ontology/geometry"


class FixtureRegistry:
    def __init__(self, *, verified=True, relation="subClassOf"):
        status = "verified" if verified else "proposed"
        self._class = CRMMapping(
            target_uri="http://crm.fixture/class/E27",
            relation=relation,
            status=status,
            standard_code="fixture-crm",
            standard_release="fixture-release",
        )
        self._properties = {
            NAME_PROPERTY: CRMMapping(
                "http://crm.fixture/property/name",
                "exactMatch",
                status,
                "fixture-crm",
                "fixture-release",
            ),
            DATE_PROPERTY: CRMMapping(
                "http://crm.fixture/property/date",
                "exactMatch",
                status,
                "fixture-crm",
                "fixture-release",
            ),
            TYPE_PROPERTY: CRMMapping(
                "http://crm.fixture/property/type",
                "exactMatch",
                status,
                "fixture-crm",
                "fixture-release",
            ),
            GEOMETRY_PROPERTY: CRMMapping(
                "http://crm.fixture/property/geometry",
                "exactMatch",
                status,
                "fixture-crm",
                "fixture-release",
            ),
        }

    def class_mapping(self, project_class_uri):
        return self._class if project_class_uri == SITE_CLASS else None

    def property_mapping(self, project_property_uri):
        return self._properties.get(project_property_uri)


def profile(**overrides):
    values = {
        "profile_id": "legacy-site-csv",
        "version": "1.0",
        "entity_namespace": "https://pleroma.example/entity/site",
        "project_class_uri": SITE_CLASS,
        "identifier_column": "legacy_id",
        "fields": (
            FieldMapping("name", NAME_PROPERTY, "literal", required=True),
            FieldMapping("date", DATE_PROPERTY, "edtf"),
            FieldMapping(
                "type",
                TYPE_PROPERTY,
                "controlled_uri",
                vocabulary={"site": "https://pleroma.example/vocab/site"},
            ),
        ),
        "coordinate": CoordinateMapping(
            "easting", "northing", "EPSG:3857", GEOMETRY_PROPERTY
        ),
    }
    values.update(overrides)
    return CSVMappingProfile(**values)


class CoordinateTests(unittest.TestCase):
    def test_web_mercator_round_trips_with_longitude_latitude_axis_order(self):
        transformer = BasicCoordinateTransformer()
        projected = transformer.transform(1, 1, "EPSG:4326", "EPSG:3857")
        longitude, latitude = transformer.transform(
            *projected, "EPSG:3857", "EPSG:4326"
        )
        self.assertAlmostEqual(longitude, 1)
        self.assertAlmostEqual(latitude, 1)

    def test_unknown_projection_fails_instead_of_returning_untransformed_values(self):
        with self.assertRaises(CoordinateTransformError):
            BasicCoordinateTransformer().transform(
                500_000, 4_500_000, "EPSG:32630", "EPSG:4326"
            )


class CSVTransformationTests(unittest.TestCase):
    def setUp(self):
        self.transformer = CSVToCIDOCTransformer(FixtureRegistry())

    def test_valid_csv_becomes_verified_cidoc_jsonld_with_normalized_values(self):
        raw = (
            "legacy_id,name,date,type,easting,northing\n"
            'site/1,"Tell ""Example"""," -1200 ","site",111319.49079327357,111325.1428663851\n'
        ).encode()
        result = self.transformer.transform_bytes(raw, profile())
        document = result.to_jsonld()
        self.assertEqual(len(document["@graph"]), 1)
        node = document["@graph"][0]
        self.assertEqual(
            node["@id"], "https://pleroma.example/entity/site/site%2F1"
        )
        self.assertEqual(
            node["@type"],
            [SITE_CLASS, "http://crm.fixture/class/E27"],
        )
        self.assertEqual(
            node["http://crm.fixture/property/date"],
            {"@value": "-1200", "@type": "http://www.w3.org/2001/XMLSchema#string"},
        )
        self.assertEqual(
            node["http://crm.fixture/property/type"],
            {"@id": "https://pleroma.example/vocab/site"},
        )
        geometry = json.loads(node["http://crm.fixture/property/geometry"]["@value"])
        self.assertEqual(geometry["type"], "Point")
        self.assertAlmostEqual(geometry["coordinates"][0], 1)
        self.assertAlmostEqual(geometry["coordinates"][1], 1)
        self.assertEqual(result.source_row_count, 1)
        self.assertEqual(len(result.source_sha256), 64)
        self.assertEqual(result.crm_releases, ("fixture-release",))

    def test_unverified_or_close_match_mappings_cannot_be_used(self):
        for registry in (
            FixtureRegistry(verified=False),
            FixtureRegistry(relation="closeMatch"),
        ):
            with self.subTest(registry=registry):
                transformer = CSVToCIDOCTransformer(registry)
                with self.assertRaises(TransformationConfigurationError):
                    transformer.transform_bytes(
                        b"legacy_id,name,date,type,easting,northing\n",
                        profile(),
                    )

    def test_invalid_edtf_and_unmapped_columns_fail_without_partial_graph(self):
        raw = (
            "legacy_id,name,date,type,easting,northing\n"
            "1,Site,circa 1200,site,0,0\n"
        ).encode()
        with self.assertRaises(CSVTransformationError) as caught:
            self.transformer.transform_bytes(raw, profile())
        self.assertEqual(caught.exception.issues[0].field, "date")
        self.assertEqual(caught.exception.issues[0].message, "invalid EDTF value")

        with self.assertRaises(CSVTransformationError) as caught:
            self.transformer.transform_bytes(
                b"legacy_id,name,date,type,easting,northing,extra\n"
                b"1,Site,1200,site,0,0,ignored\n",
                profile(),
            )
        self.assertIn("mapped or explicitly ignored", str(caught.exception))

    def test_proprietary_excel_sources_are_rejected(self):
        with self.assertRaises(CSVTransformationError) as caught:
            self.transformer.transform_file("legacy.xlsx", profile())
        self.assertIn("Only open CSV", str(caught.exception))

    def test_coordinate_pair_must_be_complete(self):
        raw = (
            "legacy_id,name,date,type,easting,northing\n"
            "1,Site,1200,site,0,\n"
        ).encode()
        with self.assertRaises(CSVTransformationError) as caught:
            self.transformer.transform_bytes(raw, profile())
        self.assertEqual(caught.exception.issues[0].field, "northing")

if __name__ == "__main__":
    unittest.main()
