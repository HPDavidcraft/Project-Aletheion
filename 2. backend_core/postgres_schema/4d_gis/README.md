# 4D-GIS schema

`001_4d_gis.sql` creates the temporal geographic-feature, resource-node, and
directed movement-vector tables using PostGIS geography in WGS 84. It adds
GiST indexes for spatial and temporal-range queries, stores SKOS concepts by
URI, and preserves EDTF text for application-layer validation.

The migration assumes PostgreSQL 13 or later and an installed PostGIS 3.x
extension. Apply it after the database role has permission to create PostGIS
objects. Cross-domain references remain UUIDs without foreign keys until the
site-hierarchy and evidence entity schemas are available.

Application/API validation is still required for full EDTF parsing, SKOS
registry membership, date-range interpretation, and subtype-specific movement
attributes. LCP-computed routes require their energy model, DEM source,
cost-surface URI, and parameter provenance. Raw rasters remain in object
storage, not PostgreSQL.
