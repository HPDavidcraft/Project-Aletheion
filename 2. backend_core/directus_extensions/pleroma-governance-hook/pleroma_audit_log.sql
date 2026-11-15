CREATE TABLE IF NOT EXISTS pleroma_audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_uuid uuid NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    operation_type text NOT NULL CHECK (operation_type IN ('create', 'update')),
    collection_name text NOT NULL,
    record_key text NOT NULL,
    previous_state jsonb,
    justification text NOT NULL CHECK (length(btrim(justification)) > 0)
);

CREATE OR REPLACE FUNCTION prevent_pleroma_audit_log_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'pleroma_audit_log is append-only'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS pleroma_audit_log_no_row_mutation ON pleroma_audit_log;
CREATE TRIGGER pleroma_audit_log_no_row_mutation
BEFORE UPDATE OR DELETE ON pleroma_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_pleroma_audit_log_mutation();

DROP TRIGGER IF EXISTS pleroma_audit_log_no_truncate ON pleroma_audit_log;
CREATE TRIGGER pleroma_audit_log_no_truncate
BEFORE TRUNCATE ON pleroma_audit_log
FOR EACH STATEMENT EXECUTE FUNCTION prevent_pleroma_audit_log_mutation();

REVOKE UPDATE, DELETE, TRUNCATE ON pleroma_audit_log FROM PUBLIC;
