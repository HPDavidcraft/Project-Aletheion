"""Technique-aware archaeometry result and event validation."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlsplit
from uuid import UUID


class ArchaeometryValidationError(ValueError):
    """Raised when an analysis result or its provenance is invalid."""


class AnalysisTechnique(str, Enum):
    XRF = "XRF"
    XRD = "XRD"
    SEM_EDS = "SEM-EDS"
    INAA = "INAA"
    FTIR = "FTIR"
    PXRF = "pXRF"


_ELEMENTS = frozenset(
    """
    H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni
    Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I
    Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt
    Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr
    Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og
    """.split()
)
_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")
_MAX_RESULT_BYTES = 2_000_000
_ELEMENTAL_TECHNIQUES = frozenset(
    {
        AnalysisTechnique.XRF,
        AnalysisTechnique.PXRF,
        AnalysisTechnique.SEM_EDS,
        AnalysisTechnique.INAA,
    }
)


def validate_technique_results(
    technique: AnalysisTechnique | str,
    results: Mapping[str, object],
) -> dict[str, object]:
    """Validate the documented JSON result shape for an analysis technique."""
    try:
        selected_technique = (
            technique
            if isinstance(technique, AnalysisTechnique)
            else AnalysisTechnique(technique)
        )
    except (TypeError, ValueError) as exc:
        raise ArchaeometryValidationError("Unsupported archaeometry technique") from exc
    if not isinstance(results, Mapping):
        raise ArchaeometryValidationError("Technique results must be a JSON object")
    try:
        serialized = json.dumps(
            dict(results), allow_nan=False, ensure_ascii=False, separators=(",", ":")
        )
    except (TypeError, ValueError) as exc:
        raise ArchaeometryValidationError(
            "Technique results must contain finite JSON-compatible values"
        ) from exc
    if len(serialized.encode("utf-8")) > _MAX_RESULT_BYTES:
        raise ArchaeometryValidationError(
            "Structured technique results exceed the configured size limit"
        )
    normalized = json.loads(serialized)

    if selected_technique in _ELEMENTAL_TECHNIQUES:
        _require_keys(normalized, {"elemental_composition"})
        composition = normalized["elemental_composition"]
        if not isinstance(composition, dict) or not composition:
            raise ArchaeometryValidationError(
                "elemental_composition must contain at least one element"
            )
        for element, percentage in composition.items():
            if element not in _ELEMENTS:
                raise ArchaeometryValidationError(
                    f"Unknown chemical element symbol: {element}"
                )
            _validate_percentage(percentage, f"{element} mass percentage")
    elif selected_technique == AnalysisTechnique.XRD:
        _require_keys(normalized, {"phases"})
        phases = normalized["phases"]
        if not isinstance(phases, list):
            raise ArchaeometryValidationError("phases must be an array")
        for index, phase in enumerate(phases):
            label = f"phases[{index}]"
            if not isinstance(phase, dict) or set(phase) - {
                "phase",
                "reference_pattern",
                "abundance_wt_percent",
            }:
                raise ArchaeometryValidationError(f"{label} has an invalid shape")
            if not isinstance(phase.get("phase"), str) or not phase["phase"].strip():
                raise ArchaeometryValidationError(f"{label}.phase is required")
            reference = phase.get("reference_pattern")
            if reference is not None and (
                not isinstance(reference, str) or not reference.strip()
            ):
                raise ArchaeometryValidationError(
                    f"{label}.reference_pattern must be non-empty text"
                )
            if "abundance_wt_percent" in phase:
                _validate_percentage(
                    phase["abundance_wt_percent"],
                    f"{label}.abundance_wt_percent",
                )
    else:
        _require_keys(normalized, {"diagnostic_bands"})
        bands = normalized["diagnostic_bands"]
        if not isinstance(bands, list):
            raise ArchaeometryValidationError("diagnostic_bands must be an array")
        for index, band in enumerate(bands):
            label = f"diagnostic_bands[{index}]"
            if not isinstance(band, dict) or set(band) - {
                "wavenumber_cm1",
                "intensity",
                "assignment",
            }:
                raise ArchaeometryValidationError(f"{label} has an invalid shape")
            wavenumber = band.get("wavenumber_cm1")
            intensity = band.get("intensity")
            if (
                isinstance(wavenumber, bool)
                or not isinstance(wavenumber, (int, float))
                or not _is_finite_number(wavenumber)
                or wavenumber <= 0
            ):
                raise ArchaeometryValidationError(
                    f"{label}.wavenumber_cm1 must be finite and positive"
                )
            if (
                isinstance(intensity, bool)
                or not isinstance(intensity, (int, float))
                or not _is_finite_number(intensity)
            ):
                raise ArchaeometryValidationError(
                    f"{label}.intensity must be finite"
                )
            assignment = band.get("assignment")
            if assignment is not None and (
                not isinstance(assignment, str) or not assignment.strip()
            ):
                raise ArchaeometryValidationError(
                    f"{label}.assignment must be non-empty text"
                )
    return normalized


def _require_keys(results: Mapping[str, object], expected: set[str]) -> None:
    if set(results) != expected:
        raise ArchaeometryValidationError(
            "Technique result fields must be exactly: "
            + ", ".join(sorted(expected))
        )


def _validate_percentage(value: object, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not _is_finite_number(value)
        or not 0 <= value <= 100
    ):
        raise ArchaeometryValidationError(
            f"{label} must be a finite percentage between 0 and 100"
        )


def _is_finite_number(value: int | float) -> bool:
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True, slots=True)
class MaterialAnalysisEvent:
    """Validated writeback envelope; binary data remains in object storage."""

    event_id: UUID
    find_id: UUID
    technique: AnalysisTechnique
    analyst_id: UUID
    analyst_name: str
    performed_at: datetime
    raw_instrument_file_uri: str
    raw_file_sha256: str
    report_media_asset_id: UUID
    results: Mapping[str, object]
    pipeline_version: str
    processing_parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        for field_name in (
            "event_id",
            "find_id",
            "analyst_id",
            "report_media_asset_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise ArchaeometryValidationError(f"{field_name} must be a UUID")
        if not isinstance(self.technique, AnalysisTechnique):
            try:
                object.__setattr__(self, "technique", AnalysisTechnique(self.technique))
            except (TypeError, ValueError) as exc:
                raise ArchaeometryValidationError(
                    "Unsupported archaeometry technique"
                ) from exc
        if not isinstance(self.analyst_name, str) or not self.analyst_name.strip():
            raise ArchaeometryValidationError("Analyst attribution is required")
        if not isinstance(self.pipeline_version, str) or not self.pipeline_version.strip():
            raise ArchaeometryValidationError("Pipeline version is required")
        if (
            not isinstance(self.performed_at, datetime)
            or self.performed_at.tzinfo is None
            or self.performed_at.utcoffset() is None
        ):
            raise ArchaeometryValidationError(
                "performed_at must be timezone-aware"
            )
        if not isinstance(self.raw_instrument_file_uri, str):
            raise ArchaeometryValidationError(
                "Raw instrument data must use a valid S3/MinIO object URI"
            )
        try:
            parsed_uri = urlsplit(self.raw_instrument_file_uri)
            parsed_uri.port
        except (TypeError, ValueError) as exc:
            raise ArchaeometryValidationError(
                "Raw instrument data must use a valid S3/MinIO object URI"
            ) from exc
        if (
            parsed_uri.scheme not in {"s3", "minio"}
            or not parsed_uri.hostname
            or parsed_uri.path in {"", "/"}
            or parsed_uri.username is not None
            or parsed_uri.password is not None
            or parsed_uri.query
            or parsed_uri.fragment
        ):
            raise ArchaeometryValidationError(
                "Raw instrument data must use an S3/MinIO object URI"
            )
        if not isinstance(self.raw_file_sha256, str) or not _SHA256.fullmatch(
            self.raw_file_sha256
        ):
            raise ArchaeometryValidationError(
                "Raw instrument file requires a SHA-256 checksum"
            )
        normalized_results = validate_technique_results(
            self.technique, self.results
        )
        try:
            serialized_parameters = json.dumps(
                dict(self.processing_parameters),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise ArchaeometryValidationError(
                "Processing parameters must be finite JSON-compatible data"
            ) from exc
        if len(serialized_parameters.encode("utf-8")) > _MAX_RESULT_BYTES:
            raise ArchaeometryValidationError(
                "Processing parameters exceed the configured size limit"
            )
        parameters = json.loads(serialized_parameters)
        object.__setattr__(self, "results", _freeze_json(normalized_results))
        object.__setattr__(
            self, "processing_parameters", _freeze_json(parameters)
        )
        object.__setattr__(self, "raw_file_sha256", self.raw_file_sha256.lower())

    def writeback_payload(self) -> dict[str, object]:
        """Return JSON-compatible metadata for the configured API writeback."""
        return {
            "id": str(self.event_id),
            "find_id": str(self.find_id),
            "technique": self.technique.value,
            "analyst_id": str(self.analyst_id),
            "analyst_name": self.analyst_name.strip(),
            "performed_at": self.performed_at.astimezone(timezone.utc).isoformat(),
            "raw_instrument_file_uri": self.raw_instrument_file_uri,
            "raw_file_sha256": self.raw_file_sha256,
            "report_media_asset_id": str(self.report_media_asset_id),
            "technique_results": _thaw_json(self.results),
            "pipeline_version": self.pipeline_version,
            "processing_parameters": _thaw_json(self.processing_parameters),
        }


def _freeze_json(value: object) -> object:
    if isinstance(value, MappingABC):
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if isinstance(value, MappingABC):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value
