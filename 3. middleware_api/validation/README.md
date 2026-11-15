# Validation middleware

This package implements reusable server-side checks from the project quality
rules:

- `HarrisMatrixValidator` checks unit references, same-site membership,
  relationship types, canonical contemporary pairs, and acyclicity of the
  directed above/below graph. Successful results include a deterministic
  lower-to-upper topological order; cycle failures identify the cycle units.
- `validate_temporal_order` validates EDTF Start_Date/End_Date pairs against
  their full uncertainty bounds. `validate_stratigraphic_temporal_consistency`
  checks dated above/below and contemporary relationships.
- `validate_geojson_geometry` uses parameterized PostGIS
  `ST_IsValidDetail()` validation, checks the requested geometry type,
  non-empty/positive-area requirements, and WGS 84 coordinate bounds.
- `validate_publication_anchoring` prevents publication without at least one
  linked Bibliographic_Reference.
- `IIIFManifestValidator` performs the guideline-required HEAD check against a
  JSON manifest URI, with an exact hostname allowlist, HTTPS by default, a
  timeout, and redirect rejection.

These are API-layer components, not a mounted FastAPI application. The caller
must run them before persistence/publication and must fail the write whenever
the returned `ValidationReport` contains issues (`report.require_valid()`).
The database remains the final authority for foreign keys and schema
constraints. Temporal stratigraphic checks only assess relationships whose
units have dates; unknown or undated relations are not inferred.

Geometry validation needs a configured PostGIS connection. IIIF validation
makes a real network request only to configured manifest hosts. Unit tests
mock PostGIS and HTTP; no database or Cantaloupe service is configured here.

Run tests from `3. middleware_api`:

```sh
python3 -m unittest discover -s validation/tests -t . -v
```
