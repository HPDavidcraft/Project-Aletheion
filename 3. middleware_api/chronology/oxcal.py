"""Safe adapter boundary for a deployment-managed OxCal wrapper."""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence
from urllib.parse import urlsplit
from uuid import UUID

from .distribution import DistributionValidationError, TemporalDistribution

CALIBRATION_CURVES = frozenset({"IntCal20", "Marine20", "SHCal20"})


class OxCalExecutionError(RuntimeError):
    """Raised when the configured OxCal adapter fails or returns invalid data."""


@dataclass(frozen=True, slots=True)
class OxCalRequest:
    sample_id: UUID
    raw_date_bp: float
    error_margin_1sigma: float
    curve_code: str
    parameter_set_id: UUID
    notebook_version: str
    parameters: Mapping[str, object]
    execution_timestamp: datetime

    def __post_init__(self) -> None:
        if not math.isfinite(self.raw_date_bp):
            raise ValueError("raw_date_bp must be finite")
        if (
            not math.isfinite(self.error_margin_1sigma)
            or self.error_margin_1sigma <= 0
        ):
            raise ValueError("error_margin_1sigma must be finite and positive")
        if self.curve_code not in CALIBRATION_CURVES:
            raise ValueError(f"Unsupported calibration curve: {self.curve_code}")
        if not isinstance(self.notebook_version, str) or not self.notebook_version.strip():
            raise ValueError("notebook_version is required for reproducibility")
        if (
            not isinstance(self.execution_timestamp, datetime)
            or self.execution_timestamp.tzinfo is None
        ):
            raise ValueError("execution_timestamp must be timezone-aware")
        if not isinstance(self.parameters, Mapping):
            raise ValueError("parameters must be a mapping")
        try:
            json.dumps(dict(self.parameters), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("parameters must be finite JSON-compatible data") from exc

    def to_payload(self) -> dict[str, object]:
        return {
            "sample_id": str(self.sample_id),
            "raw_date_bp": self.raw_date_bp,
            "error_margin_1sigma": self.error_margin_1sigma,
            "curve_code": self.curve_code,
            "parameter_set_id": str(self.parameter_set_id),
            "notebook_version": self.notebook_version,
            "parameters": dict(self.parameters),
            "execution_timestamp": self.execution_timestamp.astimezone(
                timezone.utc
            ).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OxCalResult:
    distribution: TemporalDistribution
    software_name: str
    software_version: str
    result_uri: str | None
    request: OxCalRequest


class OxCalRunner:
    """Run a trusted, deployment-provided JSON adapter without invoking a shell.

    OxCal command-line details vary by installation. The configured executable
    must translate the request JSON on stdin to the result JSON documented in
    the module README; this class does not pretend OxCal itself has that
    universal protocol.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 180.0,
        max_output_bytes: int = 2_000_000,
    ) -> None:
        if (
            isinstance(command, (str, bytes))
            or not command
            or any(not isinstance(arg, str) or not arg for arg in command)
        ):
            raise ValueError("command must contain a configured executable")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        self._command = tuple(command)
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes

    def calibrate(self, request: OxCalRequest) -> OxCalResult:
        payload = json.dumps(request.to_payload(), allow_nan=False)
        try:
            completed = subprocess.run(
                self._command,
                input=payload,
                text=True,
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise OxCalExecutionError(
                f"OxCal adapter exceeded {self._timeout_seconds:g} seconds"
            ) from exc
        except OSError as exc:
            raise OxCalExecutionError("Could not start the configured OxCal adapter") from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip()[:1000]
            raise OxCalExecutionError(
                f"OxCal adapter exited with status {completed.returncode}"
                + (f": {detail}" if detail else "")
            )
        if len(completed.stdout.encode("utf-8")) > self._max_output_bytes:
            raise OxCalExecutionError("OxCal adapter output exceeds the configured limit")

        try:
            result = json.loads(completed.stdout)
            if not isinstance(result, dict):
                raise TypeError("adapter response must be a JSON object")
            distribution_data = result["distribution"]
            if not isinstance(distribution_data, dict):
                raise TypeError("distribution must be a JSON object")
            pairs = distribution_data["probability_curve"]
            if not isinstance(pairs, list) or any(
                not isinstance(point, list)
                or len(point) != 2
                or any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    for value in point
                )
                for point in pairs
            ):
                raise TypeError("probability_curve must be an array of numeric pairs")
            bounds = (distribution_data["p_start"], distribution_data["p_end"])
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in bounds
            ):
                raise TypeError("distribution bounds must be numeric")
            distribution = TemporalDistribution.from_pairs(
                p_start=float(bounds[0]),
                p_end=float(bounds[1]),
                pairs=(
                    (float(point[0]), float(point[1]))
                    for point in pairs
                ),
            )
            software_name = result["software_name"]
            software_version = result["software_version"]
            result_uri = result.get("result_uri")
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            IndexError,
            OverflowError,
            DistributionValidationError,
        ) as exc:
            raise OxCalExecutionError(
                "OxCal adapter returned malformed calibration output"
            ) from exc

        if (
            not isinstance(software_name, str)
            or not software_name.strip()
            or not isinstance(software_version, str)
            or not software_version.strip()
        ):
            raise OxCalExecutionError(
                "OxCal adapter output must identify software name and version"
            )
        if result_uri is not None:
            if not isinstance(result_uri, str):
                raise OxCalExecutionError("OxCal result_uri must be an external asset URI")
            try:
                parsed_uri = urlsplit(result_uri)
            except ValueError as exc:
                raise OxCalExecutionError(
                    "OxCal result_uri must be an external asset URI"
                ) from exc
            if (
                parsed_uri.scheme not in {"https", "http", "s3", "minio"}
                or not parsed_uri.netloc
            ):
                raise OxCalExecutionError("OxCal result_uri must be an external asset URI")

        return OxCalResult(
            distribution=distribution,
            software_name=software_name,
            software_version=software_version,
            result_uri=result_uri,
            request=request,
        )
