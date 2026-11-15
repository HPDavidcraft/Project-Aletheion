# Site hierarchy schema

`001_site_hierarchy.sql` creates the core archaeological entities:
`site`, `occupational_period`, `stratigraphic_unit`, `find`, and `feature`.
Each has its own identity, geometry, media-gallery reference, publication
state, and bibliographic links. The migration also provides the ordered
Harris-Matrix relationship table and a site-level entity-count view.

Site and period polygons use valid WGS 84 PostGIS geography. Finds use point
geometries; Features and strata use spatial geometries. Canonical dates remain
EDTF strings, with normalized astronomical-year ranges where temporal overlap
queries are needed. API validation must keep the EDTF values and year bounds
consistent.

Above/below stratigraphic relationships are checked as a directed acyclic graph
and must remain within one site; `contemporary` pairs are recorded once. A
transaction advisory lock serializes graph writes so concurrent updates cannot
introduce a cycle. Stratigraphic temporal consistency remains an API validation
responsibility.

Find records require an institution-unique inventory identifier, approved AAT
object type, material vocabulary URI, media gallery, and matching provenance
chain. Site/period/stratum context links are checked for same-site consistency.
Published records require at least one bibliographic citation. The migration
adds foreign keys to previously created modules whose UUID references now have
their target tables.

Apply after the foundational, conservation, hard-sciences, historiographical,
4D-GIS, civilization, and intangible-heritage migrations. Requires PostgreSQL
13+, PostGIS 3.x, and `gen_random_uuid()` supplied by the PostgreSQL version or
`pgcrypto`.

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_site_hierarchy.sql
```
