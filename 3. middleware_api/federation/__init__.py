"""SPARQL 1.1 federation between Pleroma and the Literature Database."""

from .sparql import EndpointConfig, SPARQLQueryError, SPARQLSelectClient
from .unified_query_engine import (
    FederatedEntity,
    FederatedSearchResult,
    FederationUnavailable,
    UnifiedQueryEngine,
)

__all__ = [
    "EndpointConfig",
    "FederatedEntity",
    "FederatedSearchResult",
    "FederationUnavailable",
    "SPARQLQueryError",
    "SPARQLSelectClient",
    "UnifiedQueryEngine",
]
