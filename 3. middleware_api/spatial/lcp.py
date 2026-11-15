"""Least-cost-path request validation and GRASS adapter boundary."""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Sequence
from urllib.parse import urlsplit
from uuid import UUID

from .geojson import GeoJSONLineString, validate_linestring


class LCPExecutionError(RuntimeError):
    """Raised when the configured GRASS adapter fails or returns invalid data."""


ENERGY_MODELS = frozenset({"tobler_hiking", "pandolf_load_carrying"})
GRASS_ALGORITHMS = frozenset({"r.cost", "r.walk"})


def _validate_coordinate(value: tuple[float, float], field_name: str) -> None:
    if len(value) != 2:
        raise ValueError(f"{field_name} must be a longitude/latitude pair")
    longitude, latitude = value
    if (
        isinstance(longitude, bool)
        or isinstance(latitude, bool)
        or not math.isfinite(longitude)
        or not math.isfinite(latitude)
        or not -180 <= longitude <= 180
        or not -90 <= latitude <= 90
    ):
        raise ValueError(f"{field_name} must be a valid WGS 84 coordinate")


def _external_uri(value: str, schemes: set[str], label: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in schemes
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{label} must be an external URI with an allowed scheme")


@dataclass(frozen=True, slots=True)
class LCPRequest:
    movement_category_uri: str
    dem_source_uri: str
    dem_resolution_m: float
    start_lon_lat: tuple[float, float]
    end_lon_lat: tuple[float, float]
    energy_model: str
    grass_algorithm: str
    parameter_set_id: UUID
    notebook_version: str
    execution_timestamp: datetime
    barrier_sources: tuple[str, ...] = ()
    traveler_weight_kg: float | None = None
    carried_load_kg: float | None = None
    parameters: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        _external_uri(self.movement_category_uri, {"http", "https"}, "movement_category_uri")
        _external_uri(self.dem_source_uri, {"http", "https"}, "dem_source_uri")
        if (
            isinstance(self.dem_resolution_m, bool)
            or not math.isfinite(self.dem_resolution_m)
            or self.dem_resolution_m <= 0
            or self.dem_resolution_m > 30
        ):
            raise ValueError("DEM resolution must be 30 m or finer")
        _validate_coordinate(self.start_lon_lat, "start_lon_lat")
        _validate_coordinate(self.end_lon_lat, "end_lon_lat")
        if self.start_lon_lat == self.end_lon_lat:
            raise ValueError("LCP origin and destination must differ")
        if self.energy_model not in ENERGY_MODELS:
            raise ValueError(f"Unsupported energy model: {self.energy_model}")
        if self.grass_algorithm not in GRASS_ALGORITHMS:
            raise ValueError(f"Unsupported GRASS algorithm: {self.grass_algorithm}")
        if self.energy_model == "pandolf_load_carrying":
            for name, value in (
                ("traveler_weight_kg", self.traveler_weight_kg),
                ("carried_load_kg", self.carried_load_kg),
            ):
                if (
                    value is None
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    or value <= 0
                ):
                    raise ValueError(
                        f"{name} must be finite and positive for the Pandolf model"
                    )
        elif self.traveler_weight_kg is not None or self.carried_load_kg is not None:
            raise ValueError("Pandolf load parameters are not valid for the Tobler model")
        if not self.notebook_version.strip():
            raise ValueError("notebook_version is required for reproducibility")
        if (
            not isinstance(self.execution_timestamp, datetime)
            or self.execution_timestamp.tzinfo is None
        ):
            raise ValueError("execution_timestamp must be timezone-aware")
        if any(not isinstance(source, str) or not source.strip()
               for source in self.barrier_sources):
            raise ValueError("Barrier source identifiers cannot be empty")
        try:
            json.dumps(dict(self.parameters or {}), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("parameters must be finite JSON-compatible data") from exc

    def to_payload(self) -> dict[str, object]:
        return {
            "movement_category_uri": self.movement_category_uri,
            "dem_source_uri": self.dem_source_uri,
            "dem_resolution_m": self.dem_resolution_m,
            "start_lon_lat": list(self.start_lon_lat),
            "end_lon_lat": list(self.end_lon_lat),
            "energy_model": self.energy_model,
            "grass_algorithm": self.grass_algorithm,
            "parameter_set_id": str(self.parameter_set_id),
            "notebook_version": self.notebook_version,
            "execution_timestamp": self.execution_timestamp.astimezone(
                timezone.utc
            ).isoformat(),
            "barrier_sources": list(self.barrier_sources),
            "traveler_weight_kg": self.traveler_weight_kg,
            "carried_load_kg": self.carried_load_kg,
            "parameters": dict(self.parameters or {}),
        }


@dataclass(frozen=True, slots=True)
class LCPResult:
    path: GeoJSONLineString
    cost_surface_uri: str
    total_cost: float
    adapter_version: str
    grass_version: str
    request: LCPRequest

    def movement_vector_payload(self) -> dict[str, object]:
        request = self.request
        provenance = request.to_payload()
        provenance.update(
            {
                "adapter_version": self.adapter_version,
                "grass_version": self.grass_version,
                "total_cost": self.total_cost,
            }
        )
        return {
            "geometry": self.path.as_geojson(),
            "movement_category_uri": request.movement_category_uri,
            "route_source": "LCP_computed",
            "lcp_energy_model": request.energy_model,
            "dem_source_uri": request.dem_source_uri,
            "cost_surface_uri": self.cost_surface_uri,
            "lcp_parameters": provenance,
        }


class GrassLCPRunner:
    """Call a trusted adapter that prepares inputs and runs GRASS r.cost/r.walk.

    The adapter executable translates the documented JSON contract to its
    deployment's GRASS GIS installation. No shell is used and request data is
    passed only on stdin.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        allowed_input_hosts: frozenset[str],
        timeout_seconds: float = 900,
        max_output_bytes: int = 2_000_000,
    ) -> None:
        if (
            isinstance(command, (str, bytes))
            or not command
            or any(not isinstance(arg, str) or not arg for arg in command)
        ):
            raise ValueError("command must contain a configured adapter executable")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        allowed_hosts = frozenset(
            host.lower().rstrip(".") for host in allowed_input_hosts
        )
        if not allowed_hosts:
            raise ValueError("At least one trusted DEM/barrier host is required")
        self._command = tuple(command)
        self._allowed_input_hosts = allowed_hosts
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes

    def calculate(self, request: LCPRequest) -> LCPResult:
        dem_host = urlsplit(request.dem_source_uri).hostname
        if dem_host is None or dem_host.lower().rstrip(".") not in self._allowed_input_hosts:
            raise LCPExecutionError("DEM source host is not allowlisted")
        for source in request.barrier_sources:
            if "://" in source:
                parsed_source = urlsplit(source)
                if (
                    parsed_source.scheme not in {"http", "https"}
                    or parsed_source.hostname is None
                    or parsed_source.hostname.lower().rstrip(".")
                    not in self._allowed_input_hosts
                ):
                    raise LCPExecutionError(
                        "Barrier source URI must use an allowlisted HTTP(S) host"
                    )
            elif any(ord(char) < 0x20 for char in source):
                raise LCPExecutionError("Barrier source identifiers cannot contain controls")

        try:
            completed = subprocess.run(
                self._command,
                input=json.dumps(request.to_payload(), allow_nan=False),
                text=True,
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LCPExecutionError(
                f"GRASS adapter exceeded {self._timeout_seconds:g} seconds"
            ) from exc
        except OSError as exc:
            raise LCPExecutionError("Could not start the configured GRASS adapter") from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip()[:1000]
            raise LCPExecutionError(
                f"GRASS adapter exited with status {completed.returncode}"
                + (f": {detail}" if detail else "")
            )
        if len(completed.stdout.encode("utf-8")) > self._max_output_bytes:
            raise LCPExecutionError("GRASS adapter output exceeds the configured limit")

        try:
            response = json.loads(completed.stdout)
            if not isinstance(response, dict):
                raise TypeError("response must be a JSON object")
            path = validate_linestring(response["path_geojson"])
            cost_surface_uri = response["cost_surface_uri"]
            total_cost = response["total_cost"]
            adapter_version = response["adapter_version"]
            grass_version = response["grass_version"]
            if (
                isinstance(total_cost, bool)
                or not isinstance(total_cost, (int, float))
                or not math.isfinite(total_cost)
                or total_cost < 0
            ):
                raise ValueError("total_cost must be a finite non-negative number")
            if not isinstance(cost_surface_uri, str):
                raise TypeError("cost_surface_uri must be a string")
            _external_uri(
                cost_surface_uri,
                {"s3", "minio"},
                "cost_surface_uri",
            )
            path_start = path.coordinates[0]
            path_end = path.coordinates[-1]
            if any(
                abs(actual - requested) > 1e-5
                for actual, requested in zip(path_start, request.start_lon_lat)
            ) or any(
                abs(actual - requested) > 1e-5
                for actual, requested in zip(path_end, request.end_lon_lat)
            ):
                raise ValueError("LCP path endpoints do not match the requested origin and destination")
            for label, version in (
                ("adapter_version", adapter_version),
                ("grass_version", grass_version),
            ):
                if not isinstance(version, str) or not version.strip():
                    raise ValueError(f"{label} is required")
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ) as exc:
            raise LCPExecutionError(
                "GRASS adapter returned malformed least-cost-path output"
            ) from exc

        return LCPResult(
            path=path,
            cost_surface_uri=cost_surface_uri,
            total_cost=float(total_cost),
            adapter_version=adapter_version,
            grass_version=grass_version,
            request=request,
        )
