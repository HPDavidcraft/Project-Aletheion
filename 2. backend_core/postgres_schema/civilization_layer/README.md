# Civilization layer schema

`001_civilization_layer.sql` creates the civilization container, territorial
polity phases, historical people, ordered ruler and capital-city relationships,
bibliographic links, and typed associations to events, expeditions, battles,
text witnesses, and finds.

All dates are stored in EDTF text fields and require API-level EDTF parsing and
temporal consistency validation. `polity_phase.territorial_extent` uses valid
WGS 84 PostGIS multipolygons. Role and relationship values are SKOS concept
URIs; verify vocabulary membership in the application.

Foreign keys to Site, Bibliographic_Reference, Historical_Event,
Movement_Vector, Battle, Text_Witness, and Find are deferred because those
schemas are not yet present. The link tables retain typed UUID references so
these constraints can be added when the referenced modules are implemented.

Assumptions: PostgreSQL 13+, PostGIS 3.x, and `gen_random_uuid()` supplied by
the PostgreSQL version or `pgcrypto`. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_civilization_layer.sql
```
