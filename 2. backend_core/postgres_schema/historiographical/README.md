# Historiographical schema

`001_historiographical.sql` implements the Chronicle Engine entities:
`regional_chronicle`, `cluster_history`, `site_history`, and
`historical_event`.

- Regional chronicles include a valid WGS 84 polygon, EDTF span, required
  survey/context narratives, normalized year bounds for temporal overlap
  queries, a Media_Gallery reference, contained-site links, and bibliographic
  links.
- Cluster histories use normalized participating-site links and an interaction
  type rather than storing Site UUID arrays; each has a Media_Gallery and graph
  assets are referenced by Media_Asset UUID. Publication requires sites, a
  network-graph asset, and a citation.
- Site histories are one-to-one with a Site UUID. Their version number
  increments on update; the governance audit log should retain each previous
  state and justification.
- Historical events distinguish discrete occurrences from Occupational
  Periods, require Description/Interpretation/Analysis before publication, and
  support spatial and temporal filtering. Every historiographical record has a
  Media_Gallery reference, and every published record must have a bibliographic
  reference by transaction commit.

Dates are stored as EDTF strings and require API-level parsing. Normalized
`int4range` year bounds use astronomical year numbers and must be kept consistent
with their EDTF values by the API. UUID references to Site, Media_Gallery,
Media_Asset, and Bibliographic_Reference remain without
foreign keys until those domain schemas are installed. Bibliographic links
carry the per-link citation type, page, and optional quotation.

Assumptions: PostgreSQL 13+, PostGIS 3.x, and `gen_random_uuid()` supplied by
the PostgreSQL version or `pgcrypto`. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_historiographical.sql
```
