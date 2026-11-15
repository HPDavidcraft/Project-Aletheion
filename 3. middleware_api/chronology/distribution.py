"""Validation and display transformations for temporal probability curves."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


class DistributionValidationError(ValueError):
    """Raised when a temporal probability distribution is malformed."""


@dataclass(frozen=True, slots=True)
class ProbabilityPoint:
    year: float
    probability: float


@dataclass(frozen=True, slots=True)
class TemporalDistribution:
    p_start: float
    p_end: float
    probability_curve: tuple[ProbabilityPoint, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.p_start, bool)
            or isinstance(self.p_end, bool)
            or not isfinite(self.p_start)
            or not isfinite(self.p_end)
        ):
            raise DistributionValidationError("Distribution bounds must be finite")
        if self.p_start > self.p_end:
            raise DistributionValidationError("p_start must not exceed p_end")
        if not self.probability_curve:
            raise DistributionValidationError("Probability curve cannot be empty")

        previous_year: float | None = None
        for point in self.probability_curve:
            if (
                isinstance(point.year, bool)
                or isinstance(point.probability, bool)
                or not isfinite(point.year)
                or not isfinite(point.probability)
            ):
                raise DistributionValidationError(
                    "Probability points must contain finite numeric values"
                )
            if point.year < self.p_start or point.year > self.p_end:
                raise DistributionValidationError(
                    "Every probability point must lie within the distribution bounds"
                )
            if not 0 <= point.probability <= 1:
                raise DistributionValidationError(
                    "Point probabilities must be between 0 and 1"
                )
            if previous_year is not None and point.year <= previous_year:
                raise DistributionValidationError(
                    "Probability years must be strictly increasing"
                )
            previous_year = point.year

    @classmethod
    def from_pairs(
        cls,
        p_start: float,
        p_end: float,
        pairs: Iterable[tuple[float, float]],
    ) -> TemporalDistribution:
        return cls(
            p_start=p_start,
            p_end=p_end,
            probability_curve=tuple(
                ProbabilityPoint(year=year, probability=probability)
                for year, probability in pairs
            ),
        )

    def shifted(self, year_offset: int) -> TemporalDistribution:
        """Return a display-only offset copy without mutating source chronology."""
        return TemporalDistribution(
            p_start=self.p_start + year_offset,
            p_end=self.p_end + year_offset,
            probability_curve=tuple(
                ProbabilityPoint(
                    year=point.year + year_offset,
                    probability=point.probability,
                )
                for point in self.probability_curve
            ),
        )

    def low_probability_years(self, threshold: float = 0.3) -> tuple[float, ...]:
        if not isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        return tuple(
            point.year
            for point in self.probability_curve
            if point.probability < threshold
        )
