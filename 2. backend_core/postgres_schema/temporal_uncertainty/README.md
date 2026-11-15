# Temporal uncertainty schema

`001_temporal_uncertainty.sql` reuses the `temporal_distribution` composite and
`is_valid_temporal_distribution` validator defined by the chronometric module.
It adds:

- `temporal_uncertainty_case`, grouping alternate or revised EDTF assertions
  for a date-bearing property on any domain entity.
- `temporal_distribution_assertion`, versioned date assertions with canonical
  EDTF, normalized astronomical-year bounds, an optional probability curve,
  and a distinct certainty score. A revised assertion points to the version it
  supersedes; versions must be sequential within a case.
- `temporal_distribution_evidence`, typed references to chronometric samples,
  calibration results, text witnesses, or bibliographic references. Published
  assertions require at least one supporting source.
- `temporal_distribution_probability_points`, a flattened view for
  time-slider rendering that flags probabilities below `0.3` for reduced
  opacity.

The subject entity and its temporal-property URI are polymorphic because
assertions may concern records from any domain module. The API must verify that
the subject exists, EDTF is valid, normalized bounds agree with EDTF, and any
stored distribution agrees with both. A certainty score is not a probability
curve and must not be presented as one. The database does not calculate a
consensus date or silently select among competing assertions.

Apply after the chronometric and source-critical migrations. Requires
PostgreSQL 13+ and `gen_random_uuid()` supplied by the PostgreSQL version or
`pgcrypto`. The bibliographic-reference UUID remains unconstrained until the
universal-entities schema is available.

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_temporal_uncertainty.sql
```
