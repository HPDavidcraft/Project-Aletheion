"""A deliberately bounded EDTF parser for the project's year-based date profile.

The API must use a standards-complete EDTF implementation if it needs forms
outside the documented project subset; unsupported expressions fail closed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


class EDTFValidationError(ValueError):
    """Raised when an EDTF value is invalid or outside the supported profile."""


@dataclass(frozen=True, slots=True)
class YearInterval:
    """Inclusive endpoints; None represents an open endpoint."""

    start_year: int | None
    end_year: int | None

    def __post_init__(self) -> None:
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise EDTFValidationError("Date interval start must not exceed its end")

    @property
    def int4range_bounds(self) -> tuple[int | None, int | None]:
        """Return PostgreSQL [inclusive, exclusive) bounds."""
        return (
            self.start_year,
            None if self.end_year is None else self.end_year + 1,
        )


@dataclass(frozen=True, slots=True)
class EDTFDate:
    raw: str
    intervals: tuple[YearInterval, ...]
    precision: str
    approximate: bool = False
    uncertain: bool = False

    @property
    def year_bounds(self) -> tuple[int | None, int | None]:
        """Return an envelope for indexing; alternatives remain in intervals."""
        lower = (
            None
            if any(interval.start_year is None for interval in self.intervals)
            else min(interval.start_year for interval in self.intervals if interval.start_year is not None)
        )
        upper = (
            None
            if any(interval.end_year is None for interval in self.intervals)
            else max(interval.end_year for interval in self.intervals if interval.end_year is not None)
        )
        return lower, None if upper is None else upper + 1


@dataclass(frozen=True, slots=True)
class _Atom:
    interval: YearInterval
    precision: str
    approximate: bool
    uncertain: bool


_YEAR = re.compile(
    r"(?P<year>(?:[+-]\d{4,}|\d{4}))(?P<qualifier>[~?%]?)\Z"
)
_DECADE = re.compile(r"(?P<prefix>\d{3})X\Z")
_CENTURY = re.compile(r"(?P<prefix>\d{2})XX\Z")
_MONTH = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})\Z")
_DAY = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\Z"
)


def _parse_atom(value: str, approximate_margin: int) -> _Atom:
    match = _YEAR.fullmatch(value)
    if match:
        year = int(match.group("year"))
        qualifier = match.group("qualifier")
        approximate = qualifier in ("~", "%")
        uncertain = qualifier in ("?", "%")
        margin = approximate_margin if approximate else 0
        return _Atom(
            interval=YearInterval(year - margin, year + margin),
            precision="year",
            approximate=approximate,
            uncertain=uncertain,
        )

    match = _DECADE.fullmatch(value)
    if match:
        start = int(match.group("prefix")) * 10
        return _Atom(YearInterval(start, start + 9), "decade", False, False)

    match = _CENTURY.fullmatch(value)
    if match:
        start = int(match.group("prefix")) * 100
        return _Atom(YearInterval(start, start + 99), "century", False, False)

    match = _DAY.fullmatch(value)
    if match:
        try:
            date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError as exc:
            raise EDTFValidationError(f"Invalid calendar date: {value}") from exc
        year = int(match.group("year"))
        return _Atom(YearInterval(year, year), "day", False, False)

    match = _MONTH.fullmatch(value)
    if match:
        year, month = int(match.group("year")), int(match.group("month"))
        if not 1 <= month <= 12:
            raise EDTFValidationError(f"Invalid calendar month: {value}")
        return _Atom(YearInterval(year, year), "month", False, False)

    raise EDTFValidationError(
        f"Unsupported or malformed EDTF value: {value!r}"
    )


def parse_edtf(value: str, *, approximate_margin: int = 10) -> EDTFDate:
    """Parse supported EDTF year/date forms into normalized inclusive intervals.

    Approximate years use the project's documented ±5–10 year convention,
    defaulting to ±10. Uncertain-only years retain their stated year bounds and
    uncertainty flag; no probability curve is invented.
    """
    if not isinstance(value, str) or not value or value != value.strip():
        raise EDTFValidationError("EDTF value must be a non-empty trimmed string")
    if (
        not isinstance(approximate_margin, int)
        or isinstance(approximate_margin, bool)
        or approximate_margin < 0
    ):
        raise ValueError("approximate_margin must be a non-negative integer")

    if value.startswith("{") and value.endswith("}"):
        members = value[1:-1].split(",")
        if len(members) < 2 or any(not member for member in members):
            raise EDTFValidationError("EDTF set expressions need at least two values")
        atoms = tuple(_parse_atom(member, approximate_margin) for member in members)
        if len({atom.interval for atom in atoms}) != len(atoms):
            raise EDTFValidationError("EDTF set expressions cannot repeat a value")
        return EDTFDate(
            raw=value,
            intervals=tuple(atom.interval for atom in atoms),
            precision="set",
            approximate=any(atom.approximate for atom in atoms),
            uncertain=any(atom.uncertain for atom in atoms),
        )

    if "/" in value:
        if value.count("/") != 1:
            raise EDTFValidationError("EDTF range must contain exactly one slash")
        start_text, end_text = value.split("/", maxsplit=1)
        if not start_text and end_text:
            raise EDTFValidationError("An open EDTF range start must use '..'")
        if start_text in ("", "..") and not end_text:
            raise EDTFValidationError("An EDTF range cannot have two open endpoints")
        start = (
            None
            if start_text == ".."
            else _parse_atom(start_text, approximate_margin).interval.start_year
            if start_text
            else None
        )
        end_atom = _parse_atom(end_text, approximate_margin) if end_text else None
        end = (
            None
            if end_atom is None
            else end_atom.interval.end_year
        )
        if start is None and start_text not in ("", ".."):
            raise EDTFValidationError("Invalid open EDTF range start")
        if end_atom is not None and start is not None and end is not None and start > end:
            raise EDTFValidationError("EDTF range start must not exceed its end")
        return EDTFDate(
            raw=value,
            intervals=(YearInterval(start, end),),
            precision="range",
            approximate=(
                (start_text not in ("", "..")
                 and _parse_atom(start_text, approximate_margin).approximate)
                or (end_atom is not None and end_atom.approximate)
            ),
            uncertain=(
                (start_text not in ("", "..")
                 and _parse_atom(start_text, approximate_margin).uncertain)
                or (end_atom is not None and end_atom.uncertain)
            ),
        )

    atom = _parse_atom(value, approximate_margin)
    return EDTFDate(
        raw=value,
        intervals=(atom.interval,),
        precision=atom.precision,
        approximate=atom.approximate,
        uncertain=atom.uncertain,
    )
