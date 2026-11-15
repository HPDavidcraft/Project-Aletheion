"""EDTF range and stratigraphic superposition consistency checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from chronology.edtf import EDTFDate, EDTFValidationError, YearInterval, parse_edtf

from .common import ValidationIssue, ValidationReport
from .harris import EntityId, StratigraphicRelationship


def validate_temporal_order(
    start_edtf: str | None,
    end_edtf: str | None,
    *,
    entity_id: EntityId | None = None,
) -> ValidationReport:
    """Require every possible end date to be later than every start date."""
    if start_edtf is None or end_edtf is None:
        return ValidationReport()
    start = _parse_date(start_edtf, "start", entity_id)
    end = _parse_date(end_edtf, "end", entity_id)
    issues = [*start.issues, *end.issues]
    if issues:
        return ValidationReport(tuple(issues))

    start_latest = _latest_bound(start.value)
    end_earliest = _earliest_bound(end.value)
    if start_latest is None or end_earliest is None:
        return ValidationReport(
            (
                ValidationIssue(
                    "temporal.unbounded_order",
                    "Open EDTF bounds do not establish chronological start/end order",
                    _ids(entity_id),
                ),
            )
        )
    if end_earliest <= start_latest:
        return ValidationReport(
            (
                ValidationIssue(
                    "temporal.start_end_order",
                    "End_Date must be later than Start_Date across their EDTF uncertainty bounds",
                    _ids(entity_id),
                ),
            )
        )
    return ValidationReport()


def validate_stratigraphic_temporal_consistency(
    unit_dates: Mapping[EntityId, str | None],
    relationships: Sequence[StratigraphicRelationship],
) -> ValidationReport:
    """Check that dated superposition and contemporary edges agree with EDTF."""
    parsed: dict[str, EDTFDate] = {}
    issues: list[ValidationIssue] = []
    for unit_id, date_value in unit_dates.items():
        if date_value is None:
            continue
        try:
            parsed[str(unit_id)] = parse_edtf(date_value)
        except EDTFValidationError:
            issues.append(
                ValidationIssue(
                    "temporal.invalid_stratigraphic_date",
                    "Stratigraphic unit has an invalid EDTF date",
                    (str(unit_id),),
                )
            )

    for relationship in relationships:
        unit_id = str(relationship.unit_id)
        related_id = str(relationship.related_unit_id)
        unit_date = parsed.get(unit_id)
        related_date = parsed.get(related_id)
        if unit_date is None or related_date is None:
            continue
        if relationship.relationship_type == "above":
            earlier_id, earlier, later_id, later = (
                related_id,
                related_date,
                unit_id,
                unit_date,
            )
        elif relationship.relationship_type == "below":
            earlier_id, earlier, later_id, later = (
                unit_id,
                unit_date,
                related_id,
                related_date,
            )
        elif relationship.relationship_type == "contemporary":
            if not _dates_overlap(unit_date, related_date):
                issues.append(
                    ValidationIssue(
                        "temporal.contemporary_date_conflict",
                        "Contemporary stratigraphic units have non-overlapping EDTF dates",
                        (unit_id, related_id),
                    )
                )
            continue
        else:
            continue

        earlier_latest = _latest_bound(earlier)
        later_earliest = _earliest_bound(later)
        if (
            earlier_latest is not None
            and later_earliest is not None
            and later_earliest <= earlier_latest
        ):
            issues.append(
                ValidationIssue(
                    "temporal.superposition_conflict",
                    "EDTF dates conflict with stratigraphic superposition",
                    (earlier_id, later_id),
                )
            )
    return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class _ParsedDate:
    value: EDTFDate | None
    issues: tuple[ValidationIssue, ...]


def _parse_date(
    value: str, label: str, entity_id: EntityId | None
) -> _ParsedDate:
    try:
        return _ParsedDate(parse_edtf(value), ())
    except EDTFValidationError:
        return _ParsedDate(
            None,
            (
                ValidationIssue(
                    f"temporal.invalid_{label}_date",
                    f"{label.capitalize()}_Date must be a valid EDTF expression",
                    _ids(entity_id),
                ),
            ),
        )


def _latest_bound(date_value: EDTFDate | None) -> int | None:
    if date_value is None or any(
        interval.end_year is None for interval in date_value.intervals
    ):
        return None
    return max(interval.end_year for interval in date_value.intervals if interval.end_year is not None)


def _earliest_bound(date_value: EDTFDate | None) -> int | None:
    if date_value is None or any(
        interval.start_year is None for interval in date_value.intervals
    ):
        return None
    return min(
        interval.start_year
        for interval in date_value.intervals
        if interval.start_year is not None
    )


def _dates_overlap(first: EDTFDate, second: EDTFDate) -> bool:
    return any(
        _intervals_overlap(first_interval, second_interval)
        for first_interval in first.intervals
        for second_interval in second.intervals
    )


def _intervals_overlap(first: YearInterval, second: YearInterval) -> bool:
    return not (
        first.end_year is not None
        and second.start_year is not None
        and first.end_year < second.start_year
    ) and not (
        second.end_year is not None
        and first.start_year is not None
        and second.end_year < first.start_year
    )


def _ids(entity_id: EntityId | None) -> tuple[str, ...]:
    return () if entity_id is None else (str(entity_id),)
