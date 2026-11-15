"""Reproducible, interval-based settlement population capacity estimates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, localcontext
from uuid import UUID


MODEL_ID = "settlement-capacity-constrained"
MODEL_VERSION = "1.0.0"
_MAX_DECIMAL_DIGITS = 50
_MAX_DECIMAL_EXPONENT = 50


class DemographicModelError(ValueError):
    """Raised when an input, assumption, or provenance record is invalid."""


def _decimal(value: Decimal | int | float, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float)):
        raise DemographicModelError(f"{label} must be a finite number")
    try:
        normalized = value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation as exc:
        raise DemographicModelError(f"{label} must be a finite number") from exc
    if not normalized.is_finite():
        raise DemographicModelError(f"{label} must be a finite number")
    if (
        len(normalized.as_tuple().digits) > _MAX_DECIMAL_DIGITS
        or abs(normalized.adjusted()) > _MAX_DECIMAL_EXPONENT
    ):
        raise DemographicModelError(f"{label} exceeds supported numeric precision")
    return normalized


@dataclass(frozen=True, slots=True)
class NumericRange:
    minimum: Decimal | int | float
    maximum: Decimal | int | float

    def __post_init__(self) -> None:
        minimum = _decimal(self.minimum, "minimum")
        maximum = _decimal(self.maximum, "maximum")
        if minimum > maximum:
            raise DemographicModelError("Range minimum must not exceed its maximum")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)


@dataclass(frozen=True, slots=True)
class DemographicInputs:
    site_id: UUID
    settlement_area_source_id: UUID
    settlement_area_hectares: NumericRange
    inhabited_fraction: NumericRange
    housing_density_dwellings_per_hectare: NumericRange
    household_size_persons_per_dwelling: NumericRange
    carrying_capacity_persons: NumericRange

    def __post_init__(self) -> None:
        if not isinstance(self.site_id, UUID):
            raise DemographicModelError("site_id must be a UUID")
        if not isinstance(self.settlement_area_source_id, UUID):
            raise DemographicModelError("settlement_area_source_id must be a UUID")
        if not isinstance(self.settlement_area_hectares, NumericRange):
            raise DemographicModelError("Settlement area must be an explicit numeric range")
        if not isinstance(self.inhabited_fraction, NumericRange):
            raise DemographicModelError("Inhabited fraction must be an explicit numeric range")
        if not isinstance(self.housing_density_dwellings_per_hectare, NumericRange):
            raise DemographicModelError(
                "Housing density must be an explicit numeric range"
            )
        if not isinstance(self.household_size_persons_per_dwelling, NumericRange):
            raise DemographicModelError(
                "Household size must be an explicit numeric range"
            )
        if not isinstance(self.carrying_capacity_persons, NumericRange):
            raise DemographicModelError(
                "Carrying capacity must be an explicit numeric range"
            )
        if self.settlement_area_hectares.minimum <= 0:
            raise DemographicModelError("Settlement area must be positive")
        if not 0 <= self.inhabited_fraction.minimum <= self.inhabited_fraction.maximum <= 1:
            raise DemographicModelError("Inhabited fraction must lie between 0 and 1")
        if self.housing_density_dwellings_per_hectare.minimum < 0:
            raise DemographicModelError("Housing density cannot be negative")
        if self.household_size_persons_per_dwelling.minimum <= 0:
            raise DemographicModelError("Household size must be positive")
        if self.carrying_capacity_persons.minimum < 0:
            raise DemographicModelError("Carrying capacity cannot be negative")


@dataclass(frozen=True, slots=True)
class DemographicRunProvenance:
    parameter_set_id: UUID
    notebook_version: str
    execution_timestamp: datetime
    bibliography_reference_ids: tuple[UUID, ...]
    model_version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.parameter_set_id, UUID):
            raise DemographicModelError("parameter_set_id must be a UUID")
        if not isinstance(self.notebook_version, str) or not self.notebook_version.strip():
            raise DemographicModelError("notebook_version is required")
        if (
            not isinstance(self.model_version, str)
            or not self.model_version.strip()
        ):
            raise DemographicModelError("model_version is required")
        if (
            not isinstance(self.execution_timestamp, datetime)
            or self.execution_timestamp.tzinfo is None
            or self.execution_timestamp.utcoffset() is None
        ):
            raise DemographicModelError(
                "execution_timestamp must be timezone-aware"
            )
        references = tuple(self.bibliography_reference_ids)
        if not references or any(not isinstance(reference, UUID) for reference in references):
            raise DemographicModelError(
                "At least one bibliography reference UUID is required"
            )
        if len(set(references)) != len(references):
            raise DemographicModelError("Bibliography reference UUIDs must be unique")
        object.__setattr__(self, "bibliography_reference_ids", references)


@dataclass(frozen=True, slots=True)
class PopulationEstimate:
    population_lower_bound: int
    population_upper_bound: int
    housing_capacity_lower: Decimal
    housing_capacity_upper: Decimal
    inputs: DemographicInputs
    provenance: DemographicRunProvenance

    def __post_init__(self) -> None:
        if self.population_lower_bound < 0 or self.population_upper_bound < 0:
            raise DemographicModelError("Population bounds cannot be negative")
        if self.population_lower_bound > self.population_upper_bound:
            raise DemographicModelError("Population lower bound exceeds upper bound")

    def writeback_payload(self) -> dict[str, object]:
        inputs = self.inputs
        provenance = self.provenance
        return {
            "site_id": str(inputs.site_id),
            "population_lower_bound": self.population_lower_bound,
            "population_upper_bound": self.population_upper_bound,
            "population_unit": "persons",
            "model_id": MODEL_ID,
            "model_version": provenance.model_version,
            "parameter_set_id": str(provenance.parameter_set_id),
            "notebook_version": provenance.notebook_version,
            "execution_timestamp": provenance.execution_timestamp.astimezone(
                timezone.utc
            ).isoformat(),
            "bibliography_reference_ids": [
                str(reference)
                for reference in provenance.bibliography_reference_ids
            ],
            "inputs": {
                "settlement_area_source_id": str(inputs.settlement_area_source_id),
                "settlement_area_hectares": _range_payload(
                    inputs.settlement_area_hectares
                ),
                "inhabited_fraction": _range_payload(inputs.inhabited_fraction),
                "housing_density_dwellings_per_hectare": _range_payload(
                    inputs.housing_density_dwellings_per_hectare
                ),
                "household_size_persons_per_dwelling": _range_payload(
                    inputs.household_size_persons_per_dwelling
                ),
                "carrying_capacity_persons": _range_payload(
                    inputs.carrying_capacity_persons
                ),
                "housing_capacity_persons": {
                    "minimum": _decimal_text(self.housing_capacity_lower),
                    "maximum": _decimal_text(self.housing_capacity_upper),
                },
                "constrained_capacity_persons": {
                    "minimum": _decimal_text(
                        min(
                            self.housing_capacity_lower,
                            inputs.carrying_capacity_persons.minimum,
                        )
                    ),
                    "maximum": _decimal_text(
                        min(
                            self.housing_capacity_upper,
                            inputs.carrying_capacity_persons.maximum,
                        )
                    ),
                },
                "rounding": "outward_to_whole_person",
            },
        }

    def to_json(self) -> str:
        return json.dumps(
            self.writeback_payload(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        )


class SettlementPopulationModel:
    """Estimate a capacity range constrained by housing and carrying limits.

    The lower and upper housing capacities are products of the corresponding
    input range bounds. The estimated range is constrained at each bound by
    the matching carrying-capacity bound, then rounded outward to whole people.
    """

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def estimate(
        self,
        inputs: DemographicInputs,
        provenance: DemographicRunProvenance,
    ) -> PopulationEstimate:
        if not isinstance(inputs, DemographicInputs):
            raise DemographicModelError("inputs must be a DemographicInputs record")
        if not isinstance(provenance, DemographicRunProvenance):
            raise DemographicModelError(
                "provenance must be a DemographicRunProvenance record"
            )
        with localcontext() as context:
            context.prec = 250
            housing_low = (
                inputs.settlement_area_hectares.minimum
                * inputs.inhabited_fraction.minimum
                * inputs.housing_density_dwellings_per_hectare.minimum
                * inputs.household_size_persons_per_dwelling.minimum
            )
            housing_high = (
                inputs.settlement_area_hectares.maximum
                * inputs.inhabited_fraction.maximum
                * inputs.housing_density_dwellings_per_hectare.maximum
                * inputs.household_size_persons_per_dwelling.maximum
            )
            bounded_low = min(
                housing_low, inputs.carrying_capacity_persons.minimum
            )
            bounded_high = min(
                housing_high, inputs.carrying_capacity_persons.maximum
            )
            population_low = int(
                bounded_low.to_integral_value(rounding=ROUND_FLOOR)
            )
            population_high = int(
                bounded_high.to_integral_value(rounding=ROUND_CEILING)
            )
        return PopulationEstimate(
            population_lower_bound=population_low,
            population_upper_bound=population_high,
            housing_capacity_lower=housing_low,
            housing_capacity_upper=housing_high,
            inputs=inputs,
            provenance=provenance,
        )


def _range_payload(value: NumericRange) -> dict[str, str]:
    return {
        "minimum": _decimal_text(value.minimum),
        "maximum": _decimal_text(value.maximum),
    }


def _decimal_text(value: Decimal) -> str:
    lexical = format(value, "f")
    if "." in lexical:
        lexical = lexical.rstrip("0").rstrip(".")
    return lexical if lexical not in {"", "-0", "+0"} else "0"
