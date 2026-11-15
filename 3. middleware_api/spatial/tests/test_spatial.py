import json
import subprocess
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from spatial.geojson import GeoJSONValidationError, validate_linestring
from spatial.lcp import (
    GrassLCPRunner,
    LCPExecutionError,
    LCPRequest,
)
from spatial.paleoclimate import (
    ClimateLayer,
    GeoServerConfig,
    PaleoclimateCatalog,
    PaleoclimateService,
    TooManyClimateSlices,
)


def sample_layers():
    return [
        ClimateLayer(
            layer_id="climate:koppen_12000",
            model="CHELSA-TraCE21k",
            variable="koppen",
            year_start=-12500,
            year_end_exclusive=-11500,
            wms_time="-12000-01-01T00:00:00Z",
            source_uri="https://data.example/chelsa",
            resolution_m=1000,
            unit="class",
        ),
        ClimateLayer(
            layer_id="climate:koppen_11000",
            model="CHELSA-TraCE21k",
            variable="koppen",
            year_start=-11500,
            year_end_exclusive=-10500,
            wms_time="-11000-01-01T00:00:00Z",
            source_uri="https://data.example/chelsa",
            resolution_m=1000,
            unit="class",
        ),
        ClimateLayer(
            layer_id="pmip:temperature_12000",
            model="PMIP4",
            variable="annual_mean_temperature",
            year_start=-12500,
            year_end_exclusive=-11500,
            wms_time="-12000-01-01T00:00:00Z",
            source_uri="https://data.example/pmip",
            resolution_m=50000,
            unit="degree_Celsius",
        ),
    ]


def lcp_request(**overrides):
    values = {
        "movement_category_uri": "https://vocab.example/trade",
        "dem_source_uri": "https://geoserver.example/wcs?coverage=srtm30",
        "dem_resolution_m": 30,
        "start_lon_lat": (44.0, 32.0),
        "end_lon_lat": (45.0, 33.0),
        "energy_model": "tobler_hiking",
        "grass_algorithm": "r.walk",
        "parameter_set_id": uuid4(),
        "notebook_version": "1.0.0",
        "execution_timestamp": datetime.now(timezone.utc),
        "barrier_sources": ("geo_feature_temporal:abc",),
        "parameters": {"slope_factor": 1.0},
    }
    values.update(overrides)
    return LCPRequest(**values)


class GeoJSONTests(unittest.TestCase):
    def test_valid_linestring_is_normalized_and_serializable(self):
        path = validate_linestring(
            {"type": "LineString", "coordinates": [[10, 20], [11, 21]]}
        )
        self.assertEqual(path.as_geojson()["coordinates"], [[10.0, 20.0], [11.0, 21.0]])

    def test_invalid_or_zero_length_linestring_is_rejected(self):
        for geometry in (
            {"type": "LineString", "coordinates": [[0, 0]]},
            {"type": "LineString", "coordinates": [[0, 0], [0, 0]]},
            {"type": "LineString", "coordinates": [[181, 0], [0, 1]]},
        ):
            with self.subTest(geometry=geometry):
                with self.assertRaises(GeoJSONValidationError):
                    validate_linestring(geometry)


class LCPTests(unittest.TestCase):
    def test_request_enforces_dem_and_pandolf_parameters(self):
        with self.assertRaises(ValueError):
            lcp_request(dem_resolution_m=31)
        with self.assertRaises(ValueError):
            lcp_request(
                energy_model="pandolf_load_carrying",
                traveler_weight_kg=70,
            )

    @patch("spatial.lcp.subprocess.run")
    def test_grass_result_builds_movement_vector_writeback(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["configured-grass-adapter"],
            returncode=0,
            stdout=json.dumps(
                {
                    "path_geojson": {
                        "type": "LineString",
                        "coordinates": [[44.0, 32.0], [45.0, 33.0]],
                    },
                    "cost_surface_uri": "s3://analysis/cost.tif",
                    "total_cost": 12.5,
                    "adapter_version": "1",
                    "grass_version": "8.4",
                }
            ),
            stderr="",
        )
        result = GrassLCPRunner(
            ["configured-grass-adapter"],
            allowed_input_hosts=frozenset({"geoserver.example"}),
        ).calculate(lcp_request())
        payload = result.movement_vector_payload()
        self.assertEqual(payload["route_source"], "LCP_computed")
        self.assertEqual(payload["lcp_energy_model"], "tobler_hiking")
        self.assertEqual(payload["lcp_parameters"]["grass_version"], "8.4")
        self.assertFalse(run.call_args.kwargs["shell"])

    @patch("spatial.lcp.subprocess.run")
    def test_invalid_grass_geometry_fails_explicitly(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["configured-grass-adapter"],
            returncode=0,
            stdout=json.dumps(
                {
                    "path_geojson": {
                        "type": "LineString",
                        "coordinates": [[44, 32], [44, 32]],
                    },
                    "cost_surface_uri": "s3://analysis/cost.tif",
                    "total_cost": 12,
                    "adapter_version": "1",
                    "grass_version": "8.4",
                }
            ),
            stderr="",
        )
        with self.assertRaises(LCPExecutionError):
            GrassLCPRunner(
                ["configured-grass-adapter"],
                allowed_input_hosts=frozenset({"geoserver.example"}),
            ).calculate(lcp_request())

    @patch("spatial.lcp.subprocess.run")
    def test_dem_host_must_be_allowlisted_before_adapter_runs(self, run):
        runner = GrassLCPRunner(
            ["configured-grass-adapter"],
            allowed_input_hosts=frozenset({"trusted.example"}),
        )
        with self.assertRaises(LCPExecutionError):
            runner.calculate(lcp_request())
        run.assert_not_called()

    @patch("spatial.lcp.subprocess.run")
    def test_lcp_path_must_match_requested_endpoints(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["configured-grass-adapter"],
            returncode=0,
            stdout=json.dumps(
                {
                    "path_geojson": {
                        "type": "LineString",
                        "coordinates": [[43.0, 32.0], [45.0, 33.0]],
                    },
                    "cost_surface_uri": "s3://analysis/cost.tif",
                    "total_cost": 12,
                    "adapter_version": "1",
                    "grass_version": "8.4",
                }
            ),
            stderr="",
        )
        runner = GrassLCPRunner(
            ["configured-grass-adapter"],
            allowed_input_hosts=frozenset({"geoserver.example"}),
        )
        with self.assertRaises(LCPExecutionError):
            runner.calculate(lcp_request())


class PaleoclimateTests(unittest.TestCase):
    def test_edtf_resolves_overlapping_chelsa_and_pmip_slices(self):
        catalog = PaleoclimateCatalog(sample_layers())
        resolved = catalog.resolve("-12000", variables=frozenset({"koppen"}))
        self.assertEqual([layer.layer_id for layer in resolved], ["climate:koppen_12000"])
        self.assertEqual(
            len(catalog.resolve("-12000", model="PMIP4")),
            1,
        )

    def test_open_range_enforces_slice_cap_without_truncating(self):
        catalog = PaleoclimateCatalog(sample_layers())
        with self.assertRaises(TooManyClimateSlices):
            catalog.resolve("../-9999", max_slices=1)

    def test_numeric_metrics_use_configured_raster_sampler(self):
        class Sampler:
            def sample(self, layer, longitude, latitude):
                self.request = (layer.layer_id, longitude, latitude)
                return 12.5

        sampler = Sampler()
        service = PaleoclimateService(PaleoclimateCatalog(sample_layers()), sampler)
        readings = service.extract_metrics("-12000", 44.0, 32.0, model="PMIP4")
        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0].variable, "annual_mean_temperature")
        self.assertEqual(readings[0].value, 12.5)
        self.assertEqual(sampler.request, ("pmip:temperature_12000", 44.0, 32.0))

    def test_wms_url_encodes_time_and_uses_lon_lat_crs(self):
        layer = sample_layers()[0]
        config = GeoServerConfig(
            "https://maps.example/geoserver/wms",
            frozenset({"maps.example"}),
        )
        url = config.get_map_url(layer, (40, 30, 50, 40))
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["crs"], ["CRS:84"])
        self.assertEqual(query["time"], [layer.wms_time])
        self.assertEqual(query["layers"], [layer.layer_id])


if __name__ == "__main__":
    unittest.main()
