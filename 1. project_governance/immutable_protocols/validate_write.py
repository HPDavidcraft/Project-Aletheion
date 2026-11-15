#!/usr/bin/env python3
"""Validate a Pleroma write envelope against core immutable protocols."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID


_YEAR = r"-?\d{4}"
_YEAR_OR_PRECISION = rf"(?:{_YEAR}|-?\d{{3}}X|-?\d{{2}}XX)"
_DATE = re.compile(
    rf"^{_YEAR_OR_PRECISION}(?:-(?:0[1-9]|1[0-2]|21|22|23|24)"
    rf"(?:-(?:0[1-9]|[12]\d|3[01]|XX))?)?[?~%]?$"
)
_EDTF_YEAR = re.compile(rf"^{_YEAR}(?:-(\d{{2}})(?:-(\d{{2}}))?)?[?~%]?$")
_IIIF_PATH = re.compile(
    r"/iiif/(?:2|3)/.+/(?:info\.json|manifest(?:\.json|\.jsonld)?)$"
)
_PROPRIETARY_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx"}
_BIOLOGICAL_TYPES = {
    "bio_sample",
    "human_sample",
    "flora_specimen",
    "fauna_specimen",
}
_EVIDENCE_TYPES = {"find", "feature", "text_witness"}
_AUDIT_OPERATIONS = {"create", "update", "delete", "rollback"}


def _is_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _is_edtf(value: Any) -> bool:
    """Accept the EDTF forms used in the project guidelines, including ISO dates."""
    if not isinstance(value, str) or not value:
        return False

    if value.startswith("{") and value.endswith("}"):
        members = [member.strip() for member in value[1:-1].split(",")]
        return len(members) >= 2 and all(_is_edtf(member) for member in members)

    if "/" in value:
        if value.count("/") != 1:
            return False
        start, end = value.split("/", 1)
        return (start == ".." or _is_edtf(start)) and (
            end == ".." or _is_edtf(end)
        ) and bool(start or end)

    if not _DATE.fullmatch(value):
        return False

    match = _EDTF_YEAR.fullmatch(value)
    if not match:
        return True

    month, day = match.groups()
    if day is not None and month is not None and month.isdigit() and day.isdigit():
        month_number = int(month)
        day_number = int(day)
        year_text = re.match(r"-?\d{4}", value).group()
        year_number = int(year_text)
        days_in_month = (31, 29 if year_number % 4 == 0 and (
            year_number % 100 != 0 or year_number % 400 == 0
        ) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        return day_number <= days_in_month[month_number - 1]
    return True


def _walk(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield key, child, child_path
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _valid_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_envelope(envelope: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return ["$ must be a JSON object containing record and audit"]

    record = envelope.get("record")
    audit = envelope.get("audit")
    if not isinstance(record, dict):
        errors.append("$.record must be a JSON object")
    if not isinstance(audit, dict):
        errors.append("$.audit must be a JSON object")
    if errors:
        return errors

    record_type = record.get("record_type")
    if not isinstance(record_type, str) or not record_type.strip():
        errors.append("$.record.record_type is required")
        normalized_type = ""
    else:
        normalized_type = record_type.strip().lower()

    if not _is_uuid(audit.get("actor_uuid")):
        errors.append("$.audit.actor_uuid must be a UUID")
    operation = audit.get("operation_type")
    if not isinstance(operation, str) or operation.lower() not in _AUDIT_OPERATIONS:
        errors.append("$.audit.operation_type must be create, update, delete, or rollback")
    timestamp = audit.get("timestamp")
    if not isinstance(timestamp, str):
        errors.append("$.audit.timestamp must be an ISO 8601 timestamp with timezone")
    else:
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed_timestamp.tzinfo is None:
                errors.append("$.audit.timestamp must include a timezone")
        except ValueError:
            errors.append("$.audit.timestamp must be a valid ISO 8601 timestamp")
    if "previous_state" not in audit:
        errors.append("$.audit.previous_state is required (use null for a create)")
    if not isinstance(audit.get("justification"), str) or not audit["justification"].strip():
        errors.append("$.audit.justification is required")

    for key, value, path in _walk(record):
        normalized_key = key.lower()
        if (
            isinstance(value, str)
            and (normalized_key == "date" or normalized_key.endswith("_date")
                 or normalized_key in {"time_span", "active_dates", "valid_time_range"})
            and not _is_edtf(value)
        ):
            errors.append(f"{path} must contain a supported EDTF expression")
        if normalized_key in {"binary", "binary_data", "blob", "blob_data", "file_data"}:
            errors.append(f"{path} must be a storage URI or metadata, not embedded binary data")
        if normalized_key == "source_file_name" and isinstance(value, str):
            if Path(value).suffix.lower() in _PROPRIETARY_EXTENSIONS:
                errors.append(f"{path} uses a prohibited proprietary primary-data format")
        if normalized_key == "interpretive_label" and normalized_type != "interpretation_hypothesis":
            errors.append(f"{path} is an interpretation and must be modeled as Interpretation_Hypothesis")
        if normalized_key.endswith("_vocabulary_uri") or normalized_key.endswith("_skos_uri"):
            if not _valid_https_url(value):
                errors.append(f"{path} must be an absolute HTTPS vocabulary URI")

    if normalized_type == "stratigraphic_unit":
        if not _is_uuid(record.get("id")):
            errors.append("$.record.id must be a UUID for a Stratigraphic_Unit")
        geometry = record.get("geometry")
        if not isinstance(geometry, dict) or not geometry.get("type") or "coordinates" not in geometry:
            errors.append("$.record.geometry must be a GeoJSON geometry object")
        if record.get("harris_matrix_position") in (None, ""):
            errors.append("$.record.harris_matrix_position is required")
    if "stratigraphic_unit" in record and not _is_uuid(record.get("stratigraphic_unit")):
        errors.append("$.record.stratigraphic_unit must be a UUID reference, not free text")
    if "stratigraphic_unit_uuid" in record and not _is_uuid(record.get("stratigraphic_unit_uuid")):
        errors.append("$.record.stratigraphic_unit_uuid must be a UUID")

    if normalized_type == "media_asset":
        source_url = record.get("media_source_url")
        if not _valid_https_url(source_url) or not _IIIF_PATH.search(urlparse(source_url).path):
            errors.append("$.record.media_source_url must be an HTTPS Cantaloupe IIIF image or manifest URI")
        if not isinstance(record.get("checksum"), str) or not record["checksum"].strip():
            errors.append("$.record.checksum is required")

    if normalized_type == "interpretation_hypothesis":
        score = record.get("certainty_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            errors.append("$.record.certainty_score must be a number from 0 to 1")
        links = record.get("evidence_links")
        if not isinstance(links, list) or not links:
            errors.append("$.record.evidence_links must contain at least one anchored evidence link")
        else:
            for index, link in enumerate(links):
                link_path = f"$.record.evidence_links[{index}]"
                if not isinstance(link, dict):
                    errors.append(f"{link_path} must be an object")
                    continue
                entity_type = link.get("entity_type")
                if not isinstance(entity_type, str) or entity_type.lower() not in _EVIDENCE_TYPES:
                    errors.append(f"{link_path}.entity_type must be Find, Feature, or Text_Witness")
                if not _is_uuid(link.get("entity_uuid")):
                    errors.append(f"{link_path}.entity_uuid must be a UUID")

    if normalized_type in _BIOLOGICAL_TYPES:
        has_stratum = _is_uuid(record.get("stratigraphic_unit_uuid"))
        has_surface_context = isinstance(record.get("surface_collection_context"), str) and bool(
            record["surface_collection_context"].strip()
        )
        if not (has_stratum or has_surface_context):
            errors.append(
                "$.record must reference a Stratigraphic_Unit or provide surface_collection_context"
            )
        chain = record.get("chain_of_custody", record.get("provenance_chain"))
        if not isinstance(chain, list) or not chain:
            errors.append("$.record.chain_of_custody must contain at least one provenance link")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one Pleroma write envelope from a JSON file or stdin."
    )
    parser.add_argument("input", nargs="?", help="JSON file; reads stdin when omitted or '-'")
    args = parser.parse_args()

    try:
        if args.input and args.input != "-":
            with open(args.input, encoding="utf-8") as source:
                envelope = json.load(source)
        else:
            envelope = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 2

    errors = validate_envelope(envelope)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
