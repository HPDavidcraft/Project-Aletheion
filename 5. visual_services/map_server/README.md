# GeoServer map services

This directory contains deployment-side GeoServer ImageMosaic configuration
for time-enabled GeoTIFFs and an SLD generator for dataset-defined raster
symbology. The PLEROMA guidelines call for WMS/WFS publication, paleoclimate
GeoTIFF time slices, and WCS access to the DEMs used by the GRASS LCP adapter.
The middleware's `spatial` package already resolves EDTF requests to configured
climate layers and builds bounded WMS 1.3.0 URLs; no layer IDs or model values
are invented here.

## Time-enabled paleoclimate mosaic

Copy `geoserver/imagemosaic/indexer.properties.example` to
`indexer.properties` and `timeregex.properties.example` to
`timeregex.properties` in a GeoServer ImageMosaic store directory. The template
indexes `time` from filenames matching `<prefix>_YYYY-MM-DD.tif`. Replace that
pattern, its date format, and the mosaic store path to match a verified
dataset. Each raster granule must have a valid georeferencing transform and
CRS; configure the resulting coverage's native/declared SRS correctly.

Publish the ImageMosaic as a coverage and enable its `time` dimension in the
GeoServer layer Dimensions settings. Confirm `TIME` appears in the published
WMS capabilities and that a request for a known configured instant selects
the expected granule. Keep CHELSA-TraCE21k and PMIP4 provenance, native units,
temporal semantics, and resolution in the deployment's climate catalog.
Historical and BCE/long-range dates need an explicit, tested mapping from the
source model's time axis to GeoServer's supported temporal values; do not
reinterpret archaeological EDTF values as Gregorian timestamps by default.

Expose DEM coverages through GeoServer WCS for the configured GRASS adapter.
WMS/WCS service enablement, data directories, layer publication, CORS, and
reverse-proxy authentication are GeoServer deployment settings and are not
configured by the templates alone. Do not expose private rasters or privileged
GeoServer REST endpoints publicly.

## Raster styles

`sld.py` builds SLD 1.0 raster color maps from the class codes or numeric
breakpoints supplied for a specific dataset. It intentionally has no built-in
Paleo-Köppen class values or climate ranges. A style definition is a JSON
object with `mode`, `name`, and `title`. For categorical styles, provide a
`classes` array of `{ "value": number, "label": "...", "color": "#RRGGBB" }`;
for continuous styles, provide `stops` with `{ "value": number, "color":
"#RRGGBB" }`.

```sh
python sld.py climate-style.json climate-style.sld
```

Upload the generated style through GeoServer's authenticated administration
interface or REST API, then explicitly assign it to the intended coverage.
These styles affect rendering only; they do not alter source raster values.

Run tests from this directory:

```sh
python -m unittest discover -s tests -v
```

## Integration boundary

The templates do not install GeoServer, upload rasters, publish workspaces or
layers, configure per-layer authorization, or contact a live WMS/WCS endpoint.
Actual catalog entries, layer identifiers, temporal mappings, styles, and
numeric climate sampling must be verified against the deployed data and
GeoServer capabilities before they are used by the application.
