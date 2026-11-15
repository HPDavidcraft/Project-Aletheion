# Literature federation middleware

This package implements read-only SPARQL 1.1 search across the Pleroma
endpoint and the sibling Aletheion Literature Database. It submits both
queries concurrently, uses a shared SKOS concept-scheme URI as the join key,
merges identical RDF entity URIs with source attribution, and caches only
complete responses. If one endpoint fails, callers receive a partial result
with an explicit failure record; if both fail, the engine raises
`FederationUnavailable`.

The search query matches label/title literals and labels or notations of
concepts in the configured shared scheme. Search text is escaped as a SPARQL
literal, while result sizes, timeouts, response sizes, and target endpoint
hosts are bounded. Redirects are rejected. Endpoint URLs and authorization
tokens must come from trusted deployment configuration, never request data;
each endpoint also requires an exact hostname allowlist. HTTP is disabled
unless explicitly enabled for a trusted private development endpoint.

The endpoints have distinct query mappings and neither database is written
through this module. Search output is for public display only after each
endpoint's access and publication policy has been enforced by its SPARQL
service. This module does not claim that cross-endpoint results are complete
when an endpoint is unavailable.

`limit` and `offset` are applied independently at each endpoint before URI
deduplication, so the merged response may contain up to twice the requested
limit. This avoids claiming a globally ranked order across independently
modeled knowledge graphs.

The repository does not yet include a FastAPI application root or configured
SPARQL endpoints. Mount `UnifiedQueryEngine.search()` from the API once those
deployment settings exist. Run tests from `3. middleware_api`:

```sh
python3 -m unittest discover -s federation/tests -t . -v
```
