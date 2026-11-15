"""Bounded CSV spectrum ingestion and deterministic linear resampling."""

from __future__ import annotations

import bisect
import csv
import hashlib
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class SpectrumImportError(ValueError):
    """Raised when an open-format spectrum cannot be safely parsed."""


@dataclass(frozen=True, slots=True)
class SpectrumPoint:
    axis: float
    intensity: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.axis, bool)
            or isinstance(self.intensity, bool)
            or not isinstance(self.axis, (int, float))
            or not isinstance(self.intensity, (int, float))
            or not math.isfinite(self.axis)
            or not math.isfinite(self.intensity)
        ):
            raise SpectrumImportError("Spectrum coordinates and intensities must be finite")


@dataclass(frozen=True, slots=True)
class Spectrum:
    axis_name: str
    axis_unit: str
    points: tuple[SpectrumPoint, ...]
    source_sha256: str
    source_axis_direction: str

    def __post_init__(self) -> None:
        if not self.axis_name.strip() or not self.axis_unit.strip():
            raise SpectrumImportError("Spectrum axis name and unit are required")
        if len(self.points) < 2:
            raise SpectrumImportError("A spectrum requires at least two points")
        if any(
            previous.axis >= current.axis
            for previous, current in zip(self.points, self.points[1:])
        ):
            raise SpectrumImportError("Canonical spectrum axis must be strictly increasing")
        if self.source_axis_direction not in {"ascending", "descending", "derived"}:
            raise SpectrumImportError("Invalid source axis direction")
        if (
            len(self.source_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.source_sha256)
        ):
            raise SpectrumImportError("Spectrum source checksum must be a SHA-256 digest")


def read_spectrum_csv(
    source_path: str | Path,
    *,
    axis_column: str,
    intensity_column: str,
    axis_name: str,
    axis_unit: str,
    max_file_bytes: int = 25_000_000,
    max_points: int = 250_000,
) -> Spectrum:
    """Read two selected numeric columns from an open UTF-8 CSV spectrum."""
    path = Path(source_path)
    if path.suffix.casefold() != ".csv":
        raise SpectrumImportError("Only open CSV spectra are accepted")
    if (
        isinstance(max_file_bytes, bool)
        or not isinstance(max_file_bytes, int)
        or max_file_bytes <= 0
    ):
        raise ValueError("max_file_bytes must be positive")
    if isinstance(max_points, bool) or not isinstance(max_points, int) or max_points < 2:
        raise ValueError("max_points must be an integer of at least two")
    try:
        with path.open("rb") as source_file:
            raw = source_file.read(max_file_bytes + 1)
    except OSError as exc:
        raise SpectrumImportError(
            f"Could not read spectrum CSV: {exc.strerror or 'I/O error'}"
        ) from exc
    if len(raw) > max_file_bytes:
        raise SpectrumImportError("Spectrum source exceeds the configured byte limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SpectrumImportError("Spectrum CSV must be UTF-8 encoded") from exc
    return parse_spectrum_csv(
        text,
        axis_column=axis_column,
        intensity_column=intensity_column,
        axis_name=axis_name,
        axis_unit=axis_unit,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        max_points=max_points,
        max_text_bytes=max_file_bytes,
    )


def parse_spectrum_csv(
    text: str,
    *,
    axis_column: str,
    intensity_column: str,
    axis_name: str,
    axis_unit: str,
    source_sha256: str,
    max_points: int = 250_000,
    max_text_bytes: int = 25_000_000,
) -> Spectrum:
    if not isinstance(text, str):
        raise SpectrumImportError("Spectrum CSV must be text")
    if (
        not axis_column.strip()
        or not intensity_column.strip()
        or axis_column == intensity_column
    ):
        raise ValueError("Axis and intensity columns must be distinct names")
    if isinstance(max_points, bool) or not isinstance(max_points, int) or max_points < 2:
        raise ValueError("max_points must be an integer of at least two")
    if (
        isinstance(max_text_bytes, bool)
        or not isinstance(max_text_bytes, int)
        or max_text_bytes <= 0
    ):
        raise ValueError("max_text_bytes must be positive")
    if len(text.encode("utf-8")) > max_text_bytes:
        raise SpectrumImportError("Spectrum source exceeds the configured byte limit")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    headers = reader.fieldnames
    if (
        not headers
        or len(headers) != len(set(headers))
        or axis_column not in headers
        or intensity_column not in headers
    ):
        raise SpectrumImportError(
            "Spectrum CSV must have unique headers including the selected axis and intensity"
        )
    points: list[SpectrumPoint] = []
    try:
        for row in reader:
            if row and all(value is None or not value.strip() for value in row.values()):
                continue
            if (
                None in row
                or row.get(axis_column) is None
                or row.get(intensity_column) is None
            ):
                raise SpectrumImportError(
                    f"Spectrum row {reader.line_num} has a different number of values than its header"
                )
            try:
                point = SpectrumPoint(
                    axis=float(row[axis_column]),
                    intensity=float(row[intensity_column]),
                )
            except ValueError as exc:
                raise SpectrumImportError(
                    f"Spectrum row {reader.line_num} contains a non-numeric value"
                ) from exc
            points.append(point)
            if len(points) > max_points:
                raise SpectrumImportError(
                    "Spectrum exceeds the configured point limit"
                )
    except csv.Error as exc:
        raise SpectrumImportError(
            f"Spectrum CSV syntax is invalid at row {reader.line_num}"
        ) from exc
    if len(points) < 2:
        raise SpectrumImportError("Spectrum CSV must contain at least two data points")

    differences = [
        current.axis - previous.axis
        for previous, current in zip(points, points[1:])
    ]
    if all(difference > 0 for difference in differences):
        direction = "ascending"
    elif all(difference < 0 for difference in differences):
        direction = "descending"
        points.reverse()
    else:
        raise SpectrumImportError(
            "Spectrum axis values must be strictly monotonic without duplicates"
        )
    return Spectrum(
        axis_name=axis_name.strip(),
        axis_unit=axis_unit.strip(),
        points=tuple(points),
        source_sha256=source_sha256.lower(),
        source_axis_direction=direction,
    )


def resample_linear(
    spectrum: Spectrum, target_axis: Sequence[float]
) -> Spectrum:
    """Linearly interpolate at requested ascending coordinates; never extrapolate."""
    if len(target_axis) < 2:
        raise ValueError("At least two target axis coordinates are required")
    if len(target_axis) > 250_000:
        raise ValueError("Target axis exceeds the configured point limit")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in target_axis
    ):
        raise ValueError("Target axis coordinates must be finite numbers")
    if any(left >= right for left, right in zip(target_axis, target_axis[1:])):
        raise ValueError("Target axis coordinates must be strictly increasing")

    source_axis = [point.axis for point in spectrum.points]
    source_intensity = [point.intensity for point in spectrum.points]
    if target_axis[0] < source_axis[0] or target_axis[-1] > source_axis[-1]:
        raise ValueError("Resampling outside the source range is not permitted")

    resampled: list[SpectrumPoint] = []
    for axis in target_axis:
        right_index = bisect.bisect_left(source_axis, axis)
        if right_index < len(source_axis) and source_axis[right_index] == axis:
            intensity = source_intensity[right_index]
        else:
            left_index = right_index - 1
            fraction = (axis - source_axis[left_index]) / (
                source_axis[right_index] - source_axis[left_index]
            )
            intensity = source_intensity[left_index] + fraction * (
                source_intensity[right_index] - source_intensity[left_index]
            )
        resampled.append(SpectrumPoint(axis=float(axis), intensity=intensity))
    return Spectrum(
        axis_name=spectrum.axis_name,
        axis_unit=spectrum.axis_unit,
        points=tuple(resampled),
        source_sha256=spectrum.source_sha256,
        source_axis_direction="derived",
    )
