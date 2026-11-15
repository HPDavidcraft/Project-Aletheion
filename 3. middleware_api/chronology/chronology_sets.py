"""Chronology-set display operations; offsets never rewrite source results."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from uuid import UUID

from .distribution import TemporalDistribution


LOW_CERTAINTY_THRESHOLD = 0.5


@dataclass(frozen=True, slots=True)
class ChronologySet:
    id: UUID
    name: str
    year_offset: int = 0
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Chronology set name is required")
        if not isinstance(self.year_offset, int) or isinstance(self.year_offset, bool):
            raise ValueError("year_offset must be an integer")


@dataclass(frozen=True, slots=True)
class ChronologyAssertion:
    id: UUID
    chronology_set_id: UUID
    calibration_result_id: UUID
    certainty_score: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.certainty_score, bool)
            or not isfinite(self.certainty_score)
            or not 0 <= self.certainty_score <= 1
        ):
            raise ValueError("certainty_score must be between 0 and 1")

    @property
    def has_low_certainty(self) -> bool:
        return self.certainty_score < LOW_CERTAINTY_THRESHOLD


@dataclass(frozen=True, slots=True)
class DisplayChronology:
    chronology_set_id: UUID
    assertion_id: UUID
    year_offset: int
    certainty_score: float
    uncertainty_indicator: bool
    distribution: TemporalDistribution


def display_assertion(
    chronology_set: ChronologySet,
    assertion: ChronologyAssertion,
    source_distribution: TemporalDistribution,
) -> DisplayChronology:
    if assertion.chronology_set_id != chronology_set.id:
        raise ValueError("Assertion does not belong to the selected chronology set")
    return DisplayChronology(
        chronology_set_id=chronology_set.id,
        assertion_id=assertion.id,
        year_offset=chronology_set.year_offset,
        certainty_score=assertion.certainty_score,
        uncertainty_indicator=assertion.has_low_certainty,
        distribution=source_distribution.shifted(chronology_set.year_offset),
    )
