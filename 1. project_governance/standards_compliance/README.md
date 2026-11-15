# Standards compliance

`standards.json` records the standards, mandatory uses, implementation
contracts, and external Linked Open Data reconciliation targets specified by
the project guidelines. Compliance starts as `not_assessed`; the registry does
not claim that a standard has already been implemented or verified.

The standards inventory covers the CIDOC CRM family and FRBRoo; Getty AAT,
GBIF, Glottolog, and ATU/Thompson; EDTF; Zotero/DOI; OGC/ISO geospatial
standards; IIIF; RDF serializations; and SKOS.

Validate the registry and summarize current status:

```sh
python3 validate_standards.py
```

Require evidence-backed compliance for one entry:

```sh
python3 validate_standards.py --require-compliant edtf
```

When updating an entry, use `in_progress`, `compliant`, or `blocked` only when
appropriate. A `compliant` entry requires an `evidence` reference; a `blocked`
entry requires a `blocker` explanation. References should point to concrete
implementation artifacts, tests, or review records.

This registry validator checks its own structure and recorded evidence fields;
it does not inspect application schemas, ontology files, vocabulary contents,
or conformance to external standards. Record the exact external releases and
profiles adopted by implementations before asserting compliance.
