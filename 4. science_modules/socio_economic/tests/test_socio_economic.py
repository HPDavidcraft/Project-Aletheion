import csv
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from socio_economic.silver_equivalence import (
    CommodityObservation,
    EconomicIndexError,
    calculate_silver_equivalence_index,
    read_observations_csv,
    sha256_file,
    write_index_svg,
)
from socio_economic.trade_network import (
    MovementVectorEdge,
    TradeNetworkError,
    analyze_trade_network,
    read_movement_vectors_csv,
    read_participating_sites_csv,
)


def observations():
    region_id = uuid4()
    commodity_uri = "https://vocab.example.test/commodity/barley"
    quantity_reference = uuid4()
    exchange_reference = uuid4()
    common = {
        "commodity_uri": commodity_uri,
        "region_id": region_id,
        "commodity_unit": "standardized basket",
        "quantity_reference_id": quantity_reference,
        "exchange_rate_reference_id": exchange_reference,
    }
    return (
        CommodityObservation(
            observation_id=uuid4(),
            period_label="1000",
            period_order=1,
            quantity_lower=Decimal("10"),
            quantity_upper=Decimal("12"),
            silver_grams_per_unit_lower=Decimal("2"),
            silver_grams_per_unit_upper=Decimal("3"),
            **common,
        ),
        CommodityObservation(
            observation_id=uuid4(),
            period_label="1100",
            period_order=2,
            quantity_lower=Decimal("20"),
            quantity_upper=Decimal("30"),
            silver_grams_per_unit_lower=Decimal("1.8"),
            silver_grams_per_unit_upper=Decimal("2.2"),
            **common,
        ),
    )


class SilverEquivalenceTests(unittest.TestCase):
    def test_silver_ranges_and_baseline_normalization_keep_source_citations(self):
        source = observations()
        report = calculate_silver_equivalence_index(
            source,
            baseline_period="1000",
        )
        baseline, later = report.rows
        self.assertEqual((baseline.silver_grams_lower, baseline.silver_grams_upper), (20, 36))
        self.assertEqual((baseline.index_lower, baseline.index_upper), (100, 100))
        self.assertEqual((later.silver_grams_lower, later.silver_grams_upper), (36, 66))
        self.assertEqual((later.index_lower, later.index_upper), (100, 330))

        payload = report.writeback_payload(
            input_sha256="a" * 64,
            parameter_set_id=uuid4(),
            notebook_revision="notebook:abc123",
            environment_reference="python-3.14;stdlib",
            executed_at=datetime(2026, 11, 14, tzinfo=timezone.utc),
        )
        json.dumps(payload, allow_nan=False)
        self.assertEqual(
            payload["observations"][0]["exchange_rate_reference_id"],
            str(source[0].exchange_rate_reference_id),
        )

    def test_requires_explicit_baseline_and_valid_conversion_ranges(self):
        with self.assertRaises(EconomicIndexError):
            calculate_silver_equivalence_index(observations(), baseline_period="1200")
        with self.assertRaises(EconomicIndexError):
            CommodityObservation(
                observation_id=uuid4(),
                commodity_uri="https://vocab.example.test/commodity/barley",
                region_id=uuid4(),
                period_label="1000",
                period_order=1,
                commodity_unit="basket",
                quantity_lower=Decimal("3"),
                quantity_upper=Decimal("2"),
                silver_grams_per_unit_lower=Decimal("1"),
                silver_grams_per_unit_upper=Decimal("1"),
                quantity_reference_id=uuid4(),
                exchange_rate_reference_id=uuid4(),
            )

    def test_csv_reading_digest_and_time_series_svg(self):
        source = observations()
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "observations.csv"
            fieldnames = [
                "observation_id",
                "commodity_uri",
                "region_id",
                "period_label",
                "period_order",
                "commodity_unit",
                "quantity_lower",
                "quantity_upper",
                "silver_grams_per_unit_lower",
                "silver_grams_per_unit_upper",
                "quantity_reference_id",
                "exchange_rate_reference_id",
            ]
            with input_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for item in source:
                    writer.writerow(
                        {
                            "observation_id": item.observation_id,
                            "commodity_uri": item.commodity_uri,
                            "region_id": item.region_id,
                            "period_label": item.period_label,
                            "period_order": item.period_order,
                            "commodity_unit": item.commodity_unit,
                            "quantity_lower": item.quantity_lower,
                            "quantity_upper": item.quantity_upper,
                            "silver_grams_per_unit_lower": item.silver_grams_per_unit_lower,
                            "silver_grams_per_unit_upper": item.silver_grams_per_unit_upper,
                            "quantity_reference_id": item.quantity_reference_id,
                            "exchange_rate_reference_id": item.exchange_rate_reference_id,
                        }
                    )
            loaded = read_observations_csv(input_path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(
                sha256_file(input_path),
                hashlib.sha256(input_path.read_bytes()).hexdigest(),
            )
            report = calculate_silver_equivalence_index(loaded, baseline_period="1000")
            output_path = Path(directory) / "index.svg"
            write_index_svg(
                report,
                output_path,
                commodity_uri=source[0].commodity_uri,
                region_id=source[0].region_id,
                commodity_unit=source[0].commodity_unit,
            )
            self.assertIn("baseline = 100", output_path.read_text(encoding="utf-8"))


def trade_fixture():
    site_a, site_b, site_c = uuid4(), uuid4(), uuid4()
    cluster_id = uuid4()
    category_uri = "https://vocab.example.test/movement/trade"
    edges = (
        MovementVectorEdge(uuid4(), site_a, site_b, category_uri, "documented"),
        MovementVectorEdge(uuid4(), site_b, site_c, category_uri, "inferred"),
    )
    report = analyze_trade_network(
        cluster_history_id=cluster_id,
        interaction_type="trade",
        analysis_scope="EDTF period 1000/1100; caller-filtered Movement_Vectors",
        participating_site_ids=(site_a, site_b, site_c),
        movement_vectors=edges,
        trade_category_uri=category_uri,
    )
    return report, (site_a, site_b, site_c), edges, category_uri


class TradeNetworkTests(unittest.TestCase):
    def test_directional_metrics_communities_paths_and_network_artifacts(self):
        report, (site_a, site_b, site_c), edges, _ = trade_fixture()
        centrality = {row.site_id: row for row in report.centrality}
        self.assertEqual(centrality[site_b].in_degree, 1)
        self.assertEqual(centrality[site_b].out_degree, 1)
        self.assertAlmostEqual(centrality[site_b].betweenness_centrality, 0.5)
        self.assertEqual(report.shortest_path(site_a, site_c), (site_a, site_b, site_c))
        self.assertIsNone(report.shortest_path(site_c, site_a))
        self.assertEqual(len({row.community_id for row in report.centrality}), 1)
        self.assertEqual(len(report.node_link_data()["links"]), len(edges))
        payload = report.writeback_payload(
            site_membership_sha256="a" * 64,
            movement_vectors_sha256="b" * 64,
            parameter_set_id=uuid4(),
            notebook_revision="network-notebook:abc123",
            environment_reference="python-3.14;stdlib",
            executed_at=datetime(2026, 11, 14, tzinfo=timezone.utc),
        )
        json.dumps(payload, allow_nan=False)

        with tempfile.TemporaryDirectory() as directory:
            paths = report.write_outputs(directory)
            self.assertTrue(all(path.is_file() for path in paths.values()))
            graph = json.loads(paths["graph"].read_text(encoding="utf-8"))
            self.assertTrue(graph["directed"])
            self.assertIn("circular placement is schematic", paths["visualization"].read_text(encoding="utf-8"))
            with self.assertRaises(TradeNetworkError):
                report.write_outputs(directory)

    def test_rejects_non_trade_or_unlinked_vectors(self):
        report, (site_a, site_b, _), edges, category_uri = trade_fixture()
        with self.assertRaises(TradeNetworkError):
            analyze_trade_network(
                cluster_history_id=uuid4(),
                interaction_type="warfare",
                analysis_scope="all",
                participating_site_ids=(site_a, site_b),
                movement_vectors=edges[:1],
                trade_category_uri=category_uri,
            )
        with self.assertRaises(TradeNetworkError):
            analyze_trade_network(
                cluster_history_id=uuid4(),
                interaction_type="trade",
                analysis_scope="all",
                participating_site_ids=(site_a, site_b),
                movement_vectors=edges,
                trade_category_uri=category_uri,
            )
        with self.assertRaises(TradeNetworkError):
            report.shortest_path(uuid4(), site_a)

    def test_reads_movement_vector_csv_without_evaluating_json_attributes(self):
        _, (site_a, site_b, _), edges, category_uri = trade_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "movement.csv"
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "vector_id",
                        "origin_site_id",
                        "destination_site_id",
                        "movement_category_uri",
                        "route_source",
                        "subtype_attributes",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "vector_id": edges[0].vector_id,
                        "origin_site_id": site_a,
                        "destination_site_id": site_b,
                        "movement_category_uri": category_uri,
                        "route_source": "documented",
                        "subtype_attributes": '{"commodity":"grain"}',
                    }
                )
            loaded = read_movement_vectors_csv(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].subtype_attributes["commodity"], "grain")

            sites_path = Path(directory) / "sites.csv"
            with sites_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["site_id"])
                writer.writerow([site_a])
                writer.writerow([site_b])
            self.assertEqual(
                read_participating_sites_csv(sites_path),
                (site_a, site_b),
            )


if __name__ == "__main__":
    unittest.main()
