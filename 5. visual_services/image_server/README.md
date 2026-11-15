# Image server and IIIF preparation

This directory implements the image-side ingestion contract described in the
PLEROMA guidelines: source-file integrity checks, EXIF/XMP extraction,
pyramidal TIFF derivatives, IIIF Presentation API 3 manifests, and
append-only annotation payloads. Cantaloupe serves the IIIF Image API 3 image
services; it does not generate Presentation manifests.

## Local image pipeline

Requirements: Python 3, Pillow, and the `vips` command-line tool from libvips.
The source master is never modified. The pipeline accepts one-page JPEG, PNG,
or TIFF images, enforces a configurable pixel limit, extracts metadata, hashes
the source, applies EXIF orientation to a derivative, and writes a tiled,
LZW-compressed pyramidal TIFF while retaining only the ICC profile.

```sh
python build_pyramid.py master.jpg derivatives/asset-id.tif
```

The script prints source and derivative checksums, dimensions, and sizes. It
does not upload either file. Store the original master and the derivative in
private S3/MinIO object paths; configure Cantaloupe's `path_prefix` to resolve
the derivative key. `build_media_asset_payload()` records the checksum, size,
MIME type, and source URI of the original master, while its IIIF service URI
points to the derivative served by Cantaloupe. The service identifier should
not reveal a private bucket path.

`build_manifest()` emits a Presentation API 3 manifest with Canvas painting
annotations and Image API 3 services. A single manifest is restricted to one
rights URI; use separate manifests if a gallery contains assets with
different rights. `build_annotation_version_payload()` creates the JSON shape
for `media_asset_annotation_version`. Pass the next version number to the
database, which remains authoritative for sequencing and immutability; the
existing SQL trigger rejects stale or concurrent values.

Run tests from this directory:

```sh
python -m unittest discover -s tests -v
```

## Cantaloupe

`cantaloupe.properties.example` is a Cantaloupe 5.x starting configuration
for MinIO's S3-compatible API (Cantaloupe requires Java 21 or newer). Copy it
to the path used by the Cantaloupe process and provide `AWS_ACCESS_KEY_ID`
and `AWS_SECRET_ACCESS_KEY` through its runtime secret mechanism. The example
uses an internal MinIO endpoint, the
`pleroma-media` bucket, and the `iiif-pyramids/` object prefix. Cantaloupe
configuration can be overridden with environment variables using the
uppercase property name with non-alphanumeric characters replaced by
underscores (for example `S3SOURCE_REGION`).

Run the official Cantaloupe distribution with the configuration file, for
example:

```sh
java -Dcantaloupe.config=/etc/cantaloupe/cantaloupe.properties \
  -Xmx2g -jar cantaloupe-5.0.x.jar
```

The sample binds to loopback, disables the admin/API endpoints, and disables
browser-side caching. If binding to a container interface, keep the service on
a private network and put authentication, authorization, TLS, and rate limits
at a trusted reverse proxy. Cantaloupe itself is not configured here to enforce
per-asset PLEROMA permissions.

## Limits and integrations

- The module does not upload to MinIO/S3, write to PostgreSQL, publish the
  manifest at an API URL, or implement an annotation HTTP API.
- EXIF/XMP is extracted for internal metadata; it may contain sensitive
  location data and must not be copied into public manifests without review.
- Pyramidal derivatives are losslessly TIFF-encoded, but are not archival
  masters. The original source checksum and object URI are retained in the
  generated `media_asset` payload.
- Image validation is a decoder/structure check, not a forensic malware scan
  or a substitute for resource limits at the upload boundary.
- Integration should use the existing `media_asset` and
  `media_asset_annotation_version` contracts. The API must HEAD-check the
  public manifest URI and enforce gallery readiness and access policy.

References: [Cantaloupe 5.x manual](https://cantaloupe-project.github.io/manual/5.0/),
[IIIF Image API 3.0](https://iiif.io/api/image/3.0/), and
[IIIF Presentation API 3.0](https://iiif.io/api/presentation/3.0/).
