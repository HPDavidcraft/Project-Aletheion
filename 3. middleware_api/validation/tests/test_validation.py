import unittest
from unittest.mock import Mock, patch

from validation.geometry import validate_geojson_geometry
from validation.harris import (
    HarrisMatrixValidator,
    StratigraphicRelationship,
)
from validation.iiif import IIIFManifestValidator
from validation.publication import validate_publication_anchoring
from validation.temporal import (
    validate_stratigraphic_temporal_consistency,
    validate_temporal_order,
)


class HarrisMatrixTests(unittest.TestCase):
    def test_valid_graph_returns_deterministic_lower_to_upper_order(self):
        result = HarrisMatrixValidator().validate(
            {"lower": "site-1", "middle": "site-1", "upper": "site-1"},
            (
                StratigraphicRelationship("middle", "lower", "above"),
                StratigraphicRelationship("upper", "middle", "above"),
                StratigraphicRelationship("lower", "upper", "contemporary"),
            ),
        )
        self.assertTrue(result.report.valid)
        self.assertEqual(result.topological_order, ("lower", "middle", "upper"))

    def test_cycle_is_rejected_with_conflicting_unit_path(self):
        result = HarrisMatrixValidator().validate(
            {"a": "site-1", "b": "site-1", "c": "site-1"},
            (
                StratigraphicRelationship("a", "b", "above"),
                StratigraphicRelationship("b", "c", "above"),
                StratigraphicRelationship("c", "a", "above"),
            ),
        )
        cycle = next(issue for issue in result.report.issues if issue.code == "stratigraphy.cycle")
        self.assertIn("a", cycle.entity_ids)
        self.assertIn("b", cycle.entity_ids)
        self.assertIn("c", cycle.entity_ids)

    def test_cross_site_and_unknown_unit_relationships_are_rejected(self):
        result = HarrisMatrixValidator().validate(
            {"a": "site-1", "b": "site-2"},
            (
                StratigraphicRelationship("a", "b", "above"),
                StratigraphicRelationship("a", "missing", "below"),
            ),
        )
        self.assertEqual(
            {issue.code for issue in result.report.issues},
            {
                "stratigraphy.cross_site_relationship",
                "stratigraphy.unknown_unit",
            },
        )

    def test_large_acyclic_matrix_does_not_depend_on_python_recursion_depth(self):
        unit_ids = [f"unit-{index:04d}" for index in range(1_200)]
        result = HarrisMatrixValidator().validate(
            {unit_id: "site-1" for unit_id in unit_ids},
            tuple(
                StratigraphicRelationship(
                    unit_ids[index], unit_ids[index - 1], "above"
                )
                for index in range(1, len(unit_ids))
            ),
        )
        self.assertTrue(result.report.valid)
        self.assertEqual(len(result.topological_order), len(unit_ids))


class TemporalValidationTests(unittest.TestCase):
    def test_date_range_requires_end_beyond_start_uncertainty(self):
        self.assertTrue(validate_temporal_order("1200~", "1220").valid)
        report = validate_temporal_order("1200~", "1210", entity_id="site-1")
        self.assertEqual(report.issues[0].code, "temporal.start_end_order")
        invalid = validate_temporal_order("late bronze age", "1200")
        self.assertEqual(invalid.issues[0].code, "temporal.invalid_start_date")

    def test_stratigraphic_dates_must_match_superposition_and_contemporaneity(self):
        above = StratigraphicRelationship("upper", "lower", "above")
        self.assertTrue(
            validate_stratigraphic_temporal_consistency(
                {"lower": "1100", "upper": "1200"}, (above,)
            ).valid
        )
        conflict = validate_stratigraphic_temporal_consistency(
            {"lower": "1200", "upper": "1100"}, (above,)
        )
        self.assertEqual(conflict.issues[0].code, "temporal.superposition_conflict")
        contemporary = validate_stratigraphic_temporal_consistency(
            {"lower": "1100", "upper": "1200"},
            (StratigraphicRelationship("lower", "upper", "contemporary"),),
        )
        self.assertEqual(
            contemporary.issues[0].code,
            "temporal.contemporary_date_conflict",
        )


class GeometryValidationTests(unittest.TestCase):
    class Connection:
        def __init__(self, row):
            self.row = row
            self.query = None
            self.parameters = None

        def execute(self, query, parameters):
            self.query = query
            self.parameters = parameters
            cursor = Mock()
            cursor.fetchone.return_value = self.row
            return cursor

    def test_postgis_invalid_detail_is_reported_from_parameterized_query(self):
        connection = self.Connection(
            (False, False, "Self-intersection", '{"type":"Point","coordinates":[1,1]}',
             "ST_Polygon", 1.0, 0.0, 1.0, 0.0, 1.0)
        )
        report = validate_geojson_geometry(
            connection,
            {"type": "Polygon", "coordinates": []},
            expected_type="Polygon",
            require_positive_area=True,
        )
        self.assertEqual(report.issues[0].code, "geometry.topology")
        self.assertIn("ST_IsValidDetail", connection.query)
        self.assertNotIn("Polygon", connection.query)
        self.assertEqual(len(connection.parameters), 1)

    def test_wgs84_range_and_empty_area_checks_are_reported(self):
        connection = self.Connection(
            (False, True, "Valid Geometry", None, "ST_Polygon", 0.0,
             -181.0, 181.0, -91.0, 91.0)
        )
        report = validate_geojson_geometry(
            connection,
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            expected_type="Polygon",
            require_positive_area=True,
        )
        self.assertEqual(
            {issue.code for issue in report.issues},
            {"geometry.coordinate_range", "geometry.area"},
        )


class PublicationAndIIIFTests(unittest.TestCase):
    def test_published_entities_require_bibliographic_links(self):
        self.assertTrue(
            validate_publication_anchoring("entity-1", "draft", ()).valid
        )
        report = validate_publication_anchoring("entity-1", "published", ())
        self.assertEqual(report.issues[0].code, "publication.missing_bibliography")
        self.assertTrue(
            validate_publication_anchoring(
                "entity-1", "published", ("reference-1",)
            ).valid
        )
        self.assertEqual(
            validate_publication_anchoring("entity-1", "review", ()).issues[0].code,
            "publication.invalid_status",
        )

    @patch("validation.iiif.build_opener")
    def test_iiif_manifest_uses_allowlisted_head_request(self, build_opener):
        response = Mock()
        response.status = 200
        response.headers = {"Content-Type": "application/ld+json"}
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        opener = Mock()
        opener.open.return_value = response
        build_opener.return_value = opener

        report = IIIFManifestValidator(frozenset({"iiif.example"})).validate(
            "https://iiif.example/manifest/123"
        )
        self.assertTrue(report.valid)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "HEAD")

    @patch("validation.iiif.build_opener")
    def test_iiif_validator_rejects_untrusted_hosts_before_network_access(
        self, build_opener
    ):
        report = IIIFManifestValidator(frozenset({"iiif.example"})).validate(
            "https://127.0.0.1/manifest"
        )
        self.assertEqual(report.issues[0].code, "iiif.untrusted_manifest_uri")
        build_opener.assert_not_called()

    @patch("validation.iiif.build_opener")
    def test_iiif_validator_rejects_nonstandard_ports(self, build_opener):
        report = IIIFManifestValidator(frozenset({"iiif.example"})).validate(
            "https://iiif.example:8443/manifest"
        )
        self.assertEqual(report.issues[0].code, "iiif.untrusted_manifest_uri")
        build_opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
