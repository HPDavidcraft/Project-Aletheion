# Intangible heritage schema

`001_intangible_heritage.sql` defines liturgical events, oral-tradition nodes
and their directed transmission links, and multimodal sensory profiles.

- Liturgical events accept an EDTF date or an RFC 5545 `RRULE` recurrence
  string, with optional links to a temporal geographic alignment and temple
  Feature.
- Oral traditions record mnemonic structure, performance context, optional
  performer-role vocabulary URI, and directed transmission edges. Cycles are
  permitted because transmission can include revival and reciprocal influence.
- Sensory profiles associate with a Site, Occupational_Period, or Feature;
  include RT60, acoustic simulation parameters, lighting conditions, ordered
  material/color associations, and audio Media_Asset references.
- Published records require a bibliographic reference. A published sensory
  profile must also have at least one populated sensory modality.

Impulse-response and audio files are stored in MinIO/S3 or another configured
object store. Only URIs and Media_Asset UUIDs are stored in PostgreSQL. Dates
and recurrence rules require application-level standards validation. UUID
references to Geo_Feature_Temporal, Feature, Site, Occupational_Period,
Media_Gallery, Media_Asset, and Bibliographic_Reference are not foreign keys
until those domain schemas are installed.

Assumptions: PostgreSQL 13+ and `gen_random_uuid()` supplied by the PostgreSQL
version or `pgcrypto`. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_intangible_heritage.sql
```
