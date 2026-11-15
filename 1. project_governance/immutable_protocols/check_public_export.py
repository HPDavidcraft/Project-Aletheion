#!/usr/bin/env python3
"""Fail closed when a public export contains non-clear provenance status."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


_RESTRICTED_STATUSES = {"contested", "repatriated", "stolen", "under_review"}


def find_restricted_statuses(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() == "legal_status":
                if not isinstance(child, str) or child.strip().lower() != "clear":
                    status = child if isinstance(child, str) else repr(child)
                    findings.append(f"{child_path} is not clear ({status})")
            findings.extend(find_restricted_statuses(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_restricted_statuses(child, f"{path}[{index}]"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check JSON data before public export; any non-clear legal status blocks export."
    )
    parser.add_argument("input", nargs="?", help="JSON file; reads stdin when omitted or '-'")
    args = parser.parse_args()

    try:
        if args.input and args.input != "-":
            with open(args.input, encoding="utf-8") as source:
                data = json.load(source)
        else:
            data = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"export_allowed": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 2

    errors = find_restricted_statuses(data)
    result = {"export_allowed": not errors, "errors": errors}
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
