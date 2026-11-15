"""Metadata envelopes for genomic objects stored outside PostgreSQL."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit
from uuid import UUID


_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")
_MAX_METADATA_BYTES = 1_000_000


class GenomicDataError(ValueError):
    """Raised when genomic dataset metadata or object provenance is invalid."""


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash a local raw-data file incrementally without loading it into memory."""
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as source:
            while chunk := source.read(chunk_size):
                digest.update(chunk)
    except OSError as exc:
        raise GenomicDataError(
            f"Could not read genomic source file: {exc.strerror or 'I/O error'}"
        ) from exc
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SampleLabOutput:
    id: UUID
    bio_sample_id: UUID
    storage_uri: str
    file_format: str
    checksum_sha256: str
    created_by: UUID
    media_type: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("id", "bio_sample_id", "created_by"):
            if not isinstance(getattr(self, field_name), UUID):
                raise GenomicDataError(f"{field_name} must be a UUID")
        try:
            if not isinstance(self.storage_uri, str):
                raise TypeError("storage_uri must be text")
            storage_uri = self.storage_uri.strip()
            parsed_uri = urlsplit(storage_uri)
            parsed_uri.port
        except (TypeError, ValueError) as exc:
            raise GenomicDataError("Genomic object URI is malformed") from exc
        if (
            parsed_uri.scheme not in {"s3", "minio"}
            or not parsed_uri.hostname
            or parsed_uri.path in {"", "/"}
            or parsed_uri.username is not None
            or parsed_uri.password is not None
            or parsed_uri.query
            or parsed_uri.fragment
        ):
            raise GenomicDataError(
                "Genomic binary files must be referenced by an S3/MinIO object URI"
            )
        object.__setattr__(self, "storage_uri", storage_uri)
        if not isinstance(self.file_format, str) or not self.file_format.strip():
            raise GenomicDataError("Genomic file format must be documented")
        if not isinstance(self.checksum_sha256, str) or not _SHA256.fullmatch(
            self.checksum_sha256
        ):
            raise GenomicDataError("Genomic object requires a SHA-256 checksum")
        if self.media_type is not None and (
            not isinstance(self.media_type, str) or not self.media_type.strip()
        ):
            raise GenomicDataError("media_type must be non-empty text when supplied")
        if self.description is not None and not isinstance(self.description, str):
            raise GenomicDataError("description must be text when supplied")
        object.__setattr__(self, "checksum_sha256", self.checksum_sha256.lower())
        object.__setattr__(self, "file_format", self.file_format.strip())

    def writeback_payload(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "bio_sample_id": str(self.bio_sample_id),
            "output_type": "genomic",
            "file_format": self.file_format.strip(),
            "storage_uri": self.storage_uri,
            "checksum_sha256": self.checksum_sha256,
            "media_type": self.media_type,
            "description": self.description,
            "created_by": str(self.created_by),
        }


@dataclass(frozen=True, slots=True)
class GenomicDataset:
    id: UUID
    bio_sample_id: UUID
    output: SampleLabOutput
    sequencing_method: str
    created_by: UUID
    reference_assembly: str | None = None
    dataset_metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        for field_name in ("id", "bio_sample_id", "created_by"):
            if not isinstance(getattr(self, field_name), UUID):
                raise GenomicDataError(f"{field_name} must be a UUID")
        if not isinstance(self.output, SampleLabOutput):
            raise GenomicDataError("A genomic dataset requires a sample-lab output")
        if self.output.bio_sample_id != self.bio_sample_id:
            raise GenomicDataError(
                "Genomic output must belong to the same biological sample"
            )
        if not isinstance(self.sequencing_method, str) or not self.sequencing_method.strip():
            raise GenomicDataError("Sequencing method is required")
        if self.reference_assembly is not None and (
            not isinstance(self.reference_assembly, str)
            or not self.reference_assembly.strip()
        ):
            raise GenomicDataError(
                "reference_assembly must be non-empty text when supplied"
            )
        if self.reference_assembly is not None:
            object.__setattr__(self, "reference_assembly", self.reference_assembly.strip())
        metadata = {} if self.dataset_metadata is None else self.dataset_metadata
        if not isinstance(metadata, Mapping):
            raise GenomicDataError("dataset_metadata must be a JSON object")
        try:
            serialized = json.dumps(
                dict(metadata),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise GenomicDataError(
                "dataset_metadata must contain finite JSON-compatible values"
            ) from exc
        if len(serialized.encode("utf-8")) > _MAX_METADATA_BYTES:
            raise GenomicDataError("dataset_metadata exceeds the configured size limit")
        object.__setattr__(self, "sequencing_method", self.sequencing_method.strip())
        object.__setattr__(
            self,
            "dataset_metadata",
            MappingProxyType(json.loads(serialized)),
        )

    def writeback_payload(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "bio_sample_id": str(self.bio_sample_id),
            "output_id": str(self.output.id),
            "reference_assembly": self.reference_assembly,
            "sequencing_method": self.sequencing_method.strip(),
            "dataset_metadata": dict(self.dataset_metadata or {}),
            "created_by": str(self.created_by),
        }
