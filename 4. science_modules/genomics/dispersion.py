"""Reproducible, database-aligned dispersion analysis run metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit
from uuid import UUID


_ANALYSIS_TYPES = {"genome", "flora", "fauna"}
_STATUSES = {"queued", "running", "complete", "failed"}
_ASSET_ROLES = {"interactive_visualization", "phylogenetic_tree", "other"}
_MAX_PARAMETERS_BYTES = 1_000_000


class DispersionAnalysisError(ValueError):
    """Raised when an analysis record or state transition is invalid."""


def _aware_timestamp(value: datetime | None, name: str) -> None:
    if value is not None and (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise DispersionAnalysisError(f"{name} must be a timezone-aware datetime")


@dataclass(frozen=True, slots=True)
class DispersionAnalysis:
    id: UUID
    analysis_type: str
    title: str
    notebook_uri: str
    notebook_revision: str
    environment_reference: str
    created_by: UUID
    sample_ids: tuple[UUID, ...]
    regional_chronicle_ids: tuple[UUID, ...] = ()
    parameters: Mapping[str, object] | None = None
    status: str = "queued"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    media_assets: tuple[tuple[UUID, str], ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("id", "created_by"):
            if not isinstance(getattr(self, field_name), UUID):
                raise DispersionAnalysisError(f"{field_name} must be a UUID")
        if not isinstance(self.analysis_type, str) or self.analysis_type not in _ANALYSIS_TYPES:
            raise DispersionAnalysisError("analysis_type must be genome, flora, or fauna")
        for field_name in (
            "title",
            "notebook_revision",
            "environment_reference",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DispersionAnalysisError(f"{field_name} is required")
            object.__setattr__(self, field_name, value.strip())
        try:
            if not isinstance(self.notebook_uri, str):
                raise TypeError("notebook_uri must be text")
            notebook_uri = self.notebook_uri.strip()
            parsed_uri = urlsplit(notebook_uri)
            parsed_uri.port
        except (TypeError, ValueError) as exc:
            raise DispersionAnalysisError("notebook_uri is malformed") from exc
        if (
            parsed_uri.scheme not in {"http", "https", "s3", "minio"}
            or not parsed_uri.hostname
            or parsed_uri.username is not None
            or parsed_uri.password is not None
            or parsed_uri.query
            or parsed_uri.fragment
        ):
            raise DispersionAnalysisError(
                "notebook_uri must be an absolute HTTP(S), S3, or MinIO URI"
            )
        object.__setattr__(self, "notebook_uri", notebook_uri)
        if not isinstance(self.status, str) or self.status not in _STATUSES:
            raise DispersionAnalysisError("status is not supported")

        sample_ids = tuple(self.sample_ids)
        region_ids = tuple(self.regional_chronicle_ids)
        if not sample_ids or any(not isinstance(value, UUID) for value in sample_ids):
            raise DispersionAnalysisError("At least one valid sample UUID is required")
        if len(set(sample_ids)) != len(sample_ids):
            raise DispersionAnalysisError("sample_ids must not contain duplicates")
        if any(not isinstance(value, UUID) for value in region_ids):
            raise DispersionAnalysisError("regional_chronicle_ids must contain UUIDs")
        if len(set(region_ids)) != len(region_ids):
            raise DispersionAnalysisError(
                "regional_chronicle_ids must not contain duplicates"
            )
        object.__setattr__(self, "sample_ids", sample_ids)
        object.__setattr__(self, "regional_chronicle_ids", region_ids)

        parameters = {} if self.parameters is None else self.parameters
        if not isinstance(parameters, Mapping):
            raise DispersionAnalysisError("parameters must be a JSON object")
        try:
            serialized = json.dumps(
                dict(parameters),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise DispersionAnalysisError(
                "parameters must contain finite JSON-compatible values"
            ) from exc
        if len(serialized.encode("utf-8")) > _MAX_PARAMETERS_BYTES:
            raise DispersionAnalysisError("parameters exceed the configured size limit")
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(json.loads(serialized)),
        )

        _aware_timestamp(self.started_at, "started_at")
        _aware_timestamp(self.completed_at, "completed_at")
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise DispersionAnalysisError("completed_at cannot precede started_at")
        if self.status in {"running", "complete"} and self.started_at is None:
            raise DispersionAnalysisError(f"{self.status} analysis requires started_at")
        if self.status == "complete" and self.completed_at is None:
            raise DispersionAnalysisError("complete analysis requires completed_at")
        if self.status == "queued" and (
            self.started_at is not None or self.completed_at is not None
        ):
            raise DispersionAnalysisError("queued analysis cannot have execution timestamps")
        if self.status == "running" and self.completed_at is not None:
            raise DispersionAnalysisError("running analysis cannot have completed_at")

        assets = tuple(self.media_assets)
        seen_asset_ids: set[UUID] = set()
        for asset_id, role in assets:
            if not isinstance(asset_id, UUID):
                raise DispersionAnalysisError("media asset identifiers must be UUIDs")
            if asset_id in seen_asset_ids:
                raise DispersionAnalysisError("media asset identifiers must be unique")
            if not isinstance(role, str) or role not in _ASSET_ROLES:
                raise DispersionAnalysisError("media asset role is not supported")
            seen_asset_ids.add(asset_id)
        object.__setattr__(self, "media_assets", assets)

    def start(self, at: datetime) -> DispersionAnalysis:
        _aware_timestamp(at, "started_at")
        if self.status != "queued":
            raise DispersionAnalysisError("Only queued analyses can be started")
        return replace(self, status="running", started_at=at)

    def finish(
        self,
        at: datetime,
        *,
        failed: bool = False,
        media_assets: tuple[tuple[UUID, str], ...] | None = None,
    ) -> DispersionAnalysis:
        _aware_timestamp(at, "completed_at")
        if not isinstance(failed, bool):
            raise DispersionAnalysisError("failed must be a boolean")
        if self.status != "running":
            raise DispersionAnalysisError("Only running analyses can be finished")
        return replace(
            self,
            status="failed" if failed else "complete",
            completed_at=at,
            media_assets=self.media_assets if media_assets is None else media_assets,
        )

    def writeback_payload(self) -> dict[str, object]:
        """Return table payloads for one transaction with the three link tables."""
        return {
            "analysis": {
                "id": str(self.id),
                "analysis_type": self.analysis_type,
                "title": self.title,
                "notebook_uri": self.notebook_uri,
                "notebook_revision": self.notebook_revision,
                "environment_reference": self.environment_reference,
                "parameters": dict(self.parameters or {}),
                "status": self.status,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": (
                    self.completed_at.isoformat() if self.completed_at else None
                ),
                "created_by": str(self.created_by),
            },
            "samples": [
                {"dispersion_analysis_id": str(self.id), "bio_sample_id": str(sample_id)}
                for sample_id in self.sample_ids
            ],
            "regions": [
                {
                    "dispersion_analysis_id": str(self.id),
                    "regional_chronicle_id": str(region_id),
                }
                for region_id in self.regional_chronicle_ids
            ],
            "media_assets": [
                {
                    "dispersion_analysis_id": str(self.id),
                    "media_asset_id": str(asset_id),
                    "asset_role": role,
                }
                for asset_id, role in self.media_assets
            ],
        }
