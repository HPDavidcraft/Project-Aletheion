CREATE TABLE IF NOT EXISTS conservation_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    find_id uuid NOT NULL UNIQUE,
    condition_state text NOT NULL
        CHECK (condition_state IN (
            'stable',
            'active_corrosion',
            'fragmenting',
            'lost',
            'repatriated'
        )),
    last_inspected_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE conservation_log IS
    'Current conservation state and inspection history for a Find; the Find foreign key is deferred until the site-hierarchy schema exists.';

CREATE TABLE IF NOT EXISTS conservation_treatment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conservation_log_id uuid NOT NULL
        REFERENCES conservation_log (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sequence_number integer NOT NULL CHECK (sequence_number >= 0),
    treatment_date_edtf text NOT NULL
        CHECK (length(btrim(treatment_date_edtf)) > 0),
    materials text NOT NULL CHECK (length(btrim(materials)) > 0),
    treatment_description text NOT NULL
        CHECK (length(btrim(treatment_description)) > 0),
    performed_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (conservation_log_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS conservation_treatment_log_order_idx
    ON conservation_treatment (conservation_log_id, sequence_number);

CREATE TABLE IF NOT EXISTS conservation_inspection (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conservation_log_id uuid NOT NULL
        REFERENCES conservation_log (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    inspected_at timestamptz NOT NULL DEFAULT now(),
    condition_state text NOT NULL
        CHECK (condition_state IN (
            'stable',
            'active_corrosion',
            'fragmenting',
            'lost',
            'repatriated'
        )),
    temperature_c numeric,
    relative_humidity_percent numeric
        CHECK (
            relative_humidity_percent IS NULL
            OR relative_humidity_percent BETWEEN 0 AND 100
        ),
    light_level_lux numeric CHECK (light_level_lux IS NULL OR light_level_lux >= 0),
    notes text,
    inspector_uuid uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conservation_inspection_log_time_idx
    ON conservation_inspection (conservation_log_id, inspected_at DESC);

CREATE TABLE IF NOT EXISTS conservation_alert_outbox (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conservation_log_id uuid NOT NULL
        REFERENCES conservation_log (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    condition_state text NOT NULL
        CHECK (condition_state IN ('active_corrosion', 'fragmenting')),
    recipient_role_code text NOT NULL DEFAULT 'conservator'
        CHECK (length(btrim(recipient_role_code)) > 0),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'delivered', 'failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    delivered_at timestamptz,
    last_error text
);

CREATE INDEX IF NOT EXISTS conservation_alert_pending_idx
    ON conservation_alert_outbox (created_at)
    WHERE status = 'pending';

CREATE OR REPLACE FUNCTION set_conservation_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION queue_conservation_alert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    condition_changed boolean;
BEGIN
    IF TG_OP = 'INSERT' THEN
        condition_changed := true;
    ELSE
        condition_changed := NEW.condition_state IS DISTINCT FROM OLD.condition_state;
    END IF;

    IF condition_changed
       AND NEW.condition_state IN ('active_corrosion', 'fragmenting') THEN
        INSERT INTO conservation_alert_outbox (
            conservation_log_id,
            condition_state
        )
        VALUES (NEW.id, NEW.condition_state);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS conservation_log_set_updated_at ON conservation_log;
CREATE TRIGGER conservation_log_set_updated_at
BEFORE UPDATE ON conservation_log
FOR EACH ROW EXECUTE FUNCTION set_conservation_updated_at();

DROP TRIGGER IF EXISTS conservation_log_queue_alert ON conservation_log;
CREATE TRIGGER conservation_log_queue_alert
AFTER INSERT OR UPDATE ON conservation_log
FOR EACH ROW EXECUTE FUNCTION queue_conservation_alert();

CREATE OR REPLACE FUNCTION apply_conservation_inspection()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE conservation_log
    SET condition_state = NEW.condition_state,
        last_inspected_at = NEW.inspected_at
    WHERE id = NEW.conservation_log_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS conservation_inspection_update_current_state
    ON conservation_inspection;
CREATE TRIGGER conservation_inspection_update_current_state
AFTER INSERT ON conservation_inspection
FOR EACH ROW EXECUTE FUNCTION apply_conservation_inspection();

CREATE OR REPLACE FUNCTION prevent_conservation_log_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Conservation logs cannot be deleted; preserve the inspection and treatment history'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS conservation_log_no_delete ON conservation_log;
CREATE TRIGGER conservation_log_no_delete
BEFORE DELETE ON conservation_log
FOR EACH ROW EXECUTE FUNCTION prevent_conservation_log_delete();

CREATE TABLE IF NOT EXISTS provenance_chain (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type text NOT NULL
        CHECK (subject_type IN (
            'find',
            'bio_sample',
            'human_sample',
            'flora_specimen',
            'fauna_specimen'
        )),
    subject_id uuid NOT NULL,
    stratigraphic_unit_id uuid,
    surface_collection_context text,
    human_remains_ethics_reviewed boolean,
    human_remains_ethics_reference text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (subject_type, subject_id),
    CONSTRAINT provenance_biological_context_check CHECK (
        subject_type NOT IN (
            'bio_sample',
            'human_sample',
            'flora_specimen',
            'fauna_specimen'
        )
        OR stratigraphic_unit_id IS NOT NULL
        OR NULLIF(btrim(surface_collection_context), '') IS NOT NULL
    ),
    CONSTRAINT provenance_human_remains_ethics_check CHECK (
        subject_type <> 'human_sample'
        OR (
            human_remains_ethics_reviewed IS NOT NULL
            AND human_remains_ethics_reference IS NOT NULL
            AND length(btrim(human_remains_ethics_reference)) > 0
        )
    )
);

COMMENT ON TABLE provenance_chain IS
    'One provenance chain per governed Find or biological-sample record; external subject and stratigraphic UUIDs are validated by the application until their schemas are installed.';

CREATE INDEX IF NOT EXISTS provenance_chain_subject_idx
    ON provenance_chain (subject_type, subject_id);

CREATE TABLE IF NOT EXISTS provenance_chain_entry (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provenance_chain_id uuid NOT NULL
        REFERENCES provenance_chain (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    sequence_number integer NOT NULL CHECK (sequence_number >= 0),
    custodian text NOT NULL CHECK (length(btrim(custodian)) > 0),
    acquisition_method text NOT NULL
        CHECK (acquisition_method IN (
            'excavation',
            'purchase',
            'gift',
            'seizure',
            'repatriation',
            'unknown'
        )),
    date_range_edtf text NOT NULL CHECK (length(btrim(date_range_edtf)) > 0),
    legal_status text NOT NULL
        CHECK (legal_status IN (
            'clear',
            'contested',
            'repatriated',
            'stolen',
            'under_review'
        )),
    claimant_community text,
    documentation_reference text,
    notes text,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provenance_chain_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS provenance_chain_entry_status_idx
    ON provenance_chain_entry (legal_status);
CREATE INDEX IF NOT EXISTS provenance_chain_entry_chain_order_idx
    ON provenance_chain_entry (provenance_chain_id, sequence_number);

CREATE OR REPLACE FUNCTION require_provenance_chain_entry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    chain_id uuid;
BEGIN
    IF TG_TABLE_NAME = 'provenance_chain' THEN
        chain_id := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        chain_id := OLD.provenance_chain_id;
    ELSE
        chain_id := NEW.provenance_chain_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM provenance_chain_entry
        WHERE provenance_chain_id = chain_id
    ) THEN
        RAISE EXCEPTION
            'A provenance chain must retain at least one custody entry'
            USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS provenance_chain_entry_required
    ON provenance_chain_entry;
CREATE CONSTRAINT TRIGGER provenance_chain_entry_required
AFTER INSERT OR UPDATE OR DELETE ON provenance_chain_entry
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_provenance_chain_entry();

DROP TRIGGER IF EXISTS provenance_chain_requires_entry
    ON provenance_chain;
CREATE CONSTRAINT TRIGGER provenance_chain_requires_entry
AFTER INSERT ON provenance_chain
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_provenance_chain_entry();

CREATE OR REPLACE FUNCTION prevent_provenance_chain_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Provenance chains cannot be deleted; correct the chain with a new custody entry'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS provenance_chain_no_delete ON provenance_chain;
CREATE TRIGGER provenance_chain_no_delete
BEFORE DELETE ON provenance_chain
FOR EACH ROW EXECUTE FUNCTION prevent_provenance_chain_delete();

CREATE OR REPLACE FUNCTION provenance_allows_public_export(
    requested_subject_type text,
    requested_subject_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
STRICT
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM provenance_chain AS chain
        WHERE chain.subject_type = requested_subject_type
          AND chain.subject_id = requested_subject_id
          AND EXISTS (
              SELECT 1
              FROM provenance_chain_entry AS entry
              WHERE entry.provenance_chain_id = chain.id
          )
          AND NOT EXISTS (
              SELECT 1
              FROM provenance_chain_entry AS entry
              WHERE entry.provenance_chain_id = chain.id
                AND entry.legal_status <> 'clear'
          )
    )
$$;

COMMENT ON FUNCTION provenance_allows_public_export(text, uuid) IS
    'Returns true only when a chain exists, has at least one custody entry, and every entry is legally clear; authorized overrides belong in the access-controlled API.';

CREATE TABLE IF NOT EXISTS excavation_protocol (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    method_type text NOT NULL
        CHECK (method_type IN (
            'open_area',
            'trench',
            'test_pit',
            'remote_sensing_only',
            'surface_survey'
        )),
    sampling_strategy text NOT NULL
        CHECK (sampling_strategy IN (
            'systematic',
            'judgmental',
            'random',
            'stratified'
        )),
    sieve_mesh_size_mm numeric CHECK (
        sieve_mesh_size_mm IS NULL OR sieve_mesh_size_mm > 0
    ),
    minimum_find_size_mm numeric CHECK (
        minimum_find_size_mm IS NULL OR minimum_find_size_mm >= 0
    ),
    significance_bias_factor numeric NOT NULL
        CHECK (significance_bias_factor BETWEEN 0 AND 1),
    campaign_reference text,
    documentation_uri text CHECK (
        documentation_uri IS NULL OR documentation_uri ~ '^https?://'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS excavation_protocol_name_idx
    ON excavation_protocol (name);

COMMENT ON TABLE excavation_protocol IS
    'Field methodology template and recovery standards; significance_bias_factor is consumed by trust-score computation.';

DROP TRIGGER IF EXISTS excavation_protocol_set_updated_at
    ON excavation_protocol;
CREATE TRIGGER excavation_protocol_set_updated_at
BEFORE UPDATE ON excavation_protocol
FOR EACH ROW EXECUTE FUNCTION set_conservation_updated_at();
