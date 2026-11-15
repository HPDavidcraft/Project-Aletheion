# Linguistic sphere schema

`001_linguistic_sphere.sql` defines Glottolog-aligned language families and
their parent-child hierarchy, plus time-bounded linguistic-zone polygons with
language, dialect, writing-system, script, and attestation-status metadata.

The family hierarchy is checked for cycles on insert/update. Linguistic zones
store canonical EDTF ranges alongside normalized astronomical-year bounds for
date-filtered spatial queries. Geometry is validated as a non-empty, valid WGS
84 polygon. Published families and zones require at least one bibliographic
reference by transaction commit.

Glottolog codes are format-checked but must still be verified against the
adopted Glottolog release. Writing-system URIs must point to approved SKOS
concepts. Script values use Unicode code-point/block notation (for example
`U+0000-U+007F`); EDTF and the consistency of normalized year bounds are
validated by the API.

Site containment at a selected date can be computed using the zone and site
spatial indexes plus the normalized year ranges. Media_Gallery and
Bibliographic_Reference UUIDs remain without foreign keys until the
universal-entities schema is installed.

Assumptions: PostgreSQL 13+, PostGIS 3.x, and `gen_random_uuid()` supplied by
the PostgreSQL version or `pgcrypto`. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_linguistic_sphere.sql
```
