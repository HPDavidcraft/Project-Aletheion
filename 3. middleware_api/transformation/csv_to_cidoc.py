"""Profile-driven, fail-closed CSV conversion to expanded CIDOC CRM JSON-LD."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, Protocol
from urllib.parse import quote, urlsplit

from chronology.edtf import parse_edtf

from .coordinates import (
    BasicCoordinateTransformer,
    CoordinateTransformError,
    CoordinateTransformer,
)


_XSD = "http://www.w3.org/2001/XMLSchema#"
_GEOSPARQL_GEOJSON = "http://www.opengis.net/ont/geosparql#geoJSONLiteral"
_KINDS = frozenset(
    {"literal", "uri", "edtf", "controlled_uri", "integer", "decimal", "boolean"}
)
_INTEGER = re.compile(r"[+-]?\d+\Z")
_DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


class TransformationConfigurationError(ValueError):
    """Raised when an import profile or verified CRM mapping is invalid."""


@dataclass(frozen=True, slots=True)
class RowIssue:
    row_number: int
    field: str
    message: str


class CSVTransformationError(ValueError):
    """Raised when any source row is invalid; no partial graph is returned."""

    def __init__(self, issues: tuple[RowIssue, ...]) -> None:
        self.issues = issues
        details = "; ".join(
            f"row {issue.row_number}"
            + (f", field {issue.field!r}" if issue.field else "")
            + f": {issue.message}"
            for issue in issues[:5]
        )
        if len(issues) > 5:
            details += f"; and {len(issues) - 5} more issue(s)"
        super().__init__(details or "CSV transformation failed")


@dataclass(frozen=True, slots=True)
class CRMMapping:
    target_uri: str
    relation: str
    status: str
    standard_code: str
    standard_release: str

    def __post_init__(self) -> None:
        _require_http_uri(self.target_uri, "CRM mapping target")
        if not self.standard_code.strip() or not self.standard_release.strip():
            raise TransformationConfigurationError(
                "CRM mappings require a pinned standard and release"
            )


class CRMMappingRegistry(Protocol):
    def class_mapping(self, project_class_uri: str) -> CRMMapping | None:
        """Return the mapping-registry entry for a project class."""

    def property_mapping(self, project_property_uri: str) -> CRMMapping | None:
        """Return the mapping-registry entry for a project property."""


def _require_http_uri(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise TransformationConfigurationError(f"{label} must be an absolute HTTP(S) URI")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as exc:
        raise TransformationConfigurationError(
            f"{label} must be an absolute HTTP(S) URI"
        ) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(char.isspace() or char in '<>"{}|\\^`' for char in value)
    ):
        raise TransformationConfigurationError(
            f"{label} must be an absolute HTTP(S) URI"
        )


@dataclass(frozen=True, slots=True)
class FieldMapping:
    source_column: str
    project_property_uri: str
    value_kind: Literal[
        "literal",
        "uri",
        "edtf",
        "controlled_uri",
        "integer",
        "decimal",
        "boolean",
    ]
    required: bool = False
    vocabulary: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.source_column.strip():
            raise TransformationConfigurationError("Mapped CSV column is required")
        _require_http_uri(self.project_property_uri, "Project property URI")
        if not isinstance(self.value_kind, str) or self.value_kind not in _KINDS:
            raise TransformationConfigurationError(
                f"Unsupported field value kind: {self.value_kind}"
            )
        if self.value_kind == "controlled_uri":
            if not self.vocabulary:
                raise TransformationConfigurationError(
                    "controlled_uri fields require an explicit code-to-URI mapping"
                )
            checked: dict[str, str] = {}
            for code, uri in self.vocabulary.items():
                if not isinstance(code, str) or not code.strip():
                    raise TransformationConfigurationError(
                        "Vocabulary codes must be non-empty strings"
                    )
                _require_http_uri(uri, "Controlled vocabulary URI")
                checked[code] = uri
            object.__setattr__(self, "vocabulary", MappingProxyType(checked))
        elif self.vocabulary is not None:
            raise TransformationConfigurationError(
                "vocabulary mappings are only valid for controlled_uri fields"
            )


@dataclass(frozen=True, slots=True)
class CoordinateMapping:
    x_column: str
    y_column: str
    source_crs: str
    project_property_uri: str

    def __post_init__(self) -> None:
        if (
            not self.x_column.strip()
            or not self.y_column.strip()
            or self.x_column == self.y_column
            or not self.source_crs.strip()
        ):
            raise TransformationConfigurationError(
                "Coordinate columns and source CRS must be distinct and non-empty"
            )
        _require_http_uri(self.project_property_uri, "Project geometry property URI")


@dataclass(frozen=True, slots=True)
class CSVMappingProfile:
    profile_id: str
    version: str
    entity_namespace: str
    project_class_uri: str
    identifier_column: str
    fields: tuple[FieldMapping, ...]
    coordinate: CoordinateMapping | None = None
    ignored_columns: frozenset[str] = frozenset()
    delimiter: str = ","

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.version.strip():
            raise TransformationConfigurationError(
                "Mapping profile ID and version are required"
            )
        _require_http_uri(self.entity_namespace, "Entity namespace")
        parsed_namespace = urlsplit(self.entity_namespace)
        if (
            parsed_namespace.scheme not in {"http", "https"}
            or not parsed_namespace.hostname
            or parsed_namespace.username is not None
            or parsed_namespace.password is not None
            or parsed_namespace.query
            or parsed_namespace.fragment
        ):
            raise TransformationConfigurationError(
                "Entity namespace must be a base HTTP(S) URI without query or fragment"
            )
        _require_http_uri(self.project_class_uri, "Project class URI")
        if not self.identifier_column.strip():
            raise TransformationConfigurationError("Identifier column is required")
        if len(self.delimiter) != 1 or self.delimiter in "\r\n":
            raise TransformationConfigurationError("CSV delimiter must be one character")

        object.__setattr__(self, "fields", tuple(self.fields))
        columns = [self.identifier_column]
        columns.extend(field.source_column for field in self.fields)
        properties = [field.project_property_uri for field in self.fields]
        if self.coordinate is not None:
            columns.extend((self.coordinate.x_column, self.coordinate.y_column))
            properties.append(self.coordinate.project_property_uri)
        if len(columns) != len(set(columns)):
            raise TransformationConfigurationError(
                "Each CSV source column may be assigned only once"
            )
        if len(properties) != len(set(properties)):
            raise TransformationConfigurationError(
                "Each project property may be mapped only once per profile"
            )
        ignored = frozenset(self.ignored_columns)
        if any(not column.strip() for column in ignored):
            raise TransformationConfigurationError(
                "Ignored CSV column names must be non-empty"
            )
        if set(columns) & ignored:
            raise TransformationConfigurationError(
                "A CSV column cannot be both mapped and ignored"
            )
        object.__setattr__(self, "ignored_columns", ignored)

    @property
    def expected_columns(self) -> frozenset[str]:
        columns = {self.identifier_column, *(field.source_column for field in self.fields)}
        if self.coordinate is not None:
            columns.update((self.coordinate.x_column, self.coordinate.y_column))
        columns.update(self.ignored_columns)
        return frozenset(columns)


@dataclass(frozen=True, slots=True)
class CSVTransformationResult:
    graph: tuple[dict[str, object], ...]
    source_sha256: str
    source_row_count: int
    profile_id: str
    profile_version: str
    crm_releases: tuple[str, ...]

    def to_jsonld(self) -> dict[str, object]:
        return {"@graph": list(self.graph)}

    def to_json(self) -> str:
        return json.dumps(
            self.to_jsonld(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )


class CSVToCIDOCTransformer:
    """Validate a whole CSV file and return JSON-LD only when every row is valid."""

    def __init__(
        self,
        registry: CRMMappingRegistry,
        *,
        coordinate_transformer: CoordinateTransformer | None = None,
        max_file_bytes: int = 25_000_000,
        max_rows: int = 100_000,
        max_issues: int = 1_000,
    ) -> None:
        if (
            isinstance(max_file_bytes, bool)
            or not isinstance(max_file_bytes, int)
            or max_file_bytes <= 0
        ):
            raise ValueError("max_file_bytes must be positive")
        if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows <= 0:
            raise ValueError("max_rows must be positive")
        if (
            isinstance(max_issues, bool)
            or not isinstance(max_issues, int)
            or max_issues <= 0
        ):
            raise ValueError("max_issues must be positive")
        self._registry = registry
        self._coordinates = coordinate_transformer or BasicCoordinateTransformer()
        self._max_file_bytes = max_file_bytes
        self._max_rows = max_rows
        self._max_issues = max_issues

    def transform_file(
        self, source_path: str | Path, profile: CSVMappingProfile
    ) -> CSVTransformationResult:
        path = Path(source_path)
        if path.suffix.casefold() != ".csv":
            raise CSVTransformationError(
                (
                    RowIssue(
                        0,
                        "",
                        "Only open CSV source files are accepted; convert proprietary formats first",
                    ),
                )
            )
        try:
            with path.open("rb") as source_file:
                raw = source_file.read(self._max_file_bytes + 1)
        except OSError as exc:
            raise CSVTransformationError(
                (RowIssue(0, "", f"Could not read the CSV source: {exc.strerror or 'I/O error'}"),)
            ) from exc
        if len(raw) > self._max_file_bytes:
            raise CSVTransformationError(
                (RowIssue(0, "", "CSV source exceeds the configured byte limit"),)
            )
        return self.transform_bytes(raw, profile)

    def transform_bytes(
        self, raw: bytes, profile: CSVMappingProfile
    ) -> CSVTransformationResult:
        if len(raw) > self._max_file_bytes:
            raise CSVTransformationError(
                (RowIssue(0, "", "CSV source exceeds the configured byte limit"),)
            )
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise CSVTransformationError(
                (RowIssue(0, "", "CSV source must be UTF-8 encoded"),)
            ) from exc

        class_mapping, property_mappings, releases = self._verified_mappings(profile)
        try:
            reader = csv.DictReader(
                io.StringIO(text, newline=""),
                delimiter=profile.delimiter,
                strict=True,
            )
            headers = reader.fieldnames
        except csv.Error as exc:
            raise CSVTransformationError(
                (RowIssue(1, "", "CSV header could not be parsed"),)
            ) from exc

        if not headers:
            raise CSVTransformationError((RowIssue(1, "", "CSV header is missing"),))
        if any(not header or header != header.strip() for header in headers):
            raise CSVTransformationError(
                (RowIssue(1, "", "CSV headers must be non-empty and trimmed"),)
            )
        if len(headers) != len(set(headers)):
            raise CSVTransformationError((RowIssue(1, "", "CSV headers must be unique"),))
        missing = profile.expected_columns - set(headers)
        unexpected = set(headers) - profile.expected_columns
        header_issues = []
        if missing:
            header_issues.append(
                RowIssue(1, "", f"Required or unaccounted-for columns are missing: {sorted(missing)}")
            )
        if unexpected:
            header_issues.append(
                RowIssue(1, "", f"Columns must be mapped or explicitly ignored: {sorted(unexpected)}")
            )
        if header_issues:
            raise CSVTransformationError(tuple(header_issues))

        graph: list[dict[str, object]] = []
        issues: list[RowIssue] = []
        seen_identifiers: set[str] = set()
        source_row_count = 0
        try:
            for row in reader:
                row_number = reader.line_num
                if row and all(value is None or not value.strip() for value in row.values()):
                    continue
                source_row_count += 1
                if source_row_count > self._max_rows:
                    issues.append(
                        RowIssue(
                            row_number,
                            "",
                            "CSV source exceeds the configured row limit",
                        )
                    )
                    break
                if None in row or any(value is None for value in row.values()):
                    issues.append(
                        RowIssue(row_number, "", "CSV row has a different number of values than its header")
                    )
                    if len(issues) >= self._max_issues:
                        break
                    continue
                try:
                    identifier = row[profile.identifier_column].strip()
                    if not identifier:
                        raise _RowValueError(profile.identifier_column, "identifier is empty")
                    if identifier in seen_identifiers:
                        raise _RowValueError(profile.identifier_column, "identifier is duplicated")
                    node: dict[str, object] = {
                        "@id": profile.entity_namespace.rstrip("/")
                        + "/"
                        + quote(identifier, safe="-._~"),
                        "@type": [profile.project_class_uri, class_mapping.target_uri],
                    }
                    for field in profile.fields:
                        converted = _convert_field(row[field.source_column], field)
                        if converted is not None:
                            node[property_mappings[field.project_property_uri]] = converted
                    if profile.coordinate is not None:
                        geometry = _convert_coordinate(
                            row[profile.coordinate.x_column],
                            row[profile.coordinate.y_column],
                            profile.coordinate,
                            self._coordinates,
                        )
                        if geometry is not None:
                            node[
                                property_mappings[profile.coordinate.project_property_uri]
                            ] = geometry
                    seen_identifiers.add(identifier)
                    graph.append(node)
                except _RowValueError as exc:
                    issues.append(RowIssue(row_number, exc.field, exc.message))
                if len(issues) >= self._max_issues:
                    break
        except csv.Error as exc:
            issues.append(
                RowIssue(reader.line_num, "", "CSV row syntax is invalid")
            )

        if source_row_count == 0 and not issues:
            issues.append(RowIssue(2, "", "CSV contains no data rows"))
        if issues:
            raise CSVTransformationError(tuple(issues))

        return CSVTransformationResult(
            graph=tuple(graph),
            source_sha256=hashlib.sha256(raw).hexdigest(),
            source_row_count=source_row_count,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            crm_releases=tuple(sorted(releases)),
        )

    def _verified_mappings(
        self, profile: CSVMappingProfile
    ) -> tuple[CRMMapping, dict[str, str], set[str]]:
        class_mapping = self._registry.class_mapping(profile.project_class_uri)
        if class_mapping is None:
            raise TransformationConfigurationError(
                "No CRM class mapping is registered for the profile"
            )
        self._require_mapping(
            class_mapping,
            allowed_relations={"subClassOf", "exactMatch"},
            label="CRM class",
        )
        project_properties = [
            field.project_property_uri for field in profile.fields
        ]
        if profile.coordinate is not None:
            project_properties.append(profile.coordinate.project_property_uri)
        property_mappings: dict[str, str] = {}
        releases = {class_mapping.standard_release}
        for project_property in project_properties:
            mapping = self._registry.property_mapping(project_property)
            if mapping is None:
                raise TransformationConfigurationError(
                    f"No CRM property mapping is registered for {project_property}"
                )
            self._require_mapping(
                mapping,
                allowed_relations={"exactMatch"},
                label=f"CRM property {project_property}",
            )
            property_mappings[project_property] = mapping.target_uri
            releases.add(mapping.standard_release)
        if len(set(property_mappings.values())) != len(property_mappings):
            raise TransformationConfigurationError(
                "Different source fields map to the same CRM property"
            )
        return class_mapping, property_mappings, releases

    @staticmethod
    def _require_mapping(
        mapping: CRMMapping, *, allowed_relations: set[str], label: str
    ) -> None:
        if mapping.status != "verified":
            raise TransformationConfigurationError(
                f"{label} mapping must be verified before import"
            )
        if mapping.relation not in allowed_relations:
            raise TransformationConfigurationError(
                f"{label} mapping relation is not safe for direct conversion"
            )


class _RowValueError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(message)


def _convert_field(value: str, field: FieldMapping) -> object | None:
    value = value.strip()
    if not value:
        if field.required:
            raise _RowValueError(field.source_column, "required value is empty")
        return None

    if field.value_kind == "literal":
        return {"@value": value}
    if field.value_kind == "uri":
        _require_row_uri(value, field.source_column)
        return {"@id": value}
    if field.value_kind == "edtf":
        try:
            normalized = parse_edtf(value).raw
        except ValueError as exc:
            raise _RowValueError(field.source_column, "invalid EDTF value") from exc
        return {"@value": normalized, "@type": _XSD + "string"}
    if field.value_kind == "controlled_uri":
        vocabulary = field.vocabulary
        if vocabulary is None:
            raise TransformationConfigurationError(
                "controlled_uri field has no configured vocabulary"
            )
        target_uri = vocabulary.get(value)
        if target_uri is None:
            raise _RowValueError(
                field.source_column, "value is not in the configured controlled vocabulary"
            )
        return {"@id": target_uri}
    if field.value_kind == "integer":
        if len(value) > 256 or not _INTEGER.fullmatch(value):
            raise _RowValueError(field.source_column, "invalid integer")
        return {"@value": int(value), "@type": _XSD + "integer"}
    if field.value_kind == "decimal":
        if len(value) > 256 or not _DECIMAL.fullmatch(value):
            raise _RowValueError(field.source_column, "invalid decimal")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise _RowValueError(field.source_column, "invalid decimal") from exc
        if not number.is_finite() or abs(number.adjusted()) > 1_000:
            raise _RowValueError(field.source_column, "decimal must be finite")
        lexical = format(number, "f")
        if lexical.startswith("."):
            lexical = "0" + lexical
        elif lexical.startswith("-."):
            lexical = lexical.replace("-.", "-0.", 1)
        if "." in lexical:
            lexical = lexical.rstrip("0").rstrip(".")
        if lexical in {"", "-0", "+0"}:
            lexical = "0"
        return {"@value": lexical, "@type": _XSD + "decimal"}
    if field.value_kind == "boolean":
        normalized = value.casefold()
        if normalized not in {"true", "false", "1", "0"}:
            raise _RowValueError(field.source_column, "boolean must be true, false, 1, or 0")
        return {
            "@value": "true" if normalized in {"true", "1"} else "false",
            "@type": _XSD + "boolean",
        }
    raise _RowValueError(field.source_column, "unsupported field value kind")


def _require_row_uri(value: str, field_name: str) -> None:
    try:
        _require_http_uri(value, field_name)
    except TransformationConfigurationError as exc:
        raise _RowValueError(field_name, "value must be an absolute HTTP(S) URI") from exc


def _convert_coordinate(
    x_value: str,
    y_value: str,
    mapping: CoordinateMapping,
    transformer: CoordinateTransformer,
) -> dict[str, object] | None:
    x_value = x_value.strip()
    y_value = y_value.strip()
    if not x_value and not y_value:
        return None
    if not x_value or not y_value:
        missing = mapping.x_column if not x_value else mapping.y_column
        raise _RowValueError(missing, "coordinate pair is incomplete")
    try:
        x = float(x_value)
        y = float(y_value)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("coordinates must be finite numbers")
        longitude, latitude = transformer.transform(
            x, y, mapping.source_crs, "EPSG:4326"
        )
    except (ValueError, CoordinateTransformError) as exc:
        raise _RowValueError(mapping.x_column, "invalid coordinate or CRS transformation") from exc
    geojson = json.dumps(
        {
            "type": "Point",
            "coordinates": [longitude, latitude],
        },
        allow_nan=False,
        separators=(",", ":"),
    )
    return {"@value": geojson, "@type": _GEOSPARQL_GEOJSON}
