import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from demographic_modeling.model import (
    DemographicInputs,
    DemographicModelError,
    DemographicRunProvenance,
    NumericRange,
    SettlementPopulationModel,
)


def inputs(**overrides):
    values = {
        "site_id": uuid4(),
        "settlement_area_source_id": uuid4(),
        "settlement_area_hectares": NumericRange(10, 12),
        "inhabited_fraction": NumericRange(0.5, 0.75),
        "housing_density_dwellings_per_hectare": NumericRange(20, 25),
        "household_size_persons_per_dwelling": NumericRange(2, 4),
        "carrying_capacity_persons": NumericRange(300, 700),
    }
    values.update(overrides)
    return DemographicInputs(**values)


def provenance(**overrides):
    values = {
        "parameter_set_id": uuid4(),
        "notebook_version": "1.0.0",
        "execution_timestamp": datetime(2026, 11, 14, tzinfo=timezone.utc),
        "bibliography_reference_ids": (uuid4(),),
    }
    values.update(overrides)
    return DemographicRunProvenance(**values)


class SettlementPopulationTests(unittest.TestCase):
    def test_capacity_range_uses_area_density_occupancy_and_carrying_limits(self):
        result = SettlementPopulationModel().estimate(inputs(), provenance())
        self.assertEqual(result.housing_capacity_lower, Decimal("200.0"))
        self.assertEqual(result.housing_capacity_upper, Decimal("900.00"))
        self.assertEqual(result.population_lower_bound, 200)
        self.assertEqual(result.population_upper_bound, 700)

    def test_population_bounds_round_outward_and_retain_full_input_ranges(self):
        result = SettlementPopulationModel().estimate(
            inputs(
                settlement_area_hectares=NumericRange(Decimal("1.1"), Decimal("1.2")),
                inhabited_fraction=NumericRange(1, 1),
                housing_density_dwellings_per_hectare=NumericRange(1, 1),
                household_size_persons_per_dwelling=NumericRange(
                    Decimal("1.5"), Decimal("2.2")
                ),
                carrying_capacity_persons=NumericRange(1, 10),
            ),
            provenance(),
        )
        self.assertEqual(result.population_lower_bound, 1)
        self.assertEqual(result.population_upper_bound, 3)
        payload = result.writeback_payload()
        self.assertEqual(
            payload["inputs"]["household_size_persons_per_dwelling"],
            {"minimum": "1.5", "maximum": "2.2"},
        )
        self.assertEqual(
            payload["inputs"]["constrained_capacity_persons"],
            {"minimum": "1", "maximum": "2.64"},
        )
        json.dumps(payload, allow_nan=False)

    def test_ranges_and_provenance_are_required_and_validated(self):
        with self.assertRaises(DemographicModelError):
            NumericRange(5, 4)
        with self.assertRaises(DemographicModelError):
            inputs(inhabited_fraction=NumericRange(0.2, 1.01))
        with self.assertRaises(DemographicModelError):
            provenance(bibliography_reference_ids=())
        with self.assertRaises(DemographicModelError):
            provenance(execution_timestamp=datetime(2026, 1, 1))

    def test_carrying_capacity_can_constrain_both_range_bounds(self):
        result = SettlementPopulationModel().estimate(
            inputs(carrying_capacity_persons=NumericRange(100, 150)),
            provenance(),
        )
        self.assertEqual(
            (result.population_lower_bound, result.population_upper_bound),
            (100, 150),
        )


if __name__ == "__main__":
    unittest.main()
