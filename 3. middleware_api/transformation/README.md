# Transformation middleware

This package provides a profile-driven importer for documented UTF-8 CSV
sources. `CSVToCIDOCTransformer` validates an entire file before returning
expanded JSON-LD; any invalid row rejects the batch, so callers cannot mistake
a partial conversion for a successful import. The result includes a SHA-256
checksum, row count, profile version, and pinned CRM release identifiers.

Each import profile maps source columns to Pleroma class/property URIs. The
injected `CRMMappingRegistry` must resolve those through the CRM mapping
registry (`pleroma_class_mapping`, `pleroma_property_mapping`, and the verified
standard/term records). Only verified class mappings with `subClassOf` or
`exactMatch` relations and verified property `exactMatch` relations are
accepted. The mapping registry currently seeds proposed class mappings and no
property mappings; pin and verify the upstream CRM release and review each
property correspondence before production imports. This package deliberately
does not guess CRM property mappings.

Profiles must explicitly map or mark every CSV column ignored, identify a
stable source identifier, define controlled-vocabulary crosswalks, and state
the source coordinate reference system. EDTF values are trimmed, validated
with the chronology middleware parser, and preserved as machine-readable
strings. Coordinate values become GeoJSON Points in WGS 84. The built-in
transformer supports identity, EPSG:4326/CRS:84, and EPSG:3857 transformations;
use `PyProjCoordinateTransformer` with the deployment's `pyproj` installation
for other CRSs. Axis order is always x/y, or longitude/latitude for geographic
CRSs.

Only CSV is accepted as a raw source format. Excel workbooks and other
proprietary formats must be converted to an open, documented format before
ingest. The importer does not modify source files, write to PostgreSQL, or
publish records. Persist the returned graph through the approved API/writeback
flow, retain the source checksum and provenance, and apply normal review,
evidence, and publication policies.

No concrete source-specific mapping profile is included because the repository
does not provide a reviewed legacy CSV layout or verified CRM property
mappings. Install a deployment implementation of `CRMMappingRegistry` that
reads the verified mapping tables; do not mark proposed mappings verified
solely to make an import pass.

Run tests from `3. middleware_api`:

```sh
python3 -m unittest discover -s transformation/tests -t . -v
```
