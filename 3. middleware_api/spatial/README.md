# Spatial middleware

This package provides reusable service components for the spatial middleware:

- Strict WGS 84 GeoJSON LineString validation.
- `GrassLCPRunner`, which calls a configured adapter for GRASS `r.cost` or
  `r.walk`, validates a least-cost path and cost-surface pointer, and emits a
  `Movement_Vector` writeback payload with route source `LCP_computed` and full
  run provenance.
- `PaleoclimateCatalog`, which resolves supported EDTF dates to configured
  CHELSA-TraCE21k or PMIP4 slices by temporal overlap. Open and uncertain ranges
  return all matching slices or fail explicitly when the configured slice cap
  is exceeded.
- `PaleoclimateService`, which extracts configured numeric climate metrics at
  WGS 84 points through an injected raster sampler and returns the selected
  layer, model, units, and time bounds with each reading.
- `GeoServerConfig`, which builds bounded WMS 1.3.0 GetMap URLs using CRS:84
  longitude/latitude axis order and each selected layer's configured time
  value.

GRASS GIS, GDAL, rasterio, and GeoServer are not installed in this repository
environment. `GrassLCPRunner` therefore delegates to a deployment-managed JSON
adapter rather than claiming to perform terrain analysis itself. Its adapter
accepts the validated request JSON on stdin and returns:

```json
{
  "path_geojson": {
    "type": "LineString",
    "coordinates": [[44.0, 32.0], [45.0, 33.0]]
  },
  "cost_surface_uri": "s3://analysis/cost-surface.tif",
  "total_cost": 12.5,
  "adapter_version": "1.0",
  "grass_version": "8.4"
}
```

The adapter must prepare the selected DEM and barrier inputs, run GRASS using
the requested energy model, and register the GeoTIFF externally. The runner
requires an administrator-provided allowlist for DEM and barrier hosts; it
enforces DEM resolution of 30 m or finer, valid WGS 84 endpoints, matching
path endpoints, model parameters, and reproducibility fields (notebook
version, parameter-set UUID, and execution timestamp). Cost surfaces must be
registered in S3/MinIO. Pandolf calculations require traveler weight and
carried load; energy coefficients and any other model inputs remain explicit
in the parameter JSON.

No sample climate layers are fabricated. Populate the catalog only with
verified GeoServer layer IDs, model/source metadata, slice bounds, units, and
WMS time values. Numeric climate extraction at site coordinates requires an
injected raster sampler for the actual deployed coverage; it is deliberately
not approximated from the display catalog. The caller must persist substantive
outputs through the API writeback path and apply existing entity publication
and provenance policies.

Run tests from `3. middleware_api`:

```sh
python3 -m unittest discover -s spatial/tests -t . -v
```
