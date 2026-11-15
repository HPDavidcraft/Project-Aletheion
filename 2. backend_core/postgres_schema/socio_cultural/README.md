# Socio-cultural schema

`001_socio_cultural.sql` creates `cultural_profile`, `societal_aspect`, typed
evidence links, and bibliography junctions. Evidence links use separate
foreign-key columns and a check constraint so each link points to exactly one
Find, Feature, or Bio_Sample.

Published profiles require a citation and at least one published aspect with
anchored evidence. Published aspects require both typed evidence and a
bibliographic citation. Deferred constraint triggers permit an entire
profile/aspect/evidence set to be created or updated within one transaction.
Controlled-vocabulary URI membership, EDTF parsing, and consistency between
EDTF values and normalized year bounds remain API responsibilities.

The `socio_cultural_evidence_context` view provides typed evidence identifiers,
site, spatial geometry, and temporal metadata when available. Trust Scores are
not modeled in this migration; the API must enrich reports through the Trust
Score service rather than inventing a value. Restrict this view and all
Bio_Sample-linked reports according to provenance, human-sample ethics, and
publication policies.

Apply after the site-hierarchy and hard-sciences migrations. Requires
PostgreSQL 13+, PostGIS 3.x, and `gen_random_uuid()` supplied by the PostgreSQL
version or `pgcrypto`. Bibliographic references and media galleries remain
UUID references until the universal-entities schema provides those tables.

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_socio_cultural.sql
```
