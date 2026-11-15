CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS language_family (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    glottolog_code text NOT NULL UNIQUE
        CHECK (glottolog_code ~ '^[a-z]{4}[0-9]{4}$'),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    parent_family_id uuid
        REFERENCES language_family (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    proto_language_characteristics text,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT language_family_not_own_parent_check
        CHECK (parent_family_id IS NULL OR parent_family_id <> id)
);

CREATE INDEX IF NOT EXISTS language_family_parent_idx
    ON language_family (parent_family_id)
    WHERE parent_family_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS language_family_name_idx
    ON language_family (name);

COMMENT ON TABLE language_family IS
    'Glottolog-aligned language-family tree with persistent code and optional parent-family relationship.';
COMMENT ON COLUMN language_family.glottolog_code IS
    'Glottolog identifier; validate the code against the adopted Glottolog release.';
COMMENT ON COLUMN language_family.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE OR REPLACE FUNCTION prevent_language_family_cycle()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    closes_cycle boolean;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtext('pleroma.linguistic_family_tree')::bigint
    );

    IF NEW.parent_family_id IS NULL THEN
        RETURN NEW;
    END IF;

    WITH RECURSIVE ancestors (id, parent_family_id) AS (
        SELECT family.id, family.parent_family_id
        FROM language_family AS family
        WHERE family.id = NEW.parent_family_id
        UNION
        SELECT family.id, family.parent_family_id
        FROM language_family AS family
        JOIN ancestors ON family.id = ancestors.parent_family_id
    )
    SELECT EXISTS (
        SELECT 1
        FROM ancestors
        WHERE id = NEW.id
    )
    INTO closes_cycle;

    IF closes_cycle THEN
        RAISE EXCEPTION
            'Language-family parent relationship would create a cycle'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS language_family_acyclicity_check ON language_family;
CREATE TRIGGER language_family_acyclicity_check
BEFORE INSERT OR UPDATE ON language_family
FOR EACH ROW EXECUTE FUNCTION prevent_language_family_cycle();

CREATE TABLE IF NOT EXISTS linguistic_zone (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    language_name text NOT NULL CHECK (length(btrim(language_name)) > 0),
    glottolog_code text NOT NULL
        CHECK (glottolog_code ~ '^[a-z]{4}[0-9]{4}$'),
    language_family_id uuid
        REFERENCES language_family (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    dialect text,
    writing_system_uri text
        CHECK (writing_system_uri IS NULL OR writing_system_uri ~ '^https?://'),
    script_unicode_block text
        CHECK (
            script_unicode_block IS NULL
            OR script_unicode_block ~* '^U\+[0-9A-F]{4,6}(-U\+[0-9A-F]{4,6})?$'
        ),
    status text NOT NULL
        CHECK (status IN ('attested', 'reconstructed', 'hypothetical')),
    geometry geography(Polygon, 4326) NOT NULL,
    valid_time_edtf text NOT NULL CHECK (length(btrim(valid_time_edtf)) > 0),
    valid_year_bounds int4range NOT NULL
        CHECK (
            NOT isempty(valid_year_bounds)
            AND NOT lower_inf(valid_year_bounds)
            AND NOT upper_inf(valid_year_bounds)
        ),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT linguistic_zone_geometry_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_IsValid(geometry::geometry)
            AND ST_Area(geometry) > 0
        )
);

CREATE INDEX IF NOT EXISTS linguistic_zone_geometry_gix
    ON linguistic_zone USING gist (geometry);
CREATE INDEX IF NOT EXISTS linguistic_zone_year_bounds_gix
    ON linguistic_zone USING gist (valid_year_bounds);
CREATE INDEX IF NOT EXISTS linguistic_zone_glottolog_code_idx
    ON linguistic_zone (glottolog_code);
CREATE INDEX IF NOT EXISTS linguistic_zone_family_idx
    ON linguistic_zone (language_family_id)
    WHERE language_family_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS linguistic_zone_status_idx
    ON linguistic_zone (status);

COMMENT ON TABLE linguistic_zone IS
    'Time-bounded WGS 84 polygon for a documented or estimated language/dialect distribution.';
COMMENT ON COLUMN linguistic_zone.glottolog_code IS
    'Glottolog identifier for the language or dialect represented by the zone.';
COMMENT ON COLUMN linguistic_zone.valid_time_edtf IS
    'Canonical EDTF time span; syntax is validated by the API.';
COMMENT ON COLUMN linguistic_zone.valid_year_bounds IS
    'Normalized astronomical-year range for spatial/temporal filtering; the API keeps it consistent with EDTF.';
COMMENT ON COLUMN linguistic_zone.writing_system_uri IS
    'Optional URI of an approved SKOS writing-system concept.';
COMMENT ON COLUMN linguistic_zone.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS language_family_bibliography (
    language_family_id uuid NOT NULL
        REFERENCES language_family (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (language_family_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS language_family_bibliography_reference_idx
    ON language_family_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS linguistic_zone_bibliography (
    linguistic_zone_id uuid NOT NULL
        REFERENCES linguistic_zone (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (linguistic_zone_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS linguistic_zone_bibliography_reference_idx
    ON linguistic_zone_bibliography (bibliographic_reference_id);

CREATE OR REPLACE FUNCTION require_published_linguistic_citation()
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
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'language_family' THEN
            entity_table := 'language_family';
            bibliography_table := 'language_family_bibliography';
            foreign_key_column := 'language_family_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'language_family_bibliography' THEN
            entity_table := 'language_family';
            bibliography_table := 'language_family_bibliography';
            foreign_key_column := 'language_family_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.language_family_id, NEW.language_family_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.language_family_id];
            ELSE
                target_ids := ARRAY[NEW.language_family_id];
            END IF;
        WHEN 'linguistic_zone' THEN
            entity_table := 'linguistic_zone';
            bibliography_table := 'linguistic_zone_bibliography';
            foreign_key_column := 'linguistic_zone_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'linguistic_zone_bibliography' THEN
            entity_table := 'linguistic_zone';
            bibliography_table := 'linguistic_zone_bibliography';
            foreign_key_column := 'linguistic_zone_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.linguistic_zone_id, NEW.linguistic_zone_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.linguistic_zone_id];
            ELSE
                target_ids := ARRAY[NEW.linguistic_zone_id];
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
                    'Published linguistic record % in % requires at least one bibliographic reference',
                    target_id,
                    entity_table
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
    bibliography_table text;
BEGIN
    FOREACH entity_table IN ARRAY ARRAY['language_family', 'linguistic_zone'] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_requires_citation ON %I',
            entity_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_requires_citation
             AFTER INSERT OR UPDATE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_linguistic_citation()',
            entity_table
        );
    END LOOP;

    FOREACH bibliography_table IN ARRAY ARRAY[
        'language_family_bibliography',
        'linguistic_zone_bibliography'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_citation_required ON %I',
            bibliography_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_citation_required
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_linguistic_citation()',
            bibliography_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_linguistic_sphere_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS language_family_set_updated_at ON language_family;
CREATE TRIGGER language_family_set_updated_at
BEFORE UPDATE ON language_family
FOR EACH ROW EXECUTE FUNCTION set_linguistic_sphere_updated_at();

DROP TRIGGER IF EXISTS linguistic_zone_set_updated_at ON linguistic_zone;
CREATE TRIGGER linguistic_zone_set_updated_at
BEFORE UPDATE ON linguistic_zone
FOR EACH ROW EXECUTE FUNCTION set_linguistic_sphere_updated_at();
