#!/usr/bin/env python3
"""Validate roadmap progress and report whether phase gates are satisfied."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROADMAP = Path(__file__).with_name("roadmap.json")
VALID_STATUSES = {"not_assessed", "in_progress", "blocked", "done"}


def validate_roadmap(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["roadmap must be a JSON object"]

    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        return ["roadmap.phases must be a non-empty array"]

    phase_ids: set[str] = set()
    item_ids: set[str] = set()
    for phase_index, phase in enumerate(phases):
        phase_path = f"phases[{phase_index}]"
        if not isinstance(phase, dict):
            errors.append(f"{phase_path} must be an object")
            continue
        phase_id = phase.get("id")
        if not isinstance(phase_id, str) or not phase_id:
            errors.append(f"{phase_path}.id is required")
        elif phase_id in phase_ids:
            errors.append(f"{phase_path}.id duplicates {phase_id!r}")
        else:
            phase_ids.add(phase_id)

        for collection_name in ("milestones", "exit_criteria"):
            collection = phase.get(collection_name)
            if not isinstance(collection, list):
                errors.append(f"{phase_path}.{collection_name} must be an array")
                continue
            for item_index, item in enumerate(collection):
                item_path = f"{phase_path}.{collection_name}[{item_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{item_path} must be an object")
                    continue
                item_id = item.get("id")
                if not isinstance(item_id, str) or not item_id:
                    errors.append(f"{item_path}.id is required")
                elif item_id in item_ids:
                    errors.append(f"{item_path}.id duplicates {item_id!r}")
                else:
                    item_ids.add(item_id)
                if not isinstance(item.get("description"), str) or not item["description"].strip():
                    errors.append(f"{item_path}.description is required")
                status = item.get("status")
                if not isinstance(status, str) or status not in VALID_STATUSES:
                    errors.append(f"{item_path}.status must be one of {sorted(VALID_STATUSES)}")
                elif status == "done":
                    if not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
                        errors.append(f"{item_path}.evidence is required when status is done")
                elif status == "blocked":
                    if not isinstance(item.get("blocker"), str) or not item["blocker"].strip():
                        errors.append(f"{item_path}.blocker is required when status is blocked")

    return errors


def phase_report(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reports = []
    prior_gates_complete = True
    for phase in phases:
        milestones = phase["milestones"]
        exit_criteria = phase["exit_criteria"]
        incomplete_milestones = [
            item["id"] for item in milestones if item.get("status") != "done"
        ]
        incomplete_exit_criteria = [
            item["id"] for item in exit_criteria if item.get("status") != "done"
        ]
        gate_complete = (
            not incomplete_milestones and not incomplete_exit_criteria
            if exit_criteria
            else None
        )
        reports.append(
            {
                "phase": phase["id"],
                "gate_complete": gate_complete,
                "eligible_to_start": prior_gates_complete,
                "incomplete_milestones": incomplete_milestones,
                "incomplete_exit_criteria": incomplete_exit_criteria,
            }
        )
        if gate_complete is not None:
            prior_gates_complete = prior_gates_complete and gate_complete
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the Pleroma roadmap manifest and phase completion evidence."
    )
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=DEFAULT_ROADMAP,
        help="roadmap JSON path (defaults to roadmap.json beside this script)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="validate manifest structure and progress evidence only",
    )
    parser.add_argument(
        "--gate",
        metavar="PHASE_ID",
        help="return success only when this phase and all earlier phase gates are complete",
    )
    args = parser.parse_args()

    try:
        with args.roadmap.open(encoding="utf-8") as source:
            data = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 2

    errors = validate_roadmap(data)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 2

    if args.validate:
        print(json.dumps({"valid": True}, indent=2))
        return 0

    reports = phase_report(data["phases"])
    if args.gate:
        for report in reports:
            if report["phase"] == args.gate:
                print(json.dumps(report, indent=2))
                return (
                    0
                    if report["gate_complete"] is True and report["eligible_to_start"]
                    else 1
                )
        print(
            json.dumps(
                {"valid": False, "errors": [f"unknown phase: {args.gate}"]},
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(reports, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
