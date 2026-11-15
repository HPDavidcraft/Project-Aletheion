import json
import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError

from federation.sparql import (
    EndpointConfig,
    SPARQLQueryError,
    SPARQLSelectClient,
    build_concept_search_query,
    escape_sparql_string,
)
from federation.unified_query_engine import (
    FederationUnavailable,
    UnifiedQueryEngine,
)


SCHEME = "https://example.org/vocab/motifs"


def endpoint(name, host):
    return EndpointConfig(
        name=name,
        endpoint_url=f"https://{host}/sparql",
        allowed_hosts=frozenset({host}),
    )


def binding(uri, label, matched, entity_type=None):
    result = {
        "entity": {"type": "uri", "value": uri},
        "label": {"type": "literal", "value": label},
        "matched_value": {"type": "literal", "value": matched},
    }
    if entity_type:
        result["entity_type"] = {"type": "uri", "value": entity_type}
    return result


class SparqlQueryTests(unittest.TestCase):
    def test_literal_is_escaped_and_shared_scheme_is_used(self):
        term = 'lion") } UNION { ?s ?p ?o } #'
        query = build_concept_search_query(term, SCHEME, limit=5)
        self.assertIn(f"<{SCHEME}>", query)
        self.assertIn(escape_sparql_string(term), query)
        self.assertIn("LIMIT 5", query)
        self.assertIn("skos:notation", query)

    def test_query_parameters_and_endpoint_allowlist_are_validated(self):
        with self.assertRaises(ValueError):
            build_concept_search_query("lion", SCHEME, limit=101)
        with self.assertRaises(ValueError):
            EndpointConfig(
                name="remote",
                endpoint_url="https://untrusted.example/sparql",
                allowed_hosts=frozenset({"trusted.example"}),
            )
        with self.assertRaises(ValueError):
            EndpointConfig(
                name="remote",
                endpoint_url="http://localhost/sparql",
                allowed_hosts=frozenset({"localhost"}),
            )

    @patch("federation.sparql.build_opener")
    def test_sparql_client_posts_select_json_and_parses_bindings(self, build_opener):
        body = json.dumps({"results": {"bindings": [binding("https://x/1", "lion", "lion")]}})

        class Response:
            headers = {"Content-Type": "application/sparql-results+json"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self, _limit):
                return body.encode()

        class Opener:
            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return Response()

        opener = Opener()
        build_opener.return_value = opener
        bindings = SPARQLSelectClient().select(endpoint("Pleroma", "pleroma.example"), "SELECT * {}")
        self.assertEqual(len(bindings), 1)
        self.assertEqual(opener.request.get_method(), "POST")
        self.assertEqual(
            opener.request.get_header("Content-type"),
            "application/sparql-query; charset=utf-8",
        )
        self.assertEqual(opener.timeout, 8)

    @patch("federation.sparql.build_opener")
    def test_sparql_client_rejects_redirects(self, build_opener):
        headers = Message()
        headers["Location"] = "https://other.example/sparql"
        opener = build_opener.return_value
        opener.open.side_effect = HTTPError(
            "https://pleroma.example/sparql", 302, "Redirect", headers, None
        )
        with self.assertRaises(SPARQLQueryError):
            SPARQLSelectClient().select(
                endpoint("Pleroma", "pleroma.example"), "SELECT * {}"
            )


class UnifiedQueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.pleroma = endpoint("Pleroma", "pleroma.example")
        self.literature = endpoint("Literature Database", "lit.example")

    def test_merges_duplicate_uris_and_caches_complete_response(self):
        class Client:
            calls = 0

            def select(self, configured_endpoint, _query):
                self.calls += 1
                if configured_endpoint.name == "Pleroma":
                    return [binding("https://data.example/lion", "Lion", "lion", "urn:find")]
                return [binding("https://data.example/lion", "Lion", "Lion motif", "urn:motif")]

        client = Client()
        engine = UnifiedQueryEngine(client, self.pleroma, self.literature, SCHEME)
        first = engine.search("lion")
        second = engine.search("lion")
        self.assertTrue(first.complete)
        self.assertEqual(len(first.entities), 1)
        self.assertEqual(
            first.entities[0].source_endpoints,
            ("Pleroma", "Literature Database"),
        )
        self.assertTrue(second.cache_hit)
        self.assertEqual(client.calls, 2)

    def test_partial_failure_is_explicit_and_uncached(self):
        class Client:
            calls = 0

            def select(self, configured_endpoint, _query):
                self.calls += 1
                if configured_endpoint.name == "Pleroma":
                    return [binding("https://data.example/lion", "Lion", "lion")]
                raise SPARQLQueryError("Literature Database is unavailable")

        client = Client()
        engine = UnifiedQueryEngine(client, self.pleroma, self.literature, SCHEME)
        result = engine.search("lion")
        self.assertFalse(result.complete)
        self.assertEqual(len(result.failures), 1)
        engine.search("lion")
        self.assertEqual(client.calls, 4)

    def test_all_endpoint_failures_raise(self):
        class Client:
            def select(self, configured_endpoint, _query):
                raise SPARQLQueryError(f"{configured_endpoint.name} unavailable")

        engine = UnifiedQueryEngine(Client(), self.pleroma, self.literature, SCHEME)
        with self.assertRaises(FederationUnavailable) as error:
            engine.search("lion")
        self.assertEqual(len(error.exception.failures), 2)


if __name__ == "__main__":
    unittest.main()
