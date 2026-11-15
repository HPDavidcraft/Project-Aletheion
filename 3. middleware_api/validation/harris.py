"""Harris Matrix acyclicity and same-site relationship validation."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Mapping, Sequence
from uuid import UUID

from .common import ValidationIssue, ValidationReport


EntityId = str | UUID
RELATIONSHIP_TYPES = frozenset({"above", "below", "contemporary"})


@dataclass(frozen=True, slots=True)
class StratigraphicRelationship:
    unit_id: EntityId
    related_unit_id: EntityId
    relationship_type: str


@dataclass(frozen=True, slots=True)
class HarrisMatrixResult:
    report: ValidationReport
    topological_order: tuple[str, ...]


class HarrisMatrixValidator:
    """Validate relationship references and return a deterministic DAG order."""

    def validate(
        self,
        unit_site_ids: Mapping[EntityId, EntityId],
        relationships: Sequence[StratigraphicRelationship],
    ) -> HarrisMatrixResult:
        issues: list[ValidationIssue] = []
        sites: dict[str, str] = {}
        for raw_unit_id, raw_site_id in unit_site_ids.items():
            unit_id = _normalize_identifier(raw_unit_id)
            site_id = _normalize_identifier(raw_site_id)
            if unit_id is None or site_id is None:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.invalid_identifier",
                        "Unit and site identifiers must be non-empty strings or UUIDs",
                    )
                )
                continue
            if unit_id in sites:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.duplicate_unit",
                        "Stratigraphic unit identifier is duplicated",
                        (unit_id,),
                    )
                )
                continue
            sites[unit_id] = site_id
        graph: dict[str, set[str]] = {unit_id: set() for unit_id in sites}
        indegree = {unit_id: 0 for unit_id in sites}
        seen_relationships: set[tuple[str, str, str]] = set()

        for relationship in relationships:
            unit_id = _normalize_identifier(relationship.unit_id)
            related_id = _normalize_identifier(relationship.related_unit_id)
            kind = relationship.relationship_type
            if unit_id is None or related_id is None:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.invalid_identifier",
                        "Relationship identifiers must be non-empty strings or UUIDs",
                    )
                )
                continue
            if not isinstance(kind, str) or kind not in RELATIONSHIP_TYPES:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.relationship_type",
                        f"Unsupported stratigraphic relationship type: {kind}",
                        (unit_id, related_id),
                    )
                )
                continue
            edge_key = (unit_id, related_id, kind)
            if edge_key in seen_relationships:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.duplicate_relationship",
                        "Stratigraphic relationship is duplicated",
                        (unit_id, related_id),
                    )
                )
                continue
            seen_relationships.add(edge_key)
            if unit_id == related_id:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.self_relationship",
                        "A stratigraphic unit cannot relate to itself",
                        (unit_id,),
                    )
                )
                continue
            if unit_id not in sites or related_id not in sites:
                missing = tuple(
                    identifier
                    for identifier in (unit_id, related_id)
                    if identifier not in sites
                )
                issues.append(
                    ValidationIssue(
                        "stratigraphy.unknown_unit",
                        "Relationship refers to an unknown stratigraphic unit",
                        missing,
                    )
                )
                continue
            if sites[unit_id] != sites[related_id]:
                issues.append(
                    ValidationIssue(
                        "stratigraphy.cross_site_relationship",
                        "Stratigraphic relationships must connect units from the same site",
                        (unit_id, related_id),
                    )
                )
                continue
            if kind == "contemporary":
                if unit_id >= related_id:
                    issues.append(
                        ValidationIssue(
                            "stratigraphy.noncanonical_contemporary_pair",
                            "Contemporary pairs must be stored once in canonical identifier order",
                            (unit_id, related_id),
                        )
                    )
                continue

            lower_id, upper_id = (
                (related_id, unit_id) if kind == "above" else (unit_id, related_id)
            )
            if upper_id not in graph[lower_id]:
                graph[lower_id].add(upper_id)
                indegree[upper_id] += 1

        ready = [unit_id for unit_id, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        order: list[str] = []
        while ready:
            current = heapq.heappop(ready)
            order.append(current)
            for neighbor in sorted(graph[current]):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    heapq.heappush(ready, neighbor)

        if len(order) != len(graph):
            cycle = _find_cycle(graph)
            issues.append(
                ValidationIssue(
                    "stratigraphy.cycle",
                    "Stratigraphic relationships create a Harris Matrix cycle: "
                    + " -> ".join(cycle),
                    cycle,
                )
            )
        return HarrisMatrixResult(
            report=ValidationReport(tuple(issues)),
            topological_order=tuple(order),
        )


def _normalize_identifier(value: object) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str) and value and value == value.strip():
        return value
    return None


def _find_cycle(graph: Mapping[str, set[str]]) -> tuple[str, ...]:
    state: dict[str, int] = {}
    stack: list[str] = []
    positions: dict[str, int] = {}
    for unit_id in sorted(graph):
        if state.get(unit_id, 0) != 0:
            continue
        state[unit_id] = 1
        positions[unit_id] = len(stack)
        stack.append(unit_id)
        pending = [(unit_id, iter(sorted(graph[unit_id])))]
        while pending:
            current, neighbors = pending[-1]
            neighbor = next(neighbors, None)
            if neighbor is None:
                pending.pop()
                stack.pop()
                positions.pop(current)
                state[current] = 2
                continue
            if state.get(neighbor, 0) == 0:
                state[neighbor] = 1
                positions[neighbor] = len(stack)
                stack.append(neighbor)
                pending.append((neighbor, iter(sorted(graph[neighbor]))))
            elif state[neighbor] == 1:
                return tuple(stack[positions[neighbor] :] + [neighbor])
    return ()
