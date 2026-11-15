# Theological schema

`001_theological.sql` creates `theological_system` and `religious_element`,
their many-to-many membership, typed evidence links, and bibliography tables.
Motifs retain both a scheme URI and concept URI for the ATU or Thompson
Motif-Index; actual scheme membership and release validation belong to the
application.

Evidence links are constrained to exactly one Find, Feature, or Text_Witness
using real foreign keys. A published Religious_Element requires anchored
evidence and a bibliographic citation. A published Theological_System
requires a citation and at least one linked Religious_Element. Deferred
constraint triggers allow a complete evidence-and-citation set to be written
in a single transaction.

`religious_element_evidence_context` supplies typed evidence identifiers and
available site, spatial, and temporal context for discovery and evidence
reports. SPARQL export and motif-based federation are application/graph-store
responsibilities. Trust scores are not fabricated here; the API may enrich
reports through the Trust Score service. Apply publication, provenance,
human-sample ethics, and media authorization policies before exposing results.

Apply after the site-hierarchy and source-critical migrations. Requires
PostgreSQL 13+, PostGIS 3.x, and `gen_random_uuid()` supplied by the PostgreSQL
version or `pgcrypto`. Bibliographic references and media galleries remain UUID
references until the universal-entities schema provides those tables.

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_theological.sql
```
