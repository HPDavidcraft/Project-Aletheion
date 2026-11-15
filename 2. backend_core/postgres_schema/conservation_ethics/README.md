# Conservation and ethics schema

`001_conservation_ethics.sql` defines conservation logs, ordered treatment and
inspection histories, a notification outbox, custody-chain headers and entries,
an export-eligibility function, and excavation-methodology templates.

Conservation inspections update the log's current condition. Transitions to
`active_corrosion` or `fragmenting` queue a `conservator` alert for an
application worker. The worker is responsible for delivery and retry handling.

Each provenance chain must be created with at least one custody entry in the
same transaction, retains an entry at every transaction commit, and cannot be
deleted. `provenance_allows_public_export`
returns true only if a chain exists and every entry has `legal_status = clear`.
It does not implement administrator overrides; those must be separately
authorized by the API. Human-sample chains require an ethics review flag and a
reference, and all biological-sample chains require a stratigraphic-unit UUID
or surface-collection context.

Dates are stored in EDTF text and must be parsed by the API. UUID references to
Find, biological samples, Stratigraphic_Unit, and excavation campaigns are not
foreign keys until those domain schemas are available. The project Directus
hook should provide authenticated actor UUIDs and append-only audit records for
all writes.

Assumptions: PostgreSQL 13+ and `gen_random_uuid()` supplied by the PostgreSQL
version or `pgcrypto`. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_conservation_ethics.sql
```
