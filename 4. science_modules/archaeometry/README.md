# Archaeometry

This package provides technique-aware validation and open-format spectrum
utilities for the `Material_Analysis_Event` workflow described in the project
guidelines:

- XRF, pXRF, SEM-EDS, and INAA result templates validate element symbols and
  finite mass percentages in the inclusive 0–100 range. Values are not
  normalized or forced to sum to 100; instrument-reported analytical totals
  must remain explicit.
- XRD results validate identified phases and optional reference-pattern and
  abundance fields.
- FTIR results validate analyst-supplied diagnostic bands. The package does
  not assign chemical interpretations to spectral peaks.
- `MaterialAnalysisEvent` creates a JSON-compatible writeback envelope with a
  Find UUID, technique, timezone-aware run time, analyst identity, required
  interpreted-report `Media_Asset` UUID, raw-object URI, SHA-256 checksum,
  validated result JSON, and processing provenance.
- `read_spectrum_csv` reads selected finite numeric columns from bounded UTF-8
  CSV files. Descending axes are reversed into strictly increasing order.
  `resample_linear` interpolates only within the source range and never
  extrapolates.

Raw instrument bytes are not retained in result JSON or PostgreSQL. Upload them
to S3/MinIO and provide the object pointer and checksum. Interpreted reports
must be registered as Media_Assets and attributed to an analyst. This package
does not parse proprietary instrument formats, select calibration methods, or
make material identifications; convert vendor exports to documented CSV and
record scientific methods/parameters explicitly.

The current repository has no `Material_Analysis_Event` table or API
writeback endpoint. `writeback_payload()` is a validated service contract; it
must be mapped to the approved persistence schema when that schema is
implemented. No live instrument, object store, or database integration is
configured here.

Run tests from `4. science_modules`:

```sh
python3 -m unittest discover -s archaeometry/tests -t . -v
```
