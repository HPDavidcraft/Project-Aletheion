"""Validated haplogroup assignments and grouped dispersion summaries."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Iterable, Mapping
from uuid import UUID
from urllib.parse import urlsplit

from .ethics import GenomicPublicationContext, require_public_genomic_release


class HaplogroupDataError(ValueError):
    """Raised for invalid assignments or inconsistent dispersion inputs."""


def _confidence(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HaplogroupDataError(f"{name} must be a number in [0, 1]")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0 <= normalized <= 1:
        raise HaplogroupDataError(f"{name} must be a finite number in [0, 1]")
    return normalized


@dataclass(frozen=True, slots=True)
class HaplogroupAssignment:
    id: UUID
    bio_sample_id: UUID
    marker_type: str
    haplogroup_label: str
    confidence_lower: float
    confidence_upper: float
    authority_uri: str | None = None
    tree_media_asset_id: UUID | None = None
    analysis_output_id: UUID | None = None
    assigned_by: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("id", "bio_sample_id"):
            if not isinstance(getattr(self, field_name), UUID):
                raise HaplogroupDataError(f"{field_name} must be a UUID")
        for field_name in ("tree_media_asset_id", "analysis_output_id"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, UUID):
                raise HaplogroupDataError(f"{field_name} must be a UUID when supplied")
        if not isinstance(self.marker_type, str) or self.marker_type not in {
            "mitochondrial",
            "y_chromosomal",
            "other",
        }:
            raise HaplogroupDataError("marker_type must be mitochondrial, y_chromosomal, or other")
        if not isinstance(self.haplogroup_label, str) or not self.haplogroup_label.strip():
            raise HaplogroupDataError("haplogroup_label is required")
        lower = _confidence(self.confidence_lower, "confidence_lower")
        upper = _confidence(self.confidence_upper, "confidence_upper")
        if lower > upper:
            raise HaplogroupDataError("confidence_lower cannot exceed confidence_upper")
        if self.authority_uri is not None:
            try:
                parsed = urlsplit(self.authority_uri)
                parsed.port
            except (TypeError, ValueError) as exc:
                raise HaplogroupDataError("authority_uri is malformed") from exc
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise HaplogroupDataError("authority_uri must be an absolute HTTP(S) URI")
        if self.assigned_by is not None and (
            not isinstance(self.assigned_by, str) or not self.assigned_by.strip()
        ):
            raise HaplogroupDataError("assigned_by must be non-empty text when supplied")
        object.__setattr__(self, "confidence_lower", lower)
        object.__setattr__(self, "confidence_upper", upper)

    def writeback_payload(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "bio_sample_id": str(self.bio_sample_id),
            "marker_type": self.marker_type.strip(),
            "haplogroup_label": self.haplogroup_label.strip(),
            "authority_uri": self.authority_uri,
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "tree_media_asset_id": (
                str(self.tree_media_asset_id) if self.tree_media_asset_id else None
            ),
            "analysis_output_id": (
                str(self.analysis_output_id) if self.analysis_output_id else None
            ),
            "assigned_by": self.assigned_by.strip() if self.assigned_by else None,
        }


@dataclass(frozen=True, slots=True)
class HaplogroupObservation:
    """An assignment joined to pre-resolved region and time-slice identifiers."""

    bio_sample_id: UUID
    region_id: UUID
    time_slice: str
    marker_type: str
    haplogroup_label: str
    confidence_lower: float
    confidence_upper: float

    def __post_init__(self) -> None:
        for field_name in ("bio_sample_id", "region_id"):
            if not isinstance(getattr(self, field_name), UUID):
                raise HaplogroupDataError(f"{field_name} must be a UUID")
        if not isinstance(self.time_slice, str) or not self.time_slice.strip():
            raise HaplogroupDataError("time_slice is required")
        if not isinstance(self.marker_type, str) or self.marker_type not in {
            "mitochondrial",
            "y_chromosomal",
            "other",
        }:
            raise HaplogroupDataError("marker_type must be mitochondrial, y_chromosomal, or other")
        if not isinstance(self.haplogroup_label, str) or not self.haplogroup_label.strip():
            raise HaplogroupDataError("haplogroup_label is required")
        lower = _confidence(self.confidence_lower, "confidence_lower")
        upper = _confidence(self.confidence_upper, "confidence_upper")
        if lower > upper:
            raise HaplogroupDataError("confidence_lower cannot exceed confidence_upper")
        object.__setattr__(self, "time_slice", self.time_slice.strip())
        object.__setattr__(self, "marker_type", self.marker_type.strip())
        object.__setattr__(self, "haplogroup_label", self.haplogroup_label.strip())
        object.__setattr__(self, "confidence_lower", lower)
        object.__setattr__(self, "confidence_upper", upper)


@dataclass(frozen=True, slots=True)
class HaplogroupFrequency:
    region_id: UUID
    time_slice: str
    marker_type: str
    haplogroup_label: str
    sample_count: int
    sample_total: int
    sample_frequency: Decimal
    mean_assignment_confidence_lower: Decimal
    mean_assignment_confidence_upper: Decimal

    def to_dict(self) -> dict[str, object]:
        return {
            "region_id": str(self.region_id),
            "time_slice": self.time_slice,
            "marker_type": self.marker_type,
            "haplogroup_label": self.haplogroup_label,
            "sample_count": self.sample_count,
            "sample_total": self.sample_total,
            "sample_frequency": str(self.sample_frequency),
            "mean_assignment_confidence_lower": str(
                self.mean_assignment_confidence_lower
            ),
            "mean_assignment_confidence_upper": str(
                self.mean_assignment_confidence_upper
            ),
        }


@dataclass(frozen=True, slots=True)
class HaplogroupFrequencyReport:
    rows: tuple[HaplogroupFrequency, ...]
    sample_ids_by_partition: Mapping[
        tuple[UUID, str, str], frozenset[UUID]
    ] = field(default_factory=dict, repr=False, compare=False)

    def public_rows(
        self,
        *,
        minimum_cohort_size: int,
        publication_contexts: Iterable[GenomicPublicationContext],
    ) -> tuple[HaplogroupFrequency, ...]:
        """Return cohorts only after each contributing sample passes the release gate."""
        if (
            isinstance(minimum_cohort_size, bool)
            or not isinstance(minimum_cohort_size, int)
            or minimum_cohort_size < 1
        ):
            raise ValueError("minimum_cohort_size must be an explicitly configured positive integer")
        contexts: dict[UUID, GenomicPublicationContext] = {}
        for context in publication_contexts:
            if not isinstance(context, GenomicPublicationContext):
                raise TypeError("publication_contexts must contain trusted publication contexts")
            if context.sample_id in contexts:
                raise ValueError("publication_contexts must not repeat sample identifiers")
            contexts[context.sample_id] = context
        required_sample_ids = set().union(*self.sample_ids_by_partition.values())
        if not required_sample_ids.issubset(contexts):
            raise ValueError("A trusted publication context is required for every contributing sample")
        for sample_id in required_sample_ids:
            require_public_genomic_release(contexts[sample_id])

        partitions: dict[tuple[UUID, str, str], list[HaplogroupFrequency]] = defaultdict(list)
        for row in self.rows:
            partitions[(row.region_id, row.time_slice, row.marker_type)].append(row)
        safe_partitions = {
            key
            for key, rows in partitions.items()
            if all(row.sample_count >= minimum_cohort_size for row in rows)
        }
        return tuple(
            row
            for row in self.rows
            if (row.region_id, row.time_slice, row.marker_type) in safe_partitions
        )


def aggregate_haplogroup_frequencies(
    observations: Iterable[HaplogroupObservation],
) -> HaplogroupFrequencyReport:
    """Count unique samples by haplogroup; confidence ranges remain assignment-level.

    Region and time-slice resolution is deliberately supplied by the caller so this
    module does not invent chronology or spatial mappings.
    """
    items = tuple(observations)
    if not items:
        return HaplogroupFrequencyReport(())
    assignment_keys: set[tuple[UUID, str, str, UUID]] = set()
    partitions: dict[tuple[UUID, str, str], set[UUID]] = defaultdict(set)
    groups: dict[
        tuple[UUID, str, str, str],
        list[HaplogroupObservation],
    ] = defaultdict(list)
    for item in items:
        if not isinstance(item, HaplogroupObservation):
            raise HaplogroupDataError("observations must contain HaplogroupObservation values")
        partition_key = (item.region_id, item.time_slice, item.marker_type)
        assignment_key = (*partition_key, item.bio_sample_id)
        if assignment_key in assignment_keys:
            raise HaplogroupDataError(
                "Each sample may have only one assignment per region, time slice, and marker"
            )
        assignment_keys.add(assignment_key)
        partitions[partition_key].add(item.bio_sample_id)
        groups[(*partition_key, item.haplogroup_label)].append(item)

    rows: list[HaplogroupFrequency] = []
    for key in sorted(groups, key=lambda value: tuple(map(str, value))):
        region_id, time_slice, marker_type, label = key
        assignments = groups[key]
        total = len(partitions[(region_id, time_slice, marker_type)])
        count = len(assignments)
        rows.append(
            HaplogroupFrequency(
                region_id=region_id,
                time_slice=time_slice,
                marker_type=marker_type,
                haplogroup_label=label,
                sample_count=count,
                sample_total=total,
                sample_frequency=Decimal(count) / Decimal(total),
                mean_assignment_confidence_lower=(
                    sum(Decimal(str(item.confidence_lower)) for item in assignments)
                    / Decimal(count)
                ),
                mean_assignment_confidence_upper=(
                    sum(Decimal(str(item.confidence_upper)) for item in assignments)
                    / Decimal(count)
                ),
            )
        )
    sample_ids_by_partition = MappingProxyType(
        {
            key: frozenset(sample_ids)
            for key, sample_ids in partitions.items()
        }
    )
    return HaplogroupFrequencyReport(tuple(rows), sample_ids_by_partition)


def frequency_payload(
    report: HaplogroupFrequencyReport,
    *,
    public: bool = False,
    minimum_cohort_size: int | None = None,
    publication_contexts: Iterable[GenomicPublicationContext] | None = None,
) -> tuple[dict[str, object], ...]:
    """Serialize a report, requiring a governance-selected threshold for public use."""
    if public:
        if minimum_cohort_size is None:
            raise ValueError("Public frequency release requires an explicit cohort threshold")
        if publication_contexts is None:
            raise ValueError("Public frequency release requires trusted per-sample contexts")
        rows = report.public_rows(
            minimum_cohort_size=minimum_cohort_size,
            publication_contexts=publication_contexts,
        )
    else:
        rows = report.rows
    return tuple(row.to_dict() for row in rows)


def frequency_chart_spec(
    report: HaplogroupFrequencyReport,
    *,
    public: bool = False,
    minimum_cohort_size: int | None = None,
    publication_contexts: Iterable[GenomicPublicationContext] | None = None,
) -> dict[str, object]:
    """Build a dependency-free Vega-Lite bar-chart specification."""
    data = [
        dict(row)
        for row in frequency_payload(
            report,
            public=public,
            minimum_cohort_size=minimum_cohort_size,
            publication_contexts=publication_contexts,
        )
    ]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": data},
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "x": {
                "field": "haplogroup_label",
                "type": "nominal",
                "title": "Haplogroup",
                "sort": "-y",
            },
            "y": {
                "field": "sample_frequency",
                "type": "quantitative",
                "title": "Share of assigned samples",
            },
            "color": {
                "field": "region_id",
                "type": "nominal",
                "title": "Region",
            },
            "column": {
                "field": "time_slice",
                "type": "nominal",
                "title": "Time slice",
            },
            "tooltip": [
                {"field": "sample_count", "type": "quantitative"},
                {"field": "sample_total", "type": "quantitative"},
                {"field": "mean_assignment_confidence_lower", "type": "quantitative"},
                {"field": "mean_assignment_confidence_upper", "type": "quantitative"},
            ],
        },
    }
