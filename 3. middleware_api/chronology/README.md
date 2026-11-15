# Chronology middleware

This package provides the service-level components listed for
`middleware_api/chronology`: EDTF validation/normalization, temporal probability
curve validation, a safe OxCal adapter boundary, and High/Low chronology-set
display transforms. It uses only the Python standard library and is ready to be
mounted into the FastAPI application when that application root is added.

## EDTF profile

`parse_edtf()` supports the project guideline examples: signed four-or-more-digit
years, approximate (`~`), uncertain (`?`), approximate-and-uncertain (`%`),
year ranges, open-ended ranges, decades (`120X`), centuries (`12XX`), sets
(`{1200,1210}`), and valid positive-year month/day forms. It rejects malformed
or unsupported expressions rather than accepting free-text dates.

Normalized intervals use inclusive endpoints; `YearInterval.int4range_bounds`
converts them to PostgreSQL `[lower, upper)` bounds. Alternative-set bounds are
an envelope for indexing only; the original alternatives remain available.
The guideline gives a ±5–10 year convention for `~`, so the configurable
default is ±10. A `?` qualifier is preserved as an uncertainty flag without
inventing a probability curve or numeric error margin. Replace this bounded
profile with a standards-complete EDTF implementation before accepting forms
outside the supported subset.

## OxCal adapter

OxCal command-line interfaces differ by deployment. `OxCalRunner` therefore
invokes an administrator-configured adapter executable, not an assumed
universal OxCal CLI. It passes JSON on stdin, disables shell execution, enforces
a timeout, and validates the adapter's JSON output. The adapter output contract
is:

```json
{
  "software_name": "OxCal",
  "software_version": "deployment version",
  "distribution": {
    "p_start": -1250,
    "p_end": -1200,
    "probability_curve": [[-1250, 0.2], [-1200, 0.8]]
  },
  "result_uri": "s3://optional/model-or-output.json"
}
```

The caller supplies sample UUID, raw BP value, 1-sigma error, one of
`IntCal20`/`Marine20`/`SHCal20`, parameter-set UUID, notebook version, parameter
JSON, and a timezone-aware execution timestamp. Store results as new
`calibration_result` rows; never modify the original sample or a previous
calibration. The SQL module remains authoritative for database persistence and
append-only enforcement.

## Chronology sets

`display_assertion()` applies a set's integer year offset to a copy of the
distribution. It never mutates calibrated source values. Assertions retain
their independent certainty score; scores below `0.5` set the required
uncertainty indicator. The offset is a display transform only.

Run the unit tests from `3. middleware_api`:

```sh
python3 -m unittest discover -s chronology/tests -t . -v
```
