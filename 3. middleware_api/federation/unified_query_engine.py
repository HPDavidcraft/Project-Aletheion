"""Parallel, cached search across Pleroma and the Literature Database."""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from math import isfinite
from threading import RLock
from time import monotonic
from typing import Any

from .sparql import (
    EndpointConfig,
    SPARQLQueryError,
    SelectClient,
    build_concept_search_query,
)


@dataclass(frozen=True, slots=True)
class FederatedEntity:
    uri: str
    label: str
    matched_values: tuple[str, ...]
    entity_types: tuple[str, ...]
    source_endpoints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EndpointSearchResult:
    endpoint_name: str
    record_count: int


@dataclass(frozen=True, slots=True)
class EndpointFailure:
    endpoint_name: str
    message: str


@dataclass(frozen=True, slots=True)
class FederatedSearchResult:
    term: str
    entities: tuple[FederatedEntity, ...]
    endpoints: tuple[EndpointSearchResult, ...]
    failures: tuple[EndpointFailure, ...]
    complete: bool
    cache_hit: bool = False


class FederationUnavailable(RuntimeError):
    def __init__(self, failures: tuple[EndpointFailure, ...]) -> None:
        self.failures = failures
        names = ", ".join(failure.endpoint_name for failure in failures)
        super().__init__(f"All configured SPARQL endpoints failed: {names}")


class _TTLCache:
    def __init__(self, ttl_seconds: float, max_entries: int) -> None:
        if not isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise ValueError("cache TTL must be finite and positive")
        if max_entries <= 0:
            raise ValueError("cache max_entries must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[
            tuple[str, int, int], tuple[float, FederatedSearchResult]
        ] = OrderedDict()
        self._lock = RLock()

    def get(self, key: tuple[str, int, int]) -> FederatedSearchResult | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expiry, value = entry
            if expiry <= monotonic():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return replace(value, cache_hit=True)

    def put(self, key: tuple[str, int, int], value: FederatedSearchResult) -> None:
        with self._lock:
            self._entries[key] = (monotonic() + self._ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)


def _binding_value(
    binding: dict[str, Any], key: str, *, expected_type: str | None = None
) -> str | None:
    term = binding.get(key)
    if not isinstance(term, dict) or not isinstance(term.get("value"), str):
        return None
    if expected_type is not None and term.get("type") != expected_type:
        return None
    return term["value"]


def _normalize_bindings(
    endpoint_name: str, bindings: list[dict[str, Any]]
) -> list[FederatedEntity]:
    records: list[FederatedEntity] = []
    for binding in bindings:
        uri = _binding_value(binding, "entity", expected_type="uri")
        matched_value = _binding_value(binding, "matched_value", expected_type="literal")
        if uri is None or matched_value is None:
            raise SPARQLQueryError(
                f"{endpoint_name} returned a result without an entity URI or matched literal"
            )
        label = _binding_value(binding, "label", expected_type="literal")
        entity_type = _binding_value(binding, "entity_type", expected_type="uri")
        records.append(
            FederatedEntity(
                uri=uri,
                label=label or matched_value,
                matched_values=(matched_value,),
                entity_types=() if entity_type is None else (entity_type,),
                source_endpoints=(endpoint_name,),
            )
        )
    return records


def _merge_records(records: list[FederatedEntity]) -> tuple[FederatedEntity, ...]:
    merged: OrderedDict[str, FederatedEntity] = OrderedDict()
    for record in records:
        previous = merged.get(record.uri)
        if previous is None:
            merged[record.uri] = record
            continue
        merged[record.uri] = FederatedEntity(
            uri=record.uri,
            label=previous.label or record.label,
            matched_values=tuple(
                dict.fromkeys(previous.matched_values + record.matched_values)
            ),
            entity_types=tuple(
                dict.fromkeys(previous.entity_types + record.entity_types)
            ),
            source_endpoints=tuple(
                dict.fromkeys(previous.source_endpoints + record.source_endpoints)
            ),
        )
    return tuple(merged.values())


class UnifiedQueryEngine:
    """Route one safe search to both read-only federation endpoints."""

    def __init__(
        self,
        client: SelectClient,
        pleroma_endpoint: EndpointConfig,
        literature_endpoint: EndpointConfig,
        shared_scheme_uri: str,
        *,
        cache_ttl_seconds: float = 30.0,
        cache_max_entries: int = 256,
    ) -> None:
        if pleroma_endpoint.name == literature_endpoint.name:
            raise ValueError("Federated endpoint names must be distinct")
        self._client = client
        self._endpoints = (pleroma_endpoint, literature_endpoint)
        self._shared_scheme_uri = shared_scheme_uri
        self._cache = _TTLCache(cache_ttl_seconds, cache_max_entries)

    def search(
        self, term: str, *, limit: int = 20, offset: int = 0
    ) -> FederatedSearchResult:
        query = build_concept_search_query(
            term,
            self._shared_scheme_uri,
            limit=limit,
            offset=offset,
        )
        normalized_term = term.strip()
        cache_key = (normalized_term.casefold(), limit, offset)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        successes: list[EndpointSearchResult] = []
        failures: list[EndpointFailure] = []
        records: list[FederatedEntity] = []

        with ThreadPoolExecutor(max_workers=len(self._endpoints)) as executor:
            pending = {
                executor.submit(self._client.select, endpoint, query): endpoint
                for endpoint in self._endpoints
            }
            for future in as_completed(pending):
                endpoint = pending[future]
                try:
                    bindings = future.result()
                    endpoint_records = _normalize_bindings(endpoint.name, bindings)
                except SPARQLQueryError as exc:
                    failures.append(EndpointFailure(endpoint.name, str(exc)))
                    continue
                records.extend(endpoint_records)
                successes.append(
                    EndpointSearchResult(endpoint.name, len(endpoint_records))
                )

        if not successes:
            raise FederationUnavailable(tuple(failures))

        result = FederatedSearchResult(
            term=normalized_term,
            entities=_merge_records(records),
            endpoints=tuple(
                next(item for item in successes if item.endpoint_name == endpoint.name)
                for endpoint in self._endpoints
                if any(item.endpoint_name == endpoint.name for item in successes)
            ),
            failures=tuple(
                next(item for item in failures if item.endpoint_name == endpoint.name)
                for endpoint in self._endpoints
                if any(item.endpoint_name == endpoint.name for item in failures)
            ),
            complete=not failures,
        )
        if result.complete:
            self._cache.put(cache_key, result)
        return result
