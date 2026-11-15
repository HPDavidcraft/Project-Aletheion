"""Directed trade-network metrics and portable graph artifacts using the stdlib."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping
from urllib.parse import urlsplit
from uuid import UUID
from xml.sax.saxutils import escape


_MAX_CSV_BYTES = 25_000_000
_MAX_CSV_ROWS = 200_000
_ROUTE_SOURCES = {"documented", "inferred", "LCP_computed"}
_SHA256 = re.compile(r"[A-Fa-f0-9]{64}\Z")
_EDGE_COLUMNS = {
    "vector_id",
    "origin_site_id",
    "destination_site_id",
    "movement_category_uri",
    "route_source",
}
_COMMUNITY_COLORS = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)


class TradeNetworkError(ValueError):
    """Raised when movement-vector inputs or network parameters are invalid."""


def _http_uri(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TradeNetworkError(f"{field} is required")
    uri = value.strip()
    try:
        parsed = urlsplit(uri)
        parsed.port
    except ValueError as exc:
        raise TradeNetworkError(f"{field} is malformed") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise TradeNetworkError(f"{field} must be an absolute HTTP(S) URI")
    return uri


@dataclass(frozen=True, slots=True)
class MovementVectorEdge:
    vector_id: UUID
    origin_site_id: UUID
    destination_site_id: UUID
    movement_category_uri: str
    route_source: str
    subtype_attributes: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        for field in ("vector_id", "origin_site_id", "destination_site_id"):
            if not isinstance(getattr(self, field), UUID):
                raise TradeNetworkError(f"{field} must be a UUID")
        object.__setattr__(
            self,
            "movement_category_uri",
            _http_uri(self.movement_category_uri, "movement_category_uri"),
        )
        if not isinstance(self.route_source, str) or self.route_source not in _ROUTE_SOURCES:
            raise TradeNetworkError(
                "route_source must be documented, inferred, or LCP_computed"
            )
        attributes = (
            {} if self.subtype_attributes is None else self.subtype_attributes
        )
        if not isinstance(attributes, Mapping):
            raise TradeNetworkError("subtype_attributes must be a JSON object")
        try:
            encoded = json.dumps(
                dict(attributes),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise TradeNetworkError(
                "subtype_attributes must contain finite JSON-compatible values"
            ) from exc
        object.__setattr__(
            self,
            "subtype_attributes",
            MappingProxyType(json.loads(encoded)),
        )


@dataclass(frozen=True, slots=True)
class SiteCentrality:
    site_id: UUID
    in_degree: int
    out_degree: int
    in_degree_centrality: float
    out_degree_centrality: float
    betweenness_centrality: float
    community_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "site_id": str(self.site_id),
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "in_degree_centrality": self.in_degree_centrality,
            "out_degree_centrality": self.out_degree_centrality,
            "betweenness_centrality": self.betweenness_centrality,
            "community_id": self.community_id,
        }


@dataclass(frozen=True, slots=True)
class TradeNetworkReport:
    cluster_history_id: UUID
    trade_category_uri: str
    analysis_scope: str
    site_ids: tuple[UUID, ...]
    edges: tuple[MovementVectorEdge, ...]
    centrality: tuple[SiteCentrality, ...]
    community_iterations: int
    community_iteration_limit: int

    def shortest_path(
        self, origin_site_id: UUID, destination_site_id: UUID
    ) -> tuple[UUID, ...] | None:
        """Return the unweighted directed shortest path, or None if unreachable."""
        site_set = set(self.site_ids)
        if origin_site_id not in site_set or destination_site_id not in site_set:
            raise TradeNetworkError("Shortest-path endpoints must belong to this cluster")
        adjacency = _adjacency(self.site_ids, self.edges)
        queue = deque([origin_site_id])
        predecessor: dict[UUID, UUID | None] = {origin_site_id: None}
        while queue:
            current = queue.popleft()
            if current == destination_site_id:
                path: list[UUID] = []
                cursor: UUID | None = current
                while cursor is not None:
                    path.append(cursor)
                    cursor = predecessor[cursor]
                return tuple(reversed(path))
            for neighbor in sorted(adjacency[current], key=str):
                if neighbor not in predecessor:
                    predecessor[neighbor] = current
                    queue.append(neighbor)
        return None

    def node_link_data(self) -> dict[str, object]:
        """Emit directed multigraph node-link JSON that can be loaded by NetworkX."""
        communities = {row.site_id: row.community_id for row in self.centrality}
        return {
            "directed": True,
            "multigraph": True,
            "graph": {
                "cluster_history_id": str(self.cluster_history_id),
                "movement_category_uri": self.trade_category_uri,
                "analysis_scope": self.analysis_scope,
                "community_algorithm": "deterministic_undirected_label_propagation",
                "community_iterations": self.community_iterations,
                "community_iteration_limit": self.community_iteration_limit,
            },
            "nodes": [
                {"id": str(site_id), "community_id": communities[site_id]}
                for site_id in self.site_ids
            ],
            "links": [
                {
                    "source": str(edge.origin_site_id),
                    "target": str(edge.destination_site_id),
                    "key": str(edge.vector_id),
                    "movement_vector_id": str(edge.vector_id),
                    "movement_category_uri": edge.movement_category_uri,
                    "route_source": edge.route_source,
                    "subtype_attributes": dict(edge.subtype_attributes or {}),
                }
                for edge in self.edges
            ],
        }

    def writeback_payload(
        self,
        *,
        site_membership_sha256: str,
        movement_vectors_sha256: str,
        parameter_set_id: UUID,
        notebook_revision: str,
        environment_reference: str,
        executed_at: datetime,
    ) -> dict[str, object]:
        """Return structured analysis data; persistence remains with the API."""
        for field, checksum in (
            ("site_membership_sha256", site_membership_sha256),
            ("movement_vectors_sha256", movement_vectors_sha256),
        ):
            if not isinstance(checksum, str) or not _SHA256.fullmatch(checksum):
                raise TradeNetworkError(f"{field} must be a SHA-256 digest")
        if not isinstance(parameter_set_id, UUID):
            raise TradeNetworkError("parameter_set_id must be a UUID")
        if (
            not isinstance(executed_at, datetime)
            or executed_at.tzinfo is None
            or executed_at.utcoffset() is None
        ):
            raise TradeNetworkError("executed_at must be timezone-aware")
        if not isinstance(notebook_revision, str) or not notebook_revision.strip():
            raise TradeNetworkError("notebook_revision is required")
        if not isinstance(environment_reference, str) or not environment_reference.strip():
            raise TradeNetworkError("environment_reference is required")
        return {
            "cluster_history_id": str(self.cluster_history_id),
            "interaction_type": "trade",
            "movement_category_uri": self.trade_category_uri,
            "analysis_scope": self.analysis_scope,
            "input_sha256": {
                "site_membership": site_membership_sha256.lower(),
                "movement_vectors": movement_vectors_sha256.lower(),
            },
            "parameter_set_id": str(parameter_set_id),
            "notebook_revision": notebook_revision.strip(),
            "environment_reference": environment_reference.strip(),
            "executed_at": executed_at.isoformat(),
            "site_ids": [str(site_id) for site_id in self.site_ids],
            "movement_vector_ids": [str(edge.vector_id) for edge in self.edges],
            "centrality": [row.to_dict() for row in self.centrality],
            "community_algorithm": "deterministic_undirected_label_propagation",
            "community_iterations": self.community_iterations,
            "community_iteration_limit": self.community_iteration_limit,
            "graph": self.node_link_data(),
        }

    def write_outputs(self, output_directory: str | Path) -> dict[str, Path]:
        """Write graph JSON, metric CSVs, and an SVG schematic without overwriting."""
        directory = Path(output_directory)
        if not directory.is_dir():
            raise TradeNetworkError("Output directory must already exist")
        paths = {
            "graph": directory / "trade_network.json",
            "centrality": directory / "site_centrality.csv",
            "communities": directory / "site_communities.csv",
            "visualization": directory / "trade_network.svg",
        }
        if any(path.exists() for path in paths.values()):
            raise TradeNetworkError("Refusing to overwrite existing network outputs")
        graph_payload = self.node_link_data()
        paths["graph"].write_text(
            json.dumps(graph_payload, ensure_ascii=False, allow_nan=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        _write_dict_csv(paths["centrality"], [row.to_dict() for row in self.centrality])
        _write_dict_csv(
            paths["communities"],
            [
                {"site_id": str(row.site_id), "community_id": row.community_id}
                for row in self.centrality
            ],
        )
        paths["visualization"].write_text(
            _render_svg(self),
            encoding="utf-8",
        )
        return paths


def analyze_trade_network(
    *,
    cluster_history_id: UUID,
    interaction_type: str,
    analysis_scope: str,
    participating_site_ids: Iterable[UUID],
    movement_vectors: Iterable[MovementVectorEdge],
    trade_category_uri: str,
    max_community_iterations: int = 100,
) -> TradeNetworkReport:
    """Analyze directed site links; community detection uses an undirected projection."""
    if not isinstance(cluster_history_id, UUID):
        raise TradeNetworkError("cluster_history_id must be a UUID")
    if interaction_type != "trade":
        raise TradeNetworkError("Trade analysis requires a trade Cluster_History")
    if not isinstance(analysis_scope, str) or not analysis_scope.strip():
        raise TradeNetworkError(
            "analysis_scope must document the temporal/spatial selection criteria"
        )
    category_uri = _http_uri(trade_category_uri, "trade_category_uri")
    if (
        isinstance(max_community_iterations, bool)
        or not isinstance(max_community_iterations, int)
        or max_community_iterations <= 0
    ):
        raise TradeNetworkError("max_community_iterations must be a positive integer")
    sites = tuple(participating_site_ids)
    if not sites or any(not isinstance(site_id, UUID) for site_id in sites):
        raise TradeNetworkError("At least one participating Site UUID is required")
    if len(set(sites)) != len(sites):
        raise TradeNetworkError("Participating Site UUIDs must be unique")
    sites = tuple(sorted(sites, key=str))
    edges = tuple(movement_vectors)
    if any(not isinstance(edge, MovementVectorEdge) for edge in edges):
        raise TradeNetworkError("movement_vectors must contain MovementVectorEdge values")
    if len({edge.vector_id for edge in edges}) != len(edges):
        raise TradeNetworkError("Movement_Vector UUIDs must be unique")
    site_set = set(sites)
    for edge in edges:
        if edge.movement_category_uri != category_uri:
            raise TradeNetworkError("All input vectors must use the requested trade category")
        if (
            edge.origin_site_id not in site_set
            or edge.destination_site_id not in site_set
        ):
            raise TradeNetworkError(
                "Every movement-vector endpoint must be a participating Site"
            )

    adjacency = _adjacency(sites, edges)
    community_labels, iterations = _label_propagation(
        sites, adjacency, max_community_iterations
    )
    community_ids = _number_communities(sites, community_labels)
    metrics = _centrality_metrics(sites, edges, community_ids)
    return TradeNetworkReport(
        cluster_history_id=cluster_history_id,
        trade_category_uri=category_uri,
        analysis_scope=analysis_scope.strip(),
        site_ids=sites,
        edges=tuple(sorted(edges, key=lambda edge: str(edge.vector_id))),
        centrality=metrics,
        community_iterations=iterations,
        community_iteration_limit=max_community_iterations,
    )


def read_movement_vectors_csv(
    path: str | Path,
    *,
    max_file_bytes: int = _MAX_CSV_BYTES,
    max_rows: int = _MAX_CSV_ROWS,
) -> tuple[MovementVectorEdge, ...]:
    """Load selected Movement_Vector fields and JSON subtype attributes from CSV."""
    source_path = Path(path)
    if not source_path.is_file() or source_path.suffix.casefold() != ".csv":
        raise TradeNetworkError("Movement-vector input must be an existing CSV file")
    if (
        isinstance(max_file_bytes, bool)
        or not isinstance(max_file_bytes, int)
        or max_file_bytes <= 0
        or isinstance(max_rows, bool)
        or not isinstance(max_rows, int)
        or max_rows <= 0
    ):
        raise ValueError("CSV limits must be positive integers")
    if source_path.stat().st_size > max_file_bytes:
        raise TradeNetworkError("Movement-vector CSV exceeds the configured byte limit")
    try:
        with source_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            if (
                not reader.fieldnames
                or len(reader.fieldnames) != len(set(reader.fieldnames))
                or not _EDGE_COLUMNS.issubset(reader.fieldnames)
            ):
                raise TradeNetworkError(
                    "Movement-vector CSV lacks required headers or has duplicate headers"
                )
            result: list[MovementVectorEdge] = []
            for row_number, row in enumerate(reader, start=2):
                if row_number > max_rows + 1:
                    raise TradeNetworkError(
                        "Movement-vector CSV exceeds the configured row limit"
                    )
                if None in row or any(value is None for value in row.values()):
                    raise TradeNetworkError(
                        f"CSV row {row_number} has a different number of values than its header"
                    )
                attributes: Mapping[str, object] = {}
                if row.get("subtype_attributes", "").strip():
                    try:
                        parsed = json.loads(row["subtype_attributes"])
                    except json.JSONDecodeError as exc:
                        raise TradeNetworkError(
                            f"Invalid subtype_attributes JSON at CSV row {row_number}"
                        ) from exc
                    if not isinstance(parsed, dict):
                        raise TradeNetworkError(
                            f"subtype_attributes must be a JSON object at row {row_number}"
                        )
                    attributes = parsed
                try:
                    result.append(
                        MovementVectorEdge(
                            vector_id=UUID(row["vector_id"]),
                            origin_site_id=UUID(row["origin_site_id"]),
                            destination_site_id=UUID(row["destination_site_id"]),
                            movement_category_uri=row["movement_category_uri"],
                            route_source=row["route_source"],
                            subtype_attributes=attributes,
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise TradeNetworkError(
                        f"Invalid movement-vector value at CSV row {row_number}"
                    ) from exc
    except (OSError, csv.Error) as exc:
        raise TradeNetworkError(f"Could not read movement-vector CSV: {exc}") from exc
    return tuple(result)


def read_participating_sites_csv(
    path: str | Path,
    *,
    max_file_bytes: int = _MAX_CSV_BYTES,
    max_rows: int = _MAX_CSV_ROWS,
) -> tuple[UUID, ...]:
    """Read the normalized Cluster_History site-link export."""
    source_path = Path(path)
    if not source_path.is_file() or source_path.suffix.casefold() != ".csv":
        raise TradeNetworkError("Participating-site input must be an existing CSV file")
    if (
        isinstance(max_file_bytes, bool)
        or not isinstance(max_file_bytes, int)
        or max_file_bytes <= 0
        or isinstance(max_rows, bool)
        or not isinstance(max_rows, int)
        or max_rows <= 0
    ):
        raise ValueError("CSV limits must be positive integers")
    if source_path.stat().st_size > max_file_bytes:
        raise TradeNetworkError("Participating-site CSV exceeds the configured byte limit")
    try:
        with source_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            if not reader.fieldnames or reader.fieldnames != ["site_id"]:
                raise TradeNetworkError(
                    "Participating-site CSV must have exactly one 'site_id' column"
                )
            site_ids: list[UUID] = []
            for row_number, row in enumerate(reader, start=2):
                if row_number > max_rows + 1:
                    raise TradeNetworkError(
                        "Participating-site CSV exceeds the configured row limit"
                    )
                try:
                    if None in row or not row.get("site_id"):
                        raise ValueError("missing site_id")
                    site_ids.append(UUID(row["site_id"]))
                except (TypeError, ValueError) as exc:
                    raise TradeNetworkError(
                        f"Invalid Site UUID at CSV row {row_number}"
                    ) from exc
    except (OSError, csv.Error) as exc:
        raise TradeNetworkError(f"Could not read participating-site CSV: {exc}") from exc
    if not site_ids or len(set(site_ids)) != len(site_ids):
        raise TradeNetworkError(
            "Participating-site CSV must contain unique Site UUIDs"
        )
    return tuple(site_ids)


def _adjacency(
    site_ids: Iterable[UUID],
    edges: Iterable[MovementVectorEdge],
) -> dict[UUID, set[UUID]]:
    adjacency = {site_id: set() for site_id in site_ids}
    for edge in edges:
        if edge.origin_site_id != edge.destination_site_id:
            adjacency[edge.origin_site_id].add(edge.destination_site_id)
    return adjacency


def _label_propagation(
    site_ids: tuple[UUID, ...],
    directed_adjacency: Mapping[UUID, set[UUID]],
    max_iterations: int,
) -> tuple[dict[UUID, UUID], int]:
    nodes = tuple(sorted(site_ids, key=str))
    neighbors = {node: set(directed_adjacency[node]) for node in nodes}
    for source, targets in directed_adjacency.items():
        for target in targets:
            neighbors[target].add(source)
    labels = {node: node for node in nodes}
    seen_states = {tuple(labels[node] for node in nodes)}
    for iteration in range(1, max_iterations + 1):
        changed = False
        for node in nodes:
            if not neighbors[node]:
                continue
            counts = Counter(labels[neighbor] for neighbor in neighbors[node])
            most_common = max(counts.values())
            selected = min(
                (label for label, count in counts.items() if count == most_common),
                key=str,
            )
            if labels[node] != selected:
                labels[node] = selected
                changed = True
        if not changed:
            return labels, iteration
        state = tuple(labels[node] for node in nodes)
        if state in seen_states:
            raise TradeNetworkError(
                "Community label propagation entered a cycle; revise parameters or graph"
            )
        seen_states.add(state)
    raise TradeNetworkError(
        "Community label propagation did not converge within the configured iterations"
    )


def _number_communities(
    site_ids: tuple[UUID, ...],
    labels: Mapping[UUID, UUID],
) -> dict[UUID, int]:
    members: dict[UUID, list[UUID]] = defaultdict(list)
    for site_id in site_ids:
        members[labels[site_id]].append(site_id)
    ordered = sorted(members, key=lambda label: min(map(str, members[label])))
    community_ids = {label: index for index, label in enumerate(ordered, start=1)}
    return {site_id: community_ids[labels[site_id]] for site_id in site_ids}


def _centrality_metrics(
    site_ids: tuple[UUID, ...],
    edges: tuple[MovementVectorEdge, ...],
    community_ids: Mapping[UUID, int],
) -> tuple[SiteCentrality, ...]:
    outgoing = _adjacency(site_ids, edges)
    incoming = {site_id: set() for site_id in site_ids}
    for source, targets in outgoing.items():
        for target in targets:
            incoming[target].add(source)
    betweenness = _brandes_betweenness(site_ids, outgoing)
    denominator = len(site_ids) - 1
    betweenness_denominator = denominator * (len(site_ids) - 2)
    return tuple(
        SiteCentrality(
            site_id=site_id,
            in_degree=len(incoming[site_id]),
            out_degree=len(outgoing[site_id]),
            in_degree_centrality=(
                len(incoming[site_id]) / denominator if denominator > 0 else 0.0
            ),
            out_degree_centrality=(
                len(outgoing[site_id]) / denominator if denominator > 0 else 0.0
            ),
            betweenness_centrality=(
                betweenness[site_id] / betweenness_denominator
                if betweenness_denominator > 0
                else 0.0
            ),
            community_id=community_ids[site_id],
        )
        for site_id in site_ids
    )


def _brandes_betweenness(
    site_ids: tuple[UUID, ...],
    adjacency: Mapping[UUID, set[UUID]],
) -> dict[UUID, float]:
    centrality = {site_id: 0.0 for site_id in site_ids}
    for source in site_ids:
        stack: list[UUID] = []
        predecessors: dict[UUID, list[UUID]] = {node: [] for node in site_ids}
        paths = dict.fromkeys(site_ids, 0.0)
        paths[source] = 1.0
        distance = dict.fromkeys(site_ids, -1)
        distance[source] = 0
        queue = deque([source])
        while queue:
            node = queue.popleft()
            stack.append(node)
            for neighbor in sorted(adjacency[node], key=str):
                if distance[neighbor] < 0:
                    queue.append(neighbor)
                    distance[neighbor] = distance[node] + 1
                if distance[neighbor] == distance[node] + 1:
                    paths[neighbor] += paths[node]
                    predecessors[neighbor].append(node)
        dependency = dict.fromkeys(site_ids, 0.0)
        while stack:
            node = stack.pop()
            for predecessor in predecessors[node]:
                if paths[node]:
                    dependency[predecessor] += (
                        paths[predecessor] / paths[node]
                    ) * (1.0 + dependency[node])
            if node != source:
                centrality[node] += dependency[node]
    return centrality


def _write_dict_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _render_svg(report: TradeNetworkReport, width: int = 1200, height: int = 900) -> str:
    count = len(report.site_ids)
    center_x, center_y = width / 2, height / 2
    radius = min(width, height) * 0.36 if count > 1 else 0
    node_radius = max(15.0, min(27.0, 360.0 / max(count, 1)))
    positions = {
        site_id: (
            center_x + radius * math.cos(2 * math.pi * index / count - math.pi / 2),
            center_y + radius * math.sin(2 * math.pi * index / count - math.pi / 2),
        )
        for index, site_id in enumerate(report.site_ids)
    }
    community_by_site = {row.site_id: row.community_id for row in report.centrality}
    components = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Directed trade network schematic</title>",
        "<desc>Site links from movement vectors; circular placement is schematic and not geographic.</desc>",
        "<defs><marker id=\"arrow\" markerWidth=\"10\" markerHeight=\"8\" refX=\"8\" refY=\"4\" orient=\"auto\"><path d=\"M0,0 L0,8 L9,4 z\" fill=\"#555\"/></marker></defs>",
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    for edge in report.edges:
        x1, y1 = positions[edge.origin_site_id]
        x2, y2 = positions[edge.destination_site_id]
        if edge.origin_site_id == edge.destination_site_id:
            path = (
                f"M {x1:.2f} {y1 - node_radius:.2f} "
                f"C {x1 + 70:.2f} {y1 - 100:.2f}, {x1 - 70:.2f} {y1 - 100:.2f}, "
                f"{x1:.2f} {y1 - node_radius:.2f}"
            )
            components.append(
                f'<path d="{path}" fill="none" stroke="#555" marker-end="url(#arrow)"><title>{escape(edge.route_source)}</title></path>'
            )
            continue
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        start_x = x1 + dx * node_radius / length
        start_y = y1 + dy * node_radius / length
        end_x = x2 - dx * (node_radius + 7) / length
        end_y = y2 - dy * (node_radius + 7) / length
        components.append(
            f'<line x1="{start_x:.2f}" y1="{start_y:.2f}" x2="{end_x:.2f}" y2="{end_y:.2f}" '
            f'stroke="#555" stroke-width="1.5" marker-end="url(#arrow)"><title>'
            f'{escape(edge.route_source)}: {escape(str(edge.vector_id))}</title></line>'
        )
    for site_id in report.site_ids:
        x, y = positions[site_id]
        community = community_by_site[site_id]
        color = _COMMUNITY_COLORS[(community - 1) % len(_COMMUNITY_COLORS)]
        label = str(site_id)[:8]
        components.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{node_radius:.2f}" fill="{color}" stroke="#222"/>'
        )
        components.append(
            f'<text x="{x:.2f}" y="{y + node_radius + 16:.2f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{escape(label)}</text>'
        )
    components.append("</svg>")
    return "\n".join(components) + "\n"
