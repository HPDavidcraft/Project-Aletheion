#!/usr/bin/env python3
"""Validate the structure and declared evidence in the Pleroma standards registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY = Path(__file__).with_name("standards.json")
VALID_STATUSES = {"not_assessed", "in_progress", "compliant", "blocked"}


def validate_registry(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["registry must be a JSON object"]

    errors: list[str] = []
    standards = data.get("standards")
    if not isinstance(standards, list) or not standards:
        return ["registry.standards must be a non-empty array"]

    ids: set[str] = set()
    for index, standard in enumerate(standards):
        path = f"standards[{index}]"
        if not isinstance(standard, dict):
            errors.append(f"{path} must be an object")
            continue

        standard_id = standard.get("id")
        if not isinstance(standard_id, str) or not standard_id:
            errors.append(f"{path}.id is required")
        elif standard_id in ids:
            errors.append(f"{path}.id duplicates {standard_id!r}")
        else:
            ids.add(standard_id)

        for field in ("name", "authority", "scope"):
            if not isinstance(standard.get(field), str) or not standard[field].strip():
                errors.append(f"{path}.{field} is required")

        for field in ("mandatory_usage", "implementation_contract"):
            values = standard.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{path}.{field} must be a non-empty array")
            elif any(not isinstance(value, str) or not value.strip() for value in values):
                errors.append(f"{path}.{field} must contain only non-empty strings")

        status = standard.get("status")
        if not isinstance(status, str) or status not in VALID_STATUSES:
            errors.append(f"{path}.status must be one of {sorted(VALID_STATUSES)}")
        elif status == "compliant":
            evidence = standard.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                errors.append(f"{path}.evidence is required when status is compliant")
        elif status == "blocked":
            blocker = standard.get("blocker")
            if not isinstance(blocker, str) or not blocker.strip():
                errors.append(f"{path}.blocker is required when status is blocked")

    reconciliations = data.get("linked_data_reconciliation")
    if not isinstance(reconciliations, list):
        errors.append("registry.linked_data_reconciliation must be an array")
    else:
        for index, entry in enumerate(reconciliations):
            path = f"linked_data_reconciliation[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{path} must be an object")
                continue
            for field in ("entity_type", "authority", "link_property", "method"):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    errors.append(f"{path}.{field} is required")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the Pleroma standards registry and its compliance evidence."
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="registry JSON path (defaults to standards.json beside this script)",
    )
    parser.add_argument(
        "--require-compliant",
        metavar="STANDARD_ID",
        help="return success only if this standard is marked compliant with evidence",
    )
    args = parser.parse_args()

    try:
        with args.registry.open(encoding="utf-8") as source:
            registry = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 2

    errors = validate_registry(registry)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 2

    if args.require_compliant:
        standard = next(
            (item for item in registry["standards"] if item["id"] == args.require_compliant),
            None,
        )
        if standard is None:
            print(
                json.dumps(
                    {"valid": False, "errors": [f"unknown standard: {args.require_compliant}"]},
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
        compliant = standard["status"] == "compliant" and bool(standard.get("evidence", "").strip())
        print(
            json.dumps(
                {
                    "standard": args.require_compliant,
                    "compliant": compliant,
                    "evidence": standard.get("evidence", ""),
                },
                indent=2,
            )
        )
        return 0 if compliant else 1

    counts = {status: 0 for status in sorted(VALID_STATUSES)}
    for standard in registry["standards"]:
        counts[standard["status"]] += 1
    print(json.dumps({"valid": True, "standard_count": len(registry["standards"]), "status_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
