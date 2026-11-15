CREATE TABLE IF NOT EXISTS liturgical_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    description text NOT NULL CHECK (length(btrim(description)) > 0),
    date_edtf text CHECK (date_edtf IS NULL OR length(btrim(date_edtf)) > 0),
    recurrence_rule text CHECK (
        recurrence_rule IS NULL
        OR recurrence_rule ~* '^FREQ=(YEARLY|MONTHLY|WEEKLY|DAILY|HOURLY|MINUTELY|SECONDLY)(;|$)'
    ),
    astronomical_alignment_geo_feature_id uuid,
    associated_temple_feature_id uuid,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT liturgical_event_time_definition_check
        CHECK (date_edtf IS NOT NULL OR recurrence_rule IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS liturgical_event_status_idx
    ON liturgical_event (publication_status);
CREATE INDEX IF NOT EXISTS liturgical_event_alignment_idx
    ON liturgical_event (astronomical_alignment_geo_feature_id)
    WHERE astronomical_alignment_geo_feature_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS liturgical_event_temple_feature_idx
    ON liturgical_event (associated_temple_feature_id)
    WHERE associated_temple_feature_id IS NOT NULL;

COMMENT ON TABLE liturgical_event IS
    'Dateable or recurring ritual, festival, or ceremonial practice; recurrence strings use RFC 5545 RRULE and require application validation.';
COMMENT ON COLUMN liturgical_event.astronomical_alignment_geo_feature_id IS
    'UUID reference to Geo_Feature_Temporal; foreign key is deferred until the 4D-GIS module is available.';
COMMENT ON COLUMN liturgical_event.associated_temple_feature_id IS
    'UUID reference to a temple Feature; foreign key is deferred until the site-hierarchy schema exists.';
COMMENT ON COLUMN liturgical_event.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS oral_tradition_node (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    tradition_type text NOT NULL
        CHECK (tradition_type IN ('myth', 'formulaic_speech', 'oral_history', 'other')),
    mnemonic_structure text NOT NULL
        CHECK (length(btrim(mnemonic_structure)) > 0),
    performative_context text NOT NULL
        CHECK (length(btrim(performative_context)) > 0),
    performer_role_uri text
        CHECK (performer_role_uri IS NULL OR performer_role_uri ~ '^https?://'),
    audience_description text,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS oral_tradition_type_idx
    ON oral_tradition_node (tradition_type);
CREATE INDEX IF NOT EXISTS oral_tradition_status_idx
    ON oral_tradition_node (publication_status);

COMMENT ON TABLE oral_tradition_node IS
    'Documented oral tradition, myth, or formulaic speech act with mnemonic and performative context.';
COMMENT ON COLUMN oral_tradition_node.performer_role_uri IS
    'Optional URI of an approved SKOS performer-role concept.';

CREATE TABLE IF NOT EXISTS oral_tradition_transmission (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id uuid NOT NULL
        REFERENCES oral_tradition_node (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    target_node_id uuid NOT NULL
        REFERENCES oral_tradition_node (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    transmission_type text NOT NULL
        CHECK (transmission_type IN (
            'oral',
            'written',
            'performed',
            'adapted',
            'recorded',
            'other'
        )),
    transmission_date_edtf text
        CHECK (
            transmission_date_edtf IS NULL
            OR length(btrim(transmission_date_edtf)) > 0
        ),
    context_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT oral_tradition_transmission_not_self_check
        CHECK (source_node_id <> target_node_id),
    UNIQUE (source_node_id, target_node_id, transmission_type)
);

CREATE INDEX IF NOT EXISTS oral_tradition_transmission_target_idx
    ON oral_tradition_transmission (target_node_id);

COMMENT ON TABLE oral_tradition_transmission IS
    'Directed transmission edge between recorded tradition nodes; cycles are allowed when they document historical feedback or revival.';

CREATE TABLE IF NOT EXISTS sensory_profile (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_name text NOT NULL CHECK (length(btrim(profile_name)) > 0),
    associated_entity_type text NOT NULL
        CHECK (associated_entity_type IN ('site', 'occupational_period', 'feature')),
    associated_entity_id uuid NOT NULL,
    rt60_seconds numeric CHECK (rt60_seconds IS NULL OR rt60_seconds >= 0),
    impulse_response_uri text
        CHECK (impulse_response_uri IS NULL OR impulse_response_uri ~ '^(https?|s3|minio)://'),
    acoustic_simulation_parameters jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(acoustic_simulation_parameters) = 'object'),
    lighting_conditions jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(lighting_conditions) = 'object'),
    media_gallery_id uuid NOT NULL,
    notes text,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS sensory_profile_entity_idx
    ON sensory_profile (associated_entity_type, associated_entity_id);
CREATE INDEX IF NOT EXISTS sensory_profile_status_idx
    ON sensory_profile (publication_status);

COMMENT ON TABLE sensory_profile IS
    'Multimodal sensory reconstruction associated with a Site, Occupational_Period, or Feature; binaries are stored externally.';
COMMENT ON COLUMN sensory_profile.impulse_response_uri IS
    'Object-storage pointer to the impulse response file, never a PostgreSQL binary value.';
COMMENT ON COLUMN sensory_profile.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS sensory_profile_color (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sensory_profile_id uuid NOT NULL
        REFERENCES sensory_profile (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    hex_color text NOT NULL CHECK (hex_color ~ '^#[A-Fa-f0-9]{6}$'),
    material_association text NOT NULL
        CHECK (length(btrim(material_association)) > 0),
    color_notes text,
    display_order integer NOT NULL DEFAULT 0 CHECK (display_order >= 0),
    UNIQUE (sensory_profile_id, display_order)
);

CREATE TABLE IF NOT EXISTS sensory_profile_audio_asset (
    sensory_profile_id uuid NOT NULL
        REFERENCES sensory_profile (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    media_asset_id uuid NOT NULL,
    asset_type text NOT NULL
        CHECK (asset_type IN (
            'language_pronunciation',
            'music_reconstruction',
            'other_audio'
        )),
    description text,
    PRIMARY KEY (sensory_profile_id, media_asset_id)
);

COMMENT ON TABLE sensory_profile_audio_asset IS
    'Audio Media_Asset references for reconstructed language pronunciation, music, and related audio; no binary data is stored here.';

CREATE TABLE IF NOT EXISTS liturgical_event_bibliography (
    liturgical_event_id uuid NOT NULL
        REFERENCES liturgical_event (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    bibliographic_reference_id uuid NOT NULL,
    citation_type text NOT NULL
        CHECK (citation_type IN (
            'primary_source',
            'excavation_report',
            'synthesis',
            'database_record',
            'personal_communication'
        )),
    page_number text,
    quotation text,
    PRIMARY KEY (liturgical_event_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS liturgical_event_bibliography_reference_idx
    ON liturgical_event_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS oral_tradition_bibliography (
    oral_tradition_node_id uuid NOT NULL
        REFERENCES oral_tradition_node (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    bibliographic_reference_id uuid NOT NULL,
    citation_type text NOT NULL
        CHECK (citation_type IN (
            'primary_source',
            'excavation_report',
            'synthesis',
            'database_record',
            'personal_communication'
        )),
    page_number text,
    quotation text,
    PRIMARY KEY (oral_tradition_node_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS oral_tradition_bibliography_reference_idx
    ON oral_tradition_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS sensory_profile_bibliography (
    sensory_profile_id uuid NOT NULL
        REFERENCES sensory_profile (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    bibliographic_reference_id uuid NOT NULL,
    citation_type text NOT NULL
        CHECK (citation_type IN (
            'primary_source',
            'excavation_report',
            'synthesis',
            'database_record',
            'personal_communication'
        )),
    page_number text,
    quotation text,
    PRIMARY KEY (sensory_profile_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS sensory_profile_bibliography_reference_idx
    ON sensory_profile_bibliography (bibliographic_reference_id);

CREATE OR REPLACE FUNCTION require_published_intangible_evidence()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_ids uuid[];
    target_id uuid;
    entity_table text;
    bibliography_table text;
    foreign_key_column text;
    parent_status text;
    has_citation boolean;
    has_sensory_data boolean;
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'liturgical_event' THEN
            entity_table := 'liturgical_event';
            bibliography_table := 'liturgical_event_bibliography';
            foreign_key_column := 'liturgical_event_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'liturgical_event_bibliography' THEN
            entity_table := 'liturgical_event';
            bibliography_table := 'liturgical_event_bibliography';
            foreign_key_column := 'liturgical_event_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.liturgical_event_id, NEW.liturgical_event_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.liturgical_event_id];
            ELSE
                target_ids := ARRAY[NEW.liturgical_event_id];
            END IF;
        WHEN 'oral_tradition_node' THEN
            entity_table := 'oral_tradition_node';
            bibliography_table := 'oral_tradition_bibliography';
            foreign_key_column := 'oral_tradition_node_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'oral_tradition_bibliography' THEN
            entity_table := 'oral_tradition_node';
            bibliography_table := 'oral_tradition_bibliography';
            foreign_key_column := 'oral_tradition_node_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.oral_tradition_node_id, NEW.oral_tradition_node_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.oral_tradition_node_id];
            ELSE
                target_ids := ARRAY[NEW.oral_tradition_node_id];
            END IF;
        WHEN 'sensory_profile' THEN
            entity_table := 'sensory_profile';
            bibliography_table := 'sensory_profile_bibliography';
            foreign_key_column := 'sensory_profile_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'sensory_profile_bibliography' THEN
            entity_table := 'sensory_profile';
            bibliography_table := 'sensory_profile_bibliography';
            foreign_key_column := 'sensory_profile_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.sensory_profile_id, NEW.sensory_profile_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.sensory_profile_id];
            ELSE
                target_ids := ARRAY[NEW.sensory_profile_id];
            END IF;
        WHEN 'sensory_profile_color' THEN
            entity_table := 'sensory_profile';
            bibliography_table := 'sensory_profile_bibliography';
            foreign_key_column := 'sensory_profile_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.sensory_profile_id, NEW.sensory_profile_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.sensory_profile_id];
            ELSE
                target_ids := ARRAY[NEW.sensory_profile_id];
            END IF;
        WHEN 'sensory_profile_audio_asset' THEN
            entity_table := 'sensory_profile';
            bibliography_table := 'sensory_profile_bibliography';
            foreign_key_column := 'sensory_profile_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.sensory_profile_id, NEW.sensory_profile_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.sensory_profile_id];
            ELSE
                target_ids := ARRAY[NEW.sensory_profile_id];
            END IF;
    END CASE;

    FOREACH target_id IN ARRAY target_ids LOOP
        EXECUTE format(
            'SELECT publication_status FROM %I WHERE id = $1',
            entity_table
        )
        INTO parent_status
        USING target_id;

        IF parent_status = 'published' THEN
            EXECUTE format(
                'SELECT EXISTS (SELECT 1 FROM %I WHERE %I = $1)',
                bibliography_table,
                foreign_key_column
            )
            INTO has_citation
            USING target_id;

            IF NOT has_citation THEN
                RAISE EXCEPTION
                    'Published intangible-heritage record % in % requires a bibliographic reference',
                    target_id,
                    entity_table
                    USING ERRCODE = '23514';
            END IF;

            IF entity_table = 'sensory_profile' THEN
                SELECT
                    rt60_seconds IS NOT NULL
                    OR impulse_response_uri IS NOT NULL
                    OR acoustic_simulation_parameters <> '{}'::jsonb
                    OR lighting_conditions <> '{}'::jsonb
                    OR EXISTS (
                        SELECT 1
                        FROM sensory_profile_color
                        WHERE sensory_profile_id = target_id
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM sensory_profile_audio_asset
                        WHERE sensory_profile_id = target_id
                    )
                INTO has_sensory_data
                FROM sensory_profile
                WHERE id = target_id;

                IF NOT has_sensory_data THEN
                    RAISE EXCEPTION
                        'A published Sensory_Profile requires at least one acoustic, visual, or audio modality'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
        END IF;
    END LOOP;
    RETURN NULL;
END;
$$;

DO $$
DECLARE
    entity_table text;
    bibliography_table text;
BEGIN
    FOREACH entity_table IN ARRAY ARRAY[
        'liturgical_event',
        'oral_tradition_node',
        'sensory_profile'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_requires_evidence ON %I',
            entity_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_requires_evidence
             AFTER INSERT OR UPDATE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_intangible_evidence()',
            entity_table
        );
    END LOOP;

    FOREACH bibliography_table IN ARRAY ARRAY[
        'liturgical_event_bibliography',
        'oral_tradition_bibliography',
        'sensory_profile_bibliography',
        'sensory_profile_color',
        'sensory_profile_audio_asset'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_citation_required ON %I',
            bibliography_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_citation_required
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_intangible_evidence()',
            bibliography_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_intangible_heritage_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS liturgical_event_set_updated_at ON liturgical_event;
CREATE TRIGGER liturgical_event_set_updated_at
BEFORE UPDATE ON liturgical_event
FOR EACH ROW EXECUTE FUNCTION set_intangible_heritage_updated_at();

DROP TRIGGER IF EXISTS oral_tradition_node_set_updated_at ON oral_tradition_node;
CREATE TRIGGER oral_tradition_node_set_updated_at
BEFORE UPDATE ON oral_tradition_node
FOR EACH ROW EXECUTE FUNCTION set_intangible_heritage_updated_at();

DROP TRIGGER IF EXISTS sensory_profile_set_updated_at ON sensory_profile;
CREATE TRIGGER sensory_profile_set_updated_at
BEFORE UPDATE ON sensory_profile
FOR EACH ROW EXECUTE FUNCTION set_intangible_heritage_updated_at();
