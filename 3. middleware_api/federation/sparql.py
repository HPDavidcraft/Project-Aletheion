"""Validated SPARQL search construction and bounded HTTP SELECT transport."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)


class SPARQLQueryError(RuntimeError):
    """Raised for endpoint transport or SPARQL Results JSON errors."""


@dataclass(frozen=True, slots=True)
class EndpointConfig:
    name: str
    endpoint_url: str
    allowed_hosts: frozenset[str]
    timeout_seconds: float = 8.0
    max_response_bytes: int = 2_000_000
    authorization_token: str | None = None
    allow_http: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Endpoint name is required")
        if (
            not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("Endpoint timeout must be finite and positive")
        if self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")

        parsed = urlsplit(self.endpoint_url)
        allowed_schemes = {"https", "http"} if self.allow_http else {"https"}
        if (
            parsed.scheme not in allowed_schemes
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Endpoint URL must be a configured HTTP(S) URL")

        normalized_hosts = frozenset(host.lower().rstrip(".") for host in self.allowed_hosts)
        if not normalized_hosts or parsed.hostname.lower().rstrip(".") not in normalized_hosts:
            raise ValueError("Endpoint host is not in its administrator allowlist")
        object.__setattr__(self, "allowed_hosts", normalized_hosts)

        if self.authorization_token is not None and (
            not self.authorization_token
            or "\r" in self.authorization_token
            or "\n" in self.authorization_token
        ):
            raise ValueError("Authorization token must be a non-empty single-line value")


class SelectClient(Protocol):
    def select(
        self, endpoint: EndpointConfig, query: str
    ) -> list[dict[str, Any]]:
        """Return SPARQL result bindings for a SELECT query."""


def _validate_http_iri(value: str, label: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(char.isspace() or char in '<>"{}|\\^`' for char in value)
    ):
        raise ValueError(f"{label} must be an absolute HTTP(S) IRI")


def escape_sparql_string(value: str) -> str:
    """Escape a user literal for a SPARQL double-quoted string."""
    escaped: list[str] = []
    for char in value:
        codepoint = ord(char)
        if char == "\\":
            escaped.append("\\\\")
        elif char == '"':
            escaped.append('\\"')
        elif char == "\n":
            escaped.append("\\n")
        elif char == "\r":
            escaped.append("\\r")
        elif char == "\t":
            escaped.append("\\t")
        elif codepoint < 0x20 or codepoint == 0x7F:
            escaped.append(f"\\u{codepoint:04X}")
        else:
            escaped.append(char)
    return "".join(escaped)


def build_concept_search_query(
    term: str,
    shared_scheme_uri: str,
    *,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Build a bounded literal search plus a shared-SKOS-scheme lookup."""
    if not isinstance(term, str) or not term.strip():
        raise ValueError("Search term is required")
    if len(term) > 256 or any(ord(char) < 0x20 for char in term):
        raise ValueError("Search term must be at most 256 printable characters")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 5000:
        raise ValueError("offset must be an integer between 0 and 5000")
    _validate_http_iri(shared_scheme_uri, "shared_scheme_uri")

    literal = escape_sparql_string(term.strip())
    return f"""\
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?entity ?label ?matched_value ?entity_type
WHERE {{
  {{
    {{
      ?entity ?label_predicate ?matched_value .
      VALUES ?label_predicate {{
        rdfs:label skos:prefLabel skos:altLabel dcterms:title schema:name
      }}
    }}
    UNION
    {{
      ?entity ?concept_link ?concept .
      ?concept skos:inScheme <{shared_scheme_uri}> ;
               (skos:prefLabel|skos:altLabel|skos:notation) ?matched_value .
    }}
  }}
  FILTER(
    isLiteral(?matched_value) &&
    CONTAINS(LCASE(STR(?matched_value)), LCASE("{literal}"))
  )
  OPTIONAL {{ ?entity rdfs:label ?label . }}
  OPTIONAL {{ ?entity rdf:type ?entity_type . }}
}}
ORDER BY LCASE(STR(?matched_value)) STR(?entity)
LIMIT {limit}
OFFSET {offset}
"""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class SPARQLSelectClient:
    """HTTP SPARQL 1.1 SELECT client with endpoint allowlisting and size limits."""

    def select(
        self, endpoint: EndpointConfig, query: str
    ) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/sparql-results+json, application/json",
            "Content-Type": "application/sparql-query; charset=utf-8",
        }
        if endpoint.authorization_token is not None:
            headers["Authorization"] = f"Bearer {endpoint.authorization_token}"
        request = Request(
            endpoint.endpoint_url,
            data=query.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        opener = build_opener(_NoRedirectHandler)
        try:
            with opener.open(
                request,
                timeout=endpoint.timeout_seconds,
            ) as response:
                body = response.read(endpoint.max_response_bytes + 1)
                content_type = response.headers.get("Content-Type", "").lower()
        except HTTPError as exc:
            raise SPARQLQueryError(
                f"{endpoint.name} SPARQL endpoint returned HTTP {exc.code}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise SPARQLQueryError(
                f"Could not query {endpoint.name} SPARQL endpoint"
            ) from exc

        if len(body) > endpoint.max_response_bytes:
            raise SPARQLQueryError(
                f"{endpoint.name} SPARQL response exceeded the configured size limit"
            )
        if "json" not in content_type:
            raise SPARQLQueryError(
                f"{endpoint.name} endpoint did not return SPARQL Results JSON"
            )

        try:
            document = json.loads(body)
            bindings = document["results"]["bindings"]
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            UnicodeDecodeError,
        ) as exc:
            raise SPARQLQueryError(
                f"{endpoint.name} returned malformed SPARQL Results JSON"
            ) from exc
        if not isinstance(bindings, list) or any(
            not isinstance(binding, dict) for binding in bindings
        ):
            raise SPARQLQueryError(
                f"{endpoint.name} returned invalid SELECT bindings"
            )
        return bindings
