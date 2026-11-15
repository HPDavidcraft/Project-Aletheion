CREATE TABLE IF NOT EXISTS theological_system (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    doctrine_overview text NOT NULL
        CHECK (length(btrim(doctrine_overview)) > 0),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS theological_system_name_idx
    ON theological_system (name);
CREATE INDEX IF NOT EXISTS theological_system_status_idx
    ON theological_system (publication_status);

COMMENT ON TABLE theological_system IS
    'Documented religious tradition container with a sourced doctrine overview and links to constituent Religious_Elements.';
COMMENT ON COLUMN theological_system.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS religious_element (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    element_name text NOT NULL CHECK (length(btrim(element_name)) > 0),
    motif_scheme_uri text NOT NULL CHECK (motif_scheme_uri ~ '^https?://'),
    motif_concept_uri text NOT NULL CHECK (motif_concept_uri ~ '^https?://'),
    motif_code text NOT NULL CHECK (length(btrim(motif_code)) > 0),
    narrative_procedure text NOT NULL
        CHECK (length(btrim(narrative_procedure)) > 0),
    symbolism text NOT NULL CHECK (length(btrim(symbolism)) > 0),
    doctrine text NOT NULL CHECK (length(btrim(doctrine)) > 0),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS religious_element_name_idx
    ON religious_element (element_name);
CREATE INDEX IF NOT EXISTS religious_element_motif_code_idx
    ON religious_element (motif_scheme_uri, motif_code);
CREATE INDEX IF NOT EXISTS religious_element_motif_concept_idx
    ON religious_element (motif_concept_uri);
CREATE INDEX IF NOT EXISTS religious_element_status_idx
    ON religious_element (publication_status);

COMMENT ON TABLE religious_element IS
    'Discrete religious or mythological element, including deity, ritual, narrative, or eschatological concept, kept distinct from its material and textual evidence.';
COMMENT ON COLUMN religious_element.motif_scheme_uri IS
    'URI for the adopted ATU or Thompson Motif-Index concept scheme; verify scheme and code against the selected release in the application.';
COMMENT ON COLUMN religious_element.motif_concept_uri IS
    'URI for the SKOS motif concept; verify that it belongs to motif_scheme_uri in the application.';
COMMENT ON COLUMN religious_element.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS theological_system_element (
    theological_system_id uuid NOT NULL
        REFERENCES theological_system (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    religious_element_id uuid NOT NULL
        REFERENCES religious_element (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (theological_system_id, religious_element_id)
);

CREATE INDEX IF NOT EXISTS theological_system_element_element_idx
    ON theological_system_element (religious_element_id);

COMMENT ON TABLE theological_system_element IS
    'Many-to-many membership linking documented traditions to constituent Religious_Elements.';

CREATE TABLE IF NOT EXISTS religious_element_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    religious_element_id uuid NOT NULL
        REFERENCES religious_element (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_type_uri text NOT NULL
        CHECK (relationship_type_uri ~ '^https?://'),
    find_id uuid
        REFERENCES find (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    feature_id uuid
        REFERENCES feature (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    text_witness_id uuid
        REFERENCES text_witness (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    evidence_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT religious_element_evidence_target_check
        CHECK (num_nonnulls(find_id, feature_id, text_witness_id) = 1)
);

CREATE INDEX IF NOT EXISTS religious_element_evidence_element_idx
    ON religious_element_evidence (religious_element_id);
CREATE INDEX IF NOT EXISTS religious_element_evidence_find_idx
    ON religious_element_evidence (find_id)
    WHERE find_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS religious_element_evidence_feature_idx
    ON religious_element_evidence (feature_id)
    WHERE feature_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS religious_element_evidence_witness_idx
    ON religious_element_evidence (text_witness_id)
    WHERE text_witness_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS religious_element_evidence_find_unique
    ON religious_element_evidence
        (religious_element_id, find_id, relationship_type_uri)
    WHERE find_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS religious_element_evidence_feature_unique
    ON religious_element_evidence
        (religious_element_id, feature_id, relationship_type_uri)
    WHERE feature_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS religious_element_evidence_witness_unique
    ON religious_element_evidence
        (religious_element_id, text_witness_id, relationship_type_uri)
    WHERE text_witness_id IS NOT NULL;

COMMENT ON TABLE religious_element_evidence IS
    'Typed evidence links to exactly one archaeological Find, architectural Feature, or textual Text_Witness.';

CREATE TABLE IF NOT EXISTS theological_system_bibliography (
    theological_system_id uuid NOT NULL
        REFERENCES theological_system (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (
        theological_system_id,
        bibliographic_reference_id,
        citation_type
    ),
    CONSTRAINT theological_system_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS theological_system_bibliography_reference_idx
    ON theological_system_bibliography (bibliographic_reference_id);

COMMENT ON TABLE theological_system_bibliography IS
    'Bibliographic anchors for system-level doctrine; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS religious_element_bibliography (
    religious_element_id uuid NOT NULL
        REFERENCES religious_element (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (
        religious_element_id,
        bibliographic_reference_id,
        citation_type
    ),
    CONSTRAINT religious_element_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS religious_element_bibliography_reference_idx
    ON religious_element_bibliography (bibliographic_reference_id);

COMMENT ON TABLE religious_element_bibliography IS
    'Comparative literature and source citations for Religious_Elements; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE OR REPLACE FUNCTION require_published_theological_support()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    element_ids uuid[] := ARRAY[]::uuid[];
    element_id uuid;
    system_ids uuid[] := ARRAY[]::uuid[];
    system_id uuid;
    publication_state text;
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'religious_element' THEN
            IF TG_OP = 'UPDATE' THEN
                element_ids := array_append(element_ids, OLD.id);
            END IF;
            element_ids := array_append(element_ids, NEW.id);
        WHEN 'religious_element_evidence' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                element_ids := array_append(
                    element_ids,
                    OLD.religious_element_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                element_ids := array_append(
                    element_ids,
                    NEW.religious_element_id
                );
            END IF;
        WHEN 'religious_element_bibliography' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                element_ids := array_append(
                    element_ids,
                    OLD.religious_element_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                element_ids := array_append(
                    element_ids,
                    NEW.religious_element_id
                );
            END IF;
        WHEN 'theological_system' THEN
            IF TG_OP = 'UPDATE' THEN
                system_ids := array_append(system_ids, OLD.id);
            END IF;
            system_ids := array_append(system_ids, NEW.id);
        WHEN 'theological_system_bibliography' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                system_ids := array_append(
                    system_ids,
                    OLD.theological_system_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                system_ids := array_append(
                    system_ids,
                    NEW.theological_system_id
                );
            END IF;
        WHEN 'theological_system_element' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                system_ids := array_append(
                    system_ids,
                    OLD.theological_system_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                system_ids := array_append(
                    system_ids,
                    NEW.theological_system_id
                );
            END IF;
    END CASE;

    FOREACH element_id IN ARRAY element_ids LOOP
        SELECT publication_status
        INTO publication_state
        FROM religious_element
        WHERE id = element_id;

        IF publication_state = 'published' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM religious_element_evidence
                WHERE religious_element_id = element_id
            ) THEN
                RAISE EXCEPTION
                    'Published Religious_Element % requires at least one anchored Find, Feature, or Text_Witness evidence link',
                    element_id
                    USING ERRCODE = '23514';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM religious_element_bibliography
                WHERE religious_element_id = element_id
            ) THEN
                RAISE EXCEPTION
                    'Published Religious_Element % requires at least one bibliographic reference',
                    element_id
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END LOOP;

    FOREACH system_id IN ARRAY system_ids LOOP
        SELECT publication_status
        INTO publication_state
        FROM theological_system
        WHERE id = system_id;

        IF publication_state = 'published' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM theological_system_bibliography
                WHERE theological_system_id = system_id
            ) THEN
                RAISE EXCEPTION
                    'Published Theological_System % requires at least one bibliographic reference',
                    system_id
                    USING ERRCODE = '23514';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM theological_system_element
                WHERE theological_system_id = system_id
            ) THEN
                RAISE EXCEPTION
                    'Published Theological_System % requires at least one linked Religious_Element',
                    system_id
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END LOOP;

    RETURN NULL;
END;
$$;

DO $$
DECLARE
    entity_table text;
    relation_table text;
BEGIN
    FOREACH entity_table IN ARRAY ARRAY[
        'religious_element',
        'theological_system'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_requires_theological_support ON %I',
            entity_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_requires_theological_support
             AFTER INSERT OR UPDATE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_theological_support()',
            entity_table
        );
    END LOOP;

    FOREACH relation_table IN ARRAY ARRAY[
        'religious_element_evidence',
        'religious_element_bibliography',
        'theological_system_bibliography',
        'theological_system_element'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS relation_requires_theological_support ON %I',
            relation_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER relation_requires_theological_support
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_theological_support()',
            relation_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_theological_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS theological_system_set_updated_at ON theological_system;
CREATE TRIGGER theological_system_set_updated_at
BEFORE UPDATE ON theological_system
FOR EACH ROW EXECUTE FUNCTION set_theological_updated_at();

DROP TRIGGER IF EXISTS religious_element_set_updated_at ON religious_element;
CREATE TRIGGER religious_element_set_updated_at
BEFORE UPDATE ON religious_element
FOR EACH ROW EXECUTE FUNCTION set_theological_updated_at();

CREATE OR REPLACE VIEW religious_element_evidence_context AS
SELECT
    evidence.id AS evidence_link_id,
    evidence.religious_element_id,
    'find'::text AS evidence_entity_type,
    find.id AS evidence_entity_id,
    evidence.relationship_type_uri,
    find.site_id,
    find.location::geometry AS evidence_location,
    COALESCE(stratigraphic_unit.year_bounds, occupational_period.year_bounds)
        AS evidence_year_bounds,
    COALESCE(
        stratigraphic_unit.date_range_edtf,
        occupational_period.absolute_date_range_edtf
    ) AS evidence_time_edtf
FROM religious_element_evidence AS evidence
JOIN find ON find.id = evidence.find_id
LEFT JOIN stratigraphic_unit
  ON stratigraphic_unit.id = find.stratigraphic_unit_id
LEFT JOIN occupational_period
  ON occupational_period.id = find.occupational_period_id
WHERE evidence.find_id IS NOT NULL

UNION ALL

SELECT
    evidence.id AS evidence_link_id,
    evidence.religious_element_id,
    'feature'::text AS evidence_entity_type,
    feature.id AS evidence_entity_id,
    evidence.relationship_type_uri,
    feature.site_id,
    feature.geometry::geometry AS evidence_location,
    COALESCE(stratigraphic_unit.year_bounds, occupational_period.year_bounds)
        AS evidence_year_bounds,
    COALESCE(
        stratigraphic_unit.date_range_edtf,
        occupational_period.absolute_date_range_edtf
    ) AS evidence_time_edtf
FROM religious_element_evidence AS evidence
JOIN feature ON feature.id = evidence.feature_id
LEFT JOIN stratigraphic_unit
  ON stratigraphic_unit.id = feature.stratigraphic_unit_id
LEFT JOIN occupational_period
  ON occupational_period.id = feature.occupational_period_id
WHERE evidence.feature_id IS NOT NULL

UNION ALL

SELECT
    evidence.id AS evidence_link_id,
    evidence.religious_element_id,
    'text_witness'::text AS evidence_entity_type,
    text_witness.id AS evidence_entity_id,
    evidence.relationship_type_uri,
    NULL::uuid AS site_id,
    NULL::geometry AS evidence_location,
    NULL::int4range AS evidence_year_bounds,
    text_witness.date_edtf AS evidence_time_edtf
FROM religious_element_evidence AS evidence
JOIN text_witness ON text_witness.id = evidence.text_witness_id
WHERE evidence.text_witness_id IS NOT NULL;

COMMENT ON VIEW religious_element_evidence_context IS
    'Typed evidence report context with location, site, and available time metadata; public use must observe publication and sensitive-provenance policies.';
