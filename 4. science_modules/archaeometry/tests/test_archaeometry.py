import json
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from archaeometry.analysis import (
    AnalysisTechnique,
    ArchaeometryValidationError,
    MaterialAnalysisEvent,
    validate_technique_results,
)
from archaeometry.spectrum import (
    SpectrumImportError,
    parse_spectrum_csv,
    read_spectrum_csv,
    resample_linear,
)


class AnalysisResultTests(unittest.TestCase):
    def test_elemental_techniques_validate_percentage_values(self):
        for technique in ("XRF", "pXRF", "SEM-EDS", "INAA"):
            with self.subTest(technique=technique):
                result = validate_technique_results(
                    technique,
                    {"elemental_composition": {"Si": 44.1, "O": 55.9}},
                )
                self.assertEqual(result["elemental_composition"]["Si"], 44.1)

        self.assertEqual(
            validate_technique_results(
                "XRF", {"elemental_composition": {"Si": 40.0}}
            )["elemental_composition"],
            {"Si": 40.0},
        )
        with self.assertRaises(ArchaeometryValidationError):
            validate_technique_results(
                "XRF", {"elemental_composition": {"Si": 100.1}}
            )
        with self.assertRaises(ArchaeometryValidationError):
            validate_technique_results(
                "XRF", {"elemental_composition": {"Xx": 1.0}}
            )

    def test_xrd_and_ftir_use_distinct_result_templates(self):
        xrd = validate_technique_results(
            "XRD",
            {
                "phases": [
                    {
                        "phase": "quartz",
                        "reference_pattern": "fixture pattern",
                        "abundance_wt_percent": 75.0,
                    }
                ]
            },
        )
        self.assertEqual(xrd["phases"][0]["phase"], "quartz")
        ftir = validate_technique_results(
            "FTIR",
            {
                "diagnostic_bands": [
                    {
                        "wavenumber_cm1": 1025.0,
                        "intensity": 0.83,
                        "assignment": "analyst-authored assignment",
                    }
                ]
            },
        )
        self.assertEqual(len(ftir["diagnostic_bands"]), 1)
        with self.assertRaises(ArchaeometryValidationError):
            validate_technique_results(
                "XRD", {"elemental_composition": {"Si": 50}}
            )

    def test_analysis_writeback_requires_file_integrity_and_analyst_provenance(self):
        values = {
            "event_id": uuid4(),
            "find_id": uuid4(),
            "technique": AnalysisTechnique.PXRF,
            "analyst_id": uuid4(),
            "analyst_name": "Analyst One",
            "performed_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "raw_instrument_file_uri": "s3://pleroma-lab/raw/sample-1.csv",
            "raw_file_sha256": "A" * 64,
            "report_media_asset_id": uuid4(),
            "results": {"elemental_composition": {"Fe": 12.5}},
            "pipeline_version": "1.0.0",
            "processing_parameters": {"normalization": "instrument-reported"},
        }
        event = MaterialAnalysisEvent(**values)
        payload = event.writeback_payload()
        self.assertEqual(payload["raw_file_sha256"], "a" * 64)
        self.assertEqual(payload["analyst_name"], "Analyst One")
        self.assertIn("report_media_asset_id", payload)
        json.dumps(payload, allow_nan=False)
        with self.assertRaises(TypeError):
            event.results["elemental_composition"]["Fe"] = 101
        for field, invalid_value in (
            ("analyst_name", ""),
            ("raw_instrument_file_uri", "https://files.example/raw.csv"),
            ("raw_file_sha256", "bad"),
        ):
            with self.subTest(field=field), self.assertRaises(
                ArchaeometryValidationError
            ):
                MaterialAnalysisEvent(**{**values, field: invalid_value})


class SpectrumTests(unittest.TestCase):
    def test_descending_csv_axis_is_canonicalized_and_interpolated(self):
        spectrum = parse_spectrum_csv(
            "wavenumber,intensity\n3000,1\n2000,3\n1000,1\n",
            axis_column="wavenumber",
            intensity_column="intensity",
            axis_name="wavenumber",
            axis_unit="cm-1",
            source_sha256="a" * 64,
        )
        self.assertEqual(spectrum.source_axis_direction, "descending")
        self.assertEqual([point.axis for point in spectrum.points], [1000, 2000, 3000])
        resampled = resample_linear(spectrum, (1000, 1500, 2500, 3000))
        self.assertEqual(resampled.source_axis_direction, "derived")
        self.assertEqual(
            [point.intensity for point in resampled.points], [1, 2, 2, 1]
        )

    def test_nonmonotonic_and_nonfinite_spectra_are_rejected(self):
        with self.assertRaises(SpectrumImportError):
            parse_spectrum_csv(
                "x,y\n1,1\n3,2\n2,3\n",
                axis_column="x",
                intensity_column="y",
                axis_name="axis",
                axis_unit="unit",
                source_sha256="a" * 64,
            )
        with self.assertRaises(SpectrumImportError):
            parse_spectrum_csv(
                "x,y\n1,1\n2,nan\n",
                axis_column="x",
                intensity_column="y",
                axis_name="axis",
                axis_unit="unit",
                source_sha256="a" * 64,
            )

    def test_spectrum_resampling_refuses_extrapolation(self):
        spectrum = parse_spectrum_csv(
            "x,y\n1,10\n2,20\n",
            axis_column="x",
            intensity_column="y",
            axis_name="axis",
            axis_unit="unit",
            source_sha256="a" * 64,
        )
        with self.assertRaises(ValueError):
            resample_linear(spectrum, (0, 1))

    def test_spectrum_file_loader_checks_open_format_and_hashes_source(self):
        import hashlib
        import tempfile
        from pathlib import Path

        source = b"x,intensity\n1,10\n2,20\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spectrum.csv"
            path.write_bytes(source)
            spectrum = read_spectrum_csv(
                path,
                axis_column="x",
                intensity_column="intensity",
                axis_name="axis",
                axis_unit="unit",
            )
        self.assertEqual(spectrum.source_sha256, hashlib.sha256(source).hexdigest())


if __name__ == "__main__":
    unittest.main()
