# Hard sciences schema

`001_hard_sciences.sql` creates shared biological-sample records and subtype
tables for human samples, flora specimens, and fauna specimens; laboratory
output pointers; genomic datasets; haplogroup assignments; and reproducible
dispersion-analysis records and links.

Apply the conservation/ethics migration first. Sample writes require an
existing provenance chain whose subject type, UUID, and collection context
match the sample. The chain must already have at least one custody entry in the
same transaction. Every sample also requires a Site UUID, scientific context,
significance, and either a Stratigraphic_Unit UUID or surface-collection
context, plus a primary laboratory-output URI and SHA-256 checksum. Specialized
sample types must have exactly one corresponding subtype record at transaction
commit. Add Site and Stratigraphic_Unit foreign keys when those schemas are
available.

Human-sample records carry NAGPRA review, descendant-community consultation,
and repatriation-request fields. These fields do not themselves authorize
access or public release; API/RBAC and the provenance legal-status gate must
enforce applicable restrictions.

Raw genomic, spectral, and other lab files remain in MinIO/S3. PostgreSQL stores
only pointers and SHA-256 checksums. Dispersion analyses record notebook URI,
revision, environment, parameters, inputs, regions, and Media_Asset UUIDs so
outputs can be reproduced and connected to samples and regional chronicles.
Flora and fauna identifications require GBIF taxon keys. Haplogroup assignments
store confidence intervals and can reference an IIIF tree Media_Asset.

Assumptions: PostgreSQL 13+ and `gen_random_uuid()` supplied by the PostgreSQL
version or `pgcrypto`. Cross-domain UUIDs for Site, stratigraphy,
Regional_Chronicle, and Media_Asset are not foreign keys yet. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_hard_sciences.sql
```
