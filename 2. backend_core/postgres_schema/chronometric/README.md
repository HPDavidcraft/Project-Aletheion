# Chronometric schema

`001_chronometric.sql` defines:

- The supported dating-method and calibration-curve lookup tables.
- `chronometric_sample`, which preserves uncalibrated BP measurements and
  1-sigma error values as immutable source data.
- The `temporal_distribution` composite type and append-only
  `calibration_result` records, so recalibration with a different curve,
  software version, or parameter set creates a new result instead of changing
  old output.
- Named `chronology_set` records and per-result `chronology_assertion` certainty
  scores. The set-level year offset is a display adjustment, not a rewrite of
  source values.

The probability curve is stored as ordered JSON pairs of `[year, probability]`
inside the composite type. A database function checks bounds, ordering, and
probability values in `[0, 1]`. Application validation remains responsible for
calibration-method semantics, EDTF date serialization, and full analytical
provenance.

Assumptions: PostgreSQL 13+; `pgcrypto` (or an equivalent provision of
`gen_random_uuid()`); astronomical year numbering for numeric probability-curve
years; and a unique lab code within each lab institution. Stratigraphic and
sample-entity UUIDs are not yet foreign keys because their domain schemas are
not present.

Apply with `psql -v ON_ERROR_STOP=1 -d <database> -f 001_chronometric.sql`.
