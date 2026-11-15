# Universal entities schema

`001_universal_entities.sql` creates the shared media and bibliography records:

- `media_gallery` identifies one parent entity, stores caption, coverage, and
  rights-holder metadata, and moves from `draft` to `ready` only when it has at
  least one asset.
- `media_asset` stores object-storage pointers, checksums, type, rights,
  archival/lossless metadata, IIIF service and manifest URIs, and extracted
  EXIF/XMP metadata. Binary files remain in S3/MinIO. Image and RTI assets
  require Cantaloupe IIIF service and manifest pointers.
- `media_asset_annotation_version` stores IIIF AnnotationPage JSON as
  append-only, sequential versions; edits must create a new row.
- `bibliographic_reference` caches Zotero records keyed by mandatory Zotero
  UUID, with DOI availability and metadata. The sync/API must set DOI status
  accurately; a DOI marked available must be stored.
- `universal_entity_bibliography` provides a generic citation junction with
  per-link type, page, and quotation. Existing domain-specific bibliography
  junctions are retained.

The migration adds real foreign keys from existing `media_gallery_id`,
`bibliographic_reference_id`, and media-asset UUID columns. It also installs
parent-table triggers: each referenced gallery must be ready and must identify
the parent row's table name and UUID. Therefore, create a gallery and at least
one asset, mark the gallery ready, then create the parent record with that
gallery UUID. Vocabulary and Zotero synchronization validation remain
application responsibilities.

Apply after all current domain migrations so the cross-module foreign keys and
gallery-parent triggers can be installed. For a database that already contains
domain rows, backfill matching galleries, assets, and bibliographic records
before applying this migration; missing referenced rows intentionally cause
the foreign-key additions to fail. Requires PostgreSQL 13+, PostGIS 3.x, and
`gen_random_uuid()` supplied by the PostgreSQL version or `pgcrypto`.

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_universal_entities.sql
```
