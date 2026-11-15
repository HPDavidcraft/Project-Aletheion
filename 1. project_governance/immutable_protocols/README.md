# Immutable protocols

These dependency-free Python command-line checks are starter guardrails for the
write and public-export paths described in the project guidelines.

## Validate a write

`validate_write.py` accepts one JSON envelope:

```json
{
  "record": {
    "record_type": "Interpretation_Hypothesis",
    "certainty_score": 0.7,
    "evidence_links": [
      {
        "entity_type": "Find",
        "entity_uuid": "550e8400-e29b-41d4-a716-446655440000"
      }
    ]
  },
  "audit": {
    "actor_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-11-14T01:00:00+04:00",
    "operation_type": "create",
    "previous_state": null,
    "justification": "Record submitted for scholarly review"
  }
}
```

Run `python3 validate_write.py write.json` or pipe JSON to
`python3 validate_write.py -`. Exit status is `0` for valid input, `1` for
protocol violations, and `2` for unreadable or malformed JSON.

The checks cover the audit envelope, guideline-listed EDTF examples and date
forms, modeled stratigraphic units, IIIF media pointers, interpretation evidence
and certainty, biological-sample context, and obvious prohibited raw-file or
embedded-binary fields. EDTF checking intentionally covers the forms documented
in the guidelines; it is not a complete implementation of every EDTF level.

## Check a public export

`check_public_export.py` accepts a JSON object or array. Any `Legal_Status`
other than `clear`, including a missing/non-string value when the field is
present, blocks the export:

```sh
python3 check_public_export.py export.json
```

These scripts are local preflight checks, not substitutes for server-side API
validation, PostgreSQL constraints, authentication/authorization, an approved
SKOS vocabulary registry, IIIF endpoint reachability checks, or append-only
database permissions for the audit table. In particular, immutability of
persisted audit rows must also be enforced by the database and application.
