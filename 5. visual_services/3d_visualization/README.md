# 3D visualization assets

This module provides a structural inspector for self-contained glTF 2.0 binary
(`.glb`) files, a metadata payload for the shared `media_asset` table, and a
JSON viewer configuration contract for a future Three.js or A-Frame frontend.
The guidelines call for photogrammetry model storage in S3/MinIO and web/VR
model viewing; this module keeps binary model data outside PostgreSQL.

## Use

Run the inspector from this directory:

```sh
python inspect_glb.py path/to/model.glb
```

In Python, `inspect_glb(path)` returns the file size, SHA-256 digest, basic
scene counts, and extension declarations. Create a `ModelAsset3D` from that
inspection and supply the media-gallery UUID, private `s3://` or `minio://`
object URI, rights-statement URI, and creator UUID. Its `writeback_payload()`
matches the shared `media_asset` columns (`asset_type="3d_model"` and MIME type
`model/gltf-binary`); it does not perform a database write.

`build_viewer_config(...)` accepts an authorized HTTPS delivery URL only when
its exact hostname is on the caller-provided allowlist. It rejects query
strings (including expiring signatures), fragments, credentials, non-HTTPS
URLs, and nonstandard ports. The source object URI is not exposed to the
viewer. Autoplay is disabled and immersive mode requires user action. The
frontend must obtain delivery URLs from its authorized asset-delivery service
and apply its own access controls.

Run focused tests:

```sh
python -m unittest discover -s tests -v
```

## Limits

- Inspection checks GLB v2 container structure and selected resource
  constraints, but is not complete Khronos glTF schema/conformance validation.
- This module accepts self-contained GLB files: external buffer/image URLs are
  rejected. Large JSON chunks are bounded by default to 16 MB.
- It does not upload objects, issue signed URLs, integrate with MinIO/S3,
  authorize users, write to PostgreSQL, or implement a Three.js/A-Frame viewer.
- The project database requires each `media_asset` to belong to a gallery.
  Gallery readiness, parent-entity links, and application access policy remain
  governed by the shared database/API services.
