# Source-critical schema

`001_source_critical.sql` creates:

- `text_witness` for manuscript or epigraphic witnesses, with EDTF dates,
  Glottolog language codes, JSON variant readings, flagged interpolations,
  and a Media_Gallery UUID.
- `text_witness_comparison` to track same-tradition comparisons and external
  IIIF annotation or HTML diff output. Diff generation is performed by the
  application; PostgreSQL stores only the result pointer and checksum.
- `interpretation_hypothesis` for scholarly interpretations, with a typed
  subject identifier, proponent, certainty score, conflict-resolution tag,
  supporting/opposing citations, and a directed counter-hypothesis graph.
- Typed hypothesis evidence links, constrained to exactly one Find, Feature,
  or Text_Witness. Published hypotheses require both anchored evidence and at
  least one supporting or opposing bibliographic citation.

The subject of a hypothesis can be any domain entity. Its class URI and UUID
are stored together, but existence and class-to-record matching are validated
by the API because the target may belong to any domain schema. Historical
Person proponents are foreign-key constrained; modern-scholar UUIDs remain
application-validated until an identity schema exists.

EDTF syntax, Glottolog release membership, controlled URI membership, JSON
payload structure, and IIIF authorization are API responsibilities. The debate
metrics view provides citation and counter-hypothesis counts only; a qualified
consensus indicator must be computed and labeled by the API rather than
misrepresented as a definitive database fact.

Apply after the site-hierarchy and civilization-layer migrations. Requires
PostgreSQL 13+ and `gen_random_uuid()` supplied by the PostgreSQL version or
`pgcrypto`. Bibliographic references and media galleries remain UUID references
until the universal-entities tables are available; this migration does not
depend on those tables.

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_source_critical.sql
```
