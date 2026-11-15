import json
import subprocess
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from chronology.chronology_sets import (
    ChronologyAssertion,
    ChronologySet,
    display_assertion,
)
from chronology.distribution import (
    DistributionValidationError,
    TemporalDistribution,
)
from chronology.edtf import EDTFValidationError, parse_edtf
from chronology.oxcal import OxCalExecutionError, OxCalRequest, OxCalRunner


class EDTFTests(unittest.TestCase):
    def test_guideline_examples_normalize_to_inclusive_years(self):
        examples = {
            "1200": (1200, 1200),
            "1200/1250": (1200, 1250),
            "1200/": (1200, None),
            "../1200": (None, 1200),
            "120X": (1200, 1209),
            "12XX": (1200, 1299),
            "-1200": (-1200, -1200),
        }
        for value, expected in examples.items():
            with self.subTest(value=value):
                interval = parse_edtf(value).intervals[0]
                self.assertEqual(
                    (interval.start_year, interval.end_year),
                    expected,
                )

    def test_approximation_is_explicit_and_uncertainty_is_not_invented(self):
        self.assertEqual(parse_edtf("1200~").year_bounds, (1190, 1211))
        uncertain = parse_edtf("1200?")
        self.assertEqual(uncertain.year_bounds, (1200, 1201))
        self.assertTrue(uncertain.uncertain)
        self.assertEqual(parse_edtf("{1200,1210}").year_bounds, (1200, 1211))

    def test_invalid_or_unsupported_values_fail_closed(self):
        for value in (
            "Late Bronze Age",
            "1201/1200",
            "1200/../1201",
            "{1200}",
            "../",
            "/1200",
        ):
            with self.subTest(value=value):
                with self.assertRaises(EDTFValidationError):
                    parse_edtf(value)

    def test_month_and_day_are_calendar_validated(self):
        self.assertEqual(parse_edtf("1200-02").precision, "month")
        with self.assertRaises(EDTFValidationError):
            parse_edtf("1200-02-30")


class DistributionTests(unittest.TestCase):
    def test_invalid_probability_order_and_bounds_are_rejected(self):
        with self.assertRaises(DistributionValidationError):
            TemporalDistribution.from_pairs(1, 3, [(2, 0.5), (1, 0.4)])
        with self.assertRaises(DistributionValidationError):
            TemporalDistribution.from_pairs(1, 3, [(2, 1.1)])

    def test_chronology_offset_is_display_only_and_low_certainty_is_flagged(self):
        distribution = TemporalDistribution.from_pairs(
            100, 102, [(100, 0.2), (101, 0.8), (102, 0.1)]
        )
        chronology_set = ChronologySet(uuid4(), "High chronology", year_offset=25)
        assertion = ChronologyAssertion(
            uuid4(), chronology_set.id, uuid4(), certainty_score=0.49
        )
        displayed = display_assertion(chronology_set, assertion, distribution)
        self.assertEqual(displayed.distribution.p_start, 125)
        self.assertEqual(displayed.distribution.probability_curve[0].year, 125)
        self.assertTrue(displayed.uncertainty_indicator)
        self.assertEqual(distribution.p_start, 100)


class OxCalAdapterTests(unittest.TestCase):
    def setUp(self):
        self.request = OxCalRequest(
            sample_id=uuid4(),
            raw_date_bp=3200,
            error_margin_1sigma=30,
            curve_code="IntCal20",
            parameter_set_id=uuid4(),
            notebook_version="1.2.0",
            parameters={"model": "single_sample"},
            execution_timestamp=datetime.now(timezone.utc),
        )

    @patch("chronology.oxcal.subprocess.run")
    def test_subprocess_uses_json_and_returns_validated_result(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["configured-adapter"],
            returncode=0,
            stdout=json.dumps(
                {
                    "software_name": "OxCal",
                    "software_version": "4.4",
                    "distribution": {
                        "p_start": -1250,
                        "p_end": -1200,
                        "probability_curve": [[-1250, 0.2], [-1200, 0.8]],
                    },
                    "result_uri": "s3://results/calibration.json",
                }
            ),
            stderr="",
        )
        result = OxCalRunner(["configured-adapter"]).calibrate(self.request)
        self.assertEqual(result.software_version, "4.4")
        self.assertEqual(result.distribution.p_start, -1250)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(
            json.loads(run.call_args.kwargs["input"])["curve_code"],
            "IntCal20",
        )

    @patch("chronology.oxcal.subprocess.run")
    def test_nonzero_adapter_exit_is_reported(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["configured-adapter"],
            returncode=2,
            stdout="",
            stderr="calibration failed",
        )
        with self.assertRaises(OxCalExecutionError):
            OxCalRunner(["configured-adapter"]).calibrate(self.request)

    @patch("chronology.oxcal.subprocess.run")
    def test_malformed_probability_curve_is_rejected(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["configured-adapter"],
            returncode=0,
            stdout=json.dumps(
                {
                    "software_name": "OxCal",
                    "software_version": "4.4",
                    "distribution": {
                        "p_start": 100,
                        "p_end": 110,
                        "probability_curve": [[105]],
                    },
                }
            ),
            stderr="",
        )
        with self.assertRaises(OxCalExecutionError):
            OxCalRunner(["configured-adapter"]).calibrate(self.request)


if __name__ == "__main__":
    unittest.main()
