"""Source-driven commodity-to-silver valuation and normalized index ranges."""

from __future__ import annotations

import csv
import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit
from uuid import UUID
from xml.sax.saxutils import escape


_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")
_MAX_CSV_BYTES = 25_000_000
_MAX_CSV_ROWS = 200_000
_REQUIRED_COLUMNS = {
    "observation_id",
    "commodity_uri",
    "region_id",
    "period_label",
    "period_order",
    "commodity_unit",
    "quantity_lower",
    "quantity_upper",
    "silver_grams_per_unit_lower",
    "silver_grams_per_unit_upper",
    "quantity_reference_id",
    "exchange_rate_reference_id",
}


class EconomicIndexError(ValueError):
    """Raised when source observations or index parameters are invalid."""


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise EconomicIndexError(f"{field} must be a finite decimal value")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise EconomicIndexError(f"{field} must be a finite decimal value") from exc
    if not result.is_finite():
        raise EconomicIndexError(f"{field} must be a finite decimal value")
    return result


def _nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EconomicIndexError(f"{field} is required")
    return value.strip()


def _concept_uri(value: object) -> str:
    uri = _nonempty(value, "commodity_uri")
    try:
        parts = urlsplit(uri)
        parts.port
    except ValueError as exc:
        raise EconomicIndexError("commodity_uri is malformed") from exc
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise EconomicIndexError("commodity_uri must be an absolute HTTP(S) vocabulary URI")
    return uri


@dataclass(frozen=True, slots=True)
class CommodityObservation:
    observation_id: UUID
    commodity_uri: str
    region_id: UUID
    period_label: str
    period_order: int
    commodity_unit: str
    quantity_lower: Decimal
    quantity_upper: Decimal
    silver_grams_per_unit_lower: Decimal
    silver_grams_per_unit_upper: Decimal
    quantity_reference_id: UUID
    exchange_rate_reference_id: UUID

    def __post_init__(self) -> None:
        for field in (
            "observation_id",
            "region_id",
            "quantity_reference_id",
            "exchange_rate_reference_id",
        ):
            if not isinstance(getattr(self, field), UUID):
                raise EconomicIndexError(f"{field} must be a UUID")
        if isinstance(self.period_order, bool) or not isinstance(self.period_order, int):
            raise EconomicIndexError("period_order must be an integer ordering key")
        object.__setattr__(self, "commodity_uri", _concept_uri(self.commodity_uri))
        object.__setattr__(self, "period_label", _nonempty(self.period_label, "period_label"))
        object.__setattr__(self, "commodity_unit", _nonempty(self.commodity_unit, "commodity_unit"))

        quantity_lower = _decimal(self.quantity_lower, "quantity_lower")
        quantity_upper = _decimal(self.quantity_upper, "quantity_upper")
        rate_lower = _decimal(
            self.silver_grams_per_unit_lower, "silver_grams_per_unit_lower"
        )
        rate_upper = _decimal(
            self.silver_grams_per_unit_upper, "silver_grams_per_unit_upper"
        )
        if quantity_lower < 0 or quantity_upper < quantity_lower:
            raise EconomicIndexError("Quantity bounds must be ordered and non-negative")
        if rate_lower <= 0 or rate_upper < rate_lower:
            raise EconomicIndexError("Silver conversion bounds must be ordered and positive")
        object.__setattr__(self, "quantity_lower", quantity_lower)
        object.__setattr__(self, "quantity_upper", quantity_upper)
        object.__setattr__(self, "silver_grams_per_unit_lower", rate_lower)
        object.__setattr__(self, "silver_grams_per_unit_upper", rate_upper)


@dataclass(frozen=True, slots=True)
class EconomicIndexRow:
    observation_id: UUID
    commodity_uri: str
    region_id: UUID
    period_label: str
    period_order: int
    commodity_unit: str
    silver_grams_lower: Decimal
    silver_grams_upper: Decimal
    index_lower: Decimal
    index_upper: Decimal
    quantity_reference_id: UUID
    exchange_rate_reference_id: UUID

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": str(self.observation_id),
            "commodity_uri": self.commodity_uri,
            "region_id": str(self.region_id),
            "period_label": self.period_label,
            "period_order": self.period_order,
            "commodity_unit": self.commodity_unit,
            "silver_grams_lower": str(self.silver_grams_lower),
            "silver_grams_upper": str(self.silver_grams_upper),
            "index_lower": str(self.index_lower),
            "index_upper": str(self.index_upper),
            "quantity_reference_id": str(self.quantity_reference_id),
            "exchange_rate_reference_id": str(self.exchange_rate_reference_id),
        }


@dataclass(frozen=True, slots=True)
class EconomicIndexReport:
    baseline_period: str
    rows: tuple[EconomicIndexRow, ...]

    def writeback_payload(
        self,
        *,
        input_sha256: str,
        parameter_set_id: UUID,
        notebook_revision: str,
        environment_reference: str,
        executed_at: datetime,
    ) -> dict[str, object]:
        if not isinstance(input_sha256, str) or not _SHA256.fullmatch(input_sha256):
            raise EconomicIndexError("input_sha256 must be a SHA-256 digest")
        if not isinstance(parameter_set_id, UUID):
            raise EconomicIndexError("parameter_set_id must be a UUID")
        if (
            not isinstance(executed_at, datetime)
            or executed_at.tzinfo is None
            or executed_at.utcoffset() is None
        ):
            raise EconomicIndexError("executed_at must be timezone-aware")
        return {
            "analysis_type": "commodity_silver_equivalence_index",
            "baseline_period": self.baseline_period,
            "input_sha256": input_sha256.lower(),
            "parameter_set_id": str(parameter_set_id),
            "notebook_revision": _nonempty(notebook_revision, "notebook_revision"),
            "environment_reference": _nonempty(
                environment_reference, "environment_reference"
            ),
            "executed_at": executed_at.isoformat(),
            "observations": [row.to_dict() for row in self.rows],
        }


def calculate_silver_equivalence_index(
    observations: Iterable[CommodityObservation],
    *,
    baseline_period: str,
) -> EconomicIndexReport:
    """Calculate silver-gram ranges and per-series index values (baseline = 100).

    Exchange rates and quantities are inputs, not inferred constants. Interval
    arithmetic uses positive bounds and reports conservative quotient ranges.
    """
    period = _nonempty(baseline_period, "baseline_period")
    items = tuple(observations)
    if not items:
        raise EconomicIndexError("At least one sourced commodity observation is required")
    if any(not isinstance(item, CommodityObservation) for item in items):
        raise EconomicIndexError(
            "observations must contain CommodityObservation values"
        )

    observation_ids: set[UUID] = set()
    series_periods: set[tuple[UUID, str, str, str]] = set()
    series_orders: set[tuple[UUID, str, str, int]] = set()
    series: dict[tuple[UUID, str, str], list[CommodityObservation]] = {}
    for item in items:
        if item.observation_id in observation_ids:
            raise EconomicIndexError("observation_id values must be unique")
        observation_ids.add(item.observation_id)
        series_key = (item.region_id, item.commodity_uri, item.commodity_unit)
        period_key = (*series_key, item.period_label)
        order_key = (*series_key, item.period_order)
        if period_key in series_periods or order_key in series_orders:
            raise EconomicIndexError(
                "Each region/commodity/unit series must have unique periods and ordering keys"
            )
        series_periods.add(period_key)
        series_orders.add(order_key)
        series.setdefault(series_key, []).append(item)

    rows: list[EconomicIndexRow] = []
    for series_key, series_items in series.items():
        baselines = [item for item in series_items if item.period_label == period]
        if len(baselines) != 1:
            raise EconomicIndexError(
                "Every region/commodity/unit series must include the selected baseline period"
            )
        baseline = baselines[0]
        baseline_lower = (
            baseline.quantity_lower * baseline.silver_grams_per_unit_lower
        )
        baseline_upper = (
            baseline.quantity_upper * baseline.silver_grams_per_unit_upper
        )
        if baseline_lower <= 0:
            raise EconomicIndexError(
                "Baseline silver-equivalent lower bound must be positive"
            )
        for item in series_items:
            silver_lower = item.quantity_lower * item.silver_grams_per_unit_lower
            silver_upper = item.quantity_upper * item.silver_grams_per_unit_upper
            if item.observation_id == baseline.observation_id:
                index_lower = index_upper = Decimal(100)
            else:
                index_lower = (silver_lower / baseline_upper) * Decimal(100)
                index_upper = (silver_upper / baseline_lower) * Decimal(100)
            rows.append(
                EconomicIndexRow(
                    observation_id=item.observation_id,
                    commodity_uri=item.commodity_uri,
                    region_id=item.region_id,
                    period_label=item.period_label,
                    period_order=item.period_order,
                    commodity_unit=item.commodity_unit,
                    silver_grams_lower=silver_lower,
                    silver_grams_upper=silver_upper,
                    index_lower=index_lower,
                    index_upper=index_upper,
                    quantity_reference_id=item.quantity_reference_id,
                    exchange_rate_reference_id=item.exchange_rate_reference_id,
                )
            )
    rows.sort(
        key=lambda row: (
            str(row.region_id),
            row.commodity_uri,
            row.commodity_unit,
            row.period_order,
        )
    )
    return EconomicIndexReport(period, tuple(rows))


def read_observations_csv(
    path: str | Path,
    *,
    max_file_bytes: int = _MAX_CSV_BYTES,
    max_rows: int = _MAX_CSV_ROWS,
) -> tuple[CommodityObservation, ...]:
    """Read the explicit CSV input contract without evaluating cell contents."""
    source_path = Path(path)
    if not source_path.is_file():
        raise EconomicIndexError("Input path must name an existing CSV file")
    if source_path.suffix.casefold() != ".csv":
        raise EconomicIndexError("Only CSV observation files are accepted")
    if (
        isinstance(max_file_bytes, bool)
        or not isinstance(max_file_bytes, int)
        or max_file_bytes <= 0
        or isinstance(max_rows, bool)
        or not isinstance(max_rows, int)
        or max_rows <= 0
    ):
        raise ValueError("CSV limits must be positive integers")
    if source_path.stat().st_size > max_file_bytes:
        raise EconomicIndexError("Observation CSV exceeds the configured byte limit")
    try:
        with source_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            if (
                not reader.fieldnames
                or len(reader.fieldnames) != len(set(reader.fieldnames))
                or not _REQUIRED_COLUMNS.issubset(reader.fieldnames)
            ):
                raise EconomicIndexError(
                    "Observation CSV does not match the documented input columns"
                )
            items: list[CommodityObservation] = []
            for row_number, row in enumerate(reader, start=2):
                if row_number > max_rows + 1:
                    raise EconomicIndexError("Observation CSV exceeds the configured row limit")
                if None in row or any(value is None for value in row.values()):
                    raise EconomicIndexError(
                        f"Observation CSV row {row_number} has a different number of values than its header"
                    )
                try:
                    items.append(
                        CommodityObservation(
                            observation_id=UUID(row["observation_id"]),
                            commodity_uri=row["commodity_uri"],
                            region_id=UUID(row["region_id"]),
                            period_label=row["period_label"],
                            period_order=int(row["period_order"]),
                            commodity_unit=row["commodity_unit"],
                            quantity_lower=Decimal(row["quantity_lower"]),
                            quantity_upper=Decimal(row["quantity_upper"]),
                            silver_grams_per_unit_lower=Decimal(
                                row["silver_grams_per_unit_lower"]
                            ),
                            silver_grams_per_unit_upper=Decimal(
                                row["silver_grams_per_unit_upper"]
                            ),
                            quantity_reference_id=UUID(row["quantity_reference_id"]),
                            exchange_rate_reference_id=UUID(
                                row["exchange_rate_reference_id"]
                            ),
                        )
                    )
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise EconomicIndexError(
                        f"Invalid observation value at CSV row {row_number}"
                    ) from exc
    except (OSError, csv.Error) as exc:
        raise EconomicIndexError(
            f"Could not read observation CSV: {exc}"
        ) from exc
    if not items:
        raise EconomicIndexError("Observation CSV contains no rows")
    return tuple(items)


def sha256_file(path: str | Path) -> str:
    """Compute an input-file digest in bounded-memory chunks."""
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EconomicIndexError(
            f"Could not hash observation file: {exc.strerror or 'I/O error'}"
        ) from exc
    return digest.hexdigest()


def write_index_svg(
    report: EconomicIndexReport,
    output_path: str | Path,
    *,
    commodity_uri: str,
    region_id: UUID,
    commodity_unit: str,
) -> Path:
    """Render one normalized commodity series as an SVG with input uncertainty."""
    uri = _concept_uri(commodity_uri)
    unit = _nonempty(commodity_unit, "commodity_unit")
    if not isinstance(region_id, UUID):
        raise EconomicIndexError("region_id must be a UUID")
    path = Path(output_path)
    if (
        path.suffix.casefold() != ".svg"
        or not path.parent.is_dir()
        or path.exists()
    ):
        raise EconomicIndexError("Output must be a new SVG in an existing directory")
    rows = sorted(
        (
            row
            for row in report.rows
            if row.commodity_uri == uri
            and row.region_id == region_id
            and row.commodity_unit == unit
        ),
        key=lambda row: row.period_order,
    )
    if not rows:
        raise EconomicIndexError("No index observations match the requested series")
    lower = [float(row.index_lower) for row in rows]
    upper = [float(row.index_upper) for row in rows]
    if any(not math.isfinite(value) for value in (*lower, *upper)):
        raise EconomicIndexError("Index ranges exceed the chart's numeric limits")
    y_min, y_max = min(min(lower), 100.0), max(max(upper), 100.0)
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0
    else:
        padding = (y_max - y_min) * 0.08
        y_min -= padding
        y_max += padding

    width, height = 1000, 620
    left, right, top, bottom = 90, 960, 70, 530
    x_positions = [
        left + (right - left) * index / max(len(rows) - 1, 1)
        for index in range(len(rows))
    ]

    def y_position(value: float) -> float:
        return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

    components = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Normalized commodity silver-equivalence index</title>",
        "<desc>Index ranges are normalized against the supplied baseline observation; they are not an inflation or purchasing-power adjustment.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-family="sans-serif" font-size="18">'
        f'Index: {escape(uri)} ({escape(unit)})</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#222"/>',
    ]
    baseline_y = y_position(100.0)
    components.append(
        f'<line x1="{left}" y1="{baseline_y:.2f}" x2="{right}" y2="{baseline_y:.2f}" '
        'stroke="#777" stroke-dasharray="6 4"><title>Baseline index 100</title></line>'
    )
    midpoints: list[str] = []
    for row, x, low_value, high_value in zip(rows, x_positions, lower, upper):
        low_y, high_y = y_position(low_value), y_position(high_value)
        midpoints.append(f"{x:.2f},{y_position((low_value + high_value) / 2):.2f}")
        components.append(
            f'<line x1="{x:.2f}" y1="{low_y:.2f}" x2="{x:.2f}" y2="{high_y:.2f}" '
            'stroke="#1f77b4" stroke-width="2"><title>'
            f'{escape(row.period_label)}: {low_value:g} to {high_value:g}</title></line>'
        )
        components.append(
            f'<circle cx="{x:.2f}" cy="{y_position((low_value + high_value) / 2):.2f}" '
            'r="5" fill="#1f77b4"/>'
        )
        components.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11">{escape(row.period_label)}</text>'
        )
    if len(midpoints) > 1:
        components.append(
            f'<polyline points="{" ".join(midpoints)}" fill="none" stroke="#1f77b4"/>'
        )
    components.extend(
        [
            f'<text x="{(left + right) / 2}" y="{height - 24}" text-anchor="middle" font-family="sans-serif" font-size="13">Period (input order)</text>',
            f'<text x="22" y="{(top + bottom) / 2}" transform="rotate(-90 22 {(top + bottom) / 2})" text-anchor="middle" font-family="sans-serif" font-size="13">Normalized index (baseline = 100)</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(components) + "\n", encoding="utf-8")
    return path
