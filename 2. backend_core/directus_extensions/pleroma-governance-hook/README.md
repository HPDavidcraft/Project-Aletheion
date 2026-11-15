# Pleroma governance hook

This Directus API hook applies baseline write governance to custom Pleroma
collections:

- Requires an authenticated Directus user UUID and a per-write
  `_pleroma_justification` value.
- Appends create/update audit events, including the complete previous JSON state
  for updates, through the current Directus transaction.
- Removes `_pleroma_justification` before the collection write.
- Blocks publishing unless the actor is a Directus administrator or its role ID
  is listed in `PLEROMA_PUBLISHER_ROLE_IDS`.
- Protects the audit collection from writes through Directus and blocks hard
  deletes. Use a reviewed correction/tombstone workflow instead.

## Setup

1. Apply `pleroma_audit_log.sql` to the project PostgreSQL database before
   enabling the hook. The Directus database role needs `INSERT` access to the
   audit table. It must not own that table; table owners can disable triggers.
2. Install this package in the Directus extensions directory and restart
   Directus. The package metadata declares compatibility with Directus 10/11.
3. Configure `PLEROMA_PUBLISHER_ROLE_IDS` with the UUIDs for Domain Specialist
   roles. Principal Investigators should use Directus administrator access.
4. If the publication field is not named `status`, set
   `PLEROMA_PUBLICATION_FIELD` accordingly. Set `PLEROMA_AUDIT_TABLE` only when
   using a correspondingly migrated table name.
5. Send the justification as `_pleroma_justification` in each create/update
   payload. For batch creates, include it in every record.

The hook governs custom collections and ignores Directus system collections.
`PLEROMA_UNAUDITED_COLLECTIONS` can exclude named custom collections; do not
exclude any collection containing Pleroma research data. The audit insert uses
the current database transaction so a failed insert rejects the write.

Hard deletes are intentionally unavailable because Directus delete filters do
not provide a justification payload. A future delete workflow must accept a
reason and write an audit event atomically before hard deletion is enabled.
Configure Directus policies separately for role-scoped draft access, Agora task
access, and public read-only access; this hook is not a replacement for RBAC.

Run the local policy tests with:

```sh
npm test
```
