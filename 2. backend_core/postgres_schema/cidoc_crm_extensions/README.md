# CIDOC CRM extension mapping registry

`001_crm_mapping_registry.sql` creates a project registry for external ontology
releases, CRM classes and properties, and Pleroma-to-CRM mappings. It does not
recreate or redistribute CIDOC CRM, CRMarchaeo, CRMsci, CRMgeo, CRMinf, or
FRBRoo definitions.

The migration seeds the CRM suite and the Pleroma class mappings explicitly
named or illustrated in the project guidelines. Seeded terms and mappings
remain `unverified`/`proposed`; they do not count as production conformance.
Before marking a mapping verified, pin the exact upstream release, validate the
class/property URI against that release, and record reviewer UUID and review
timestamp. The CRMba/CRMarchaeo naming and namespace must also be resolved
during that review.

Property mappings can be added after the project property model and exact CRM
property mappings are reviewed. The generic registry intentionally does not
invent property correspondences where the guidelines do not specify them.

The mapping tables use project class/property URIs and do not impose foreign
keys on domain tables that have not yet been created. Application validation
must still enforce mapping use in RDF exports and schema implementation.

Assumptions: PostgreSQL 13+ and `gen_random_uuid()` supplied by the PostgreSQL
version or `pgcrypto`. Apply with:

```sh
psql -v ON_ERROR_STOP=1 -d <database> -f 001_crm_mapping_registry.sql
```
