# Pleroma ontologies

`pleroma.ttl` is a project-owned ontology profile, not a local copy of CIDOC
CRM, its extensions, FRBRoo, or SKOS. It declares the Pleroma entity classes
and relationships, and expresses the explicit mappings identified in the
guidelines (including Site, Find, Stratigraphic Unit, sample, observation,
interpretation, and Text Witness). External ontology releases must be pinned
and the referenced class IRIs verified before production publication.

`vocabularies.ttl` defines Pleroma SKOS concept schemes and seeds only the
controlled values enumerated in the guidelines. Object type, material type,
event type, and feature type schemes intentionally do not invent domain terms;
populate them through vocabulary governance and map external terms using the
appropriate SKOS mapping properties.

The ontology profile supplies semantic structure but does not replace database
constraints or API validation. In particular, EDTF syntax, certainty ranges,
Harris Matrix acyclicity, legal-status export restrictions, and audit
immutability require application or database enforcement.

Parse all Turtle files with Raptor's `rapper`:

```sh
python3 validate_ontologies.py
```
