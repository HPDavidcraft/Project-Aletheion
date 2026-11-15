CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS site (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    official_name text NOT NULL CHECK (length(btrim(official_name)) > 0),
    alt_names jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(alt_names) = 'array'),
    boundary geography(Polygon, 4326) NOT NULL,
    body_text text NOT NULL CHECK (length(btrim(body_text)) > 0),
    primary_paleo_climate_model_id uuid,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT site_boundary_check
        CHECK (
            NOT ST_IsEmpty(boundary::geometry)
            AND ST_IsValid(boundary::geometry)
            AND ST_Area(boundary) > 0
        )
);

CREATE INDEX IF NOT EXISTS site_boundary_gix
    ON site USING gist (boundary);
CREATE INDEX IF NOT EXISTS site_official_name_idx
    ON site (official_name);
CREATE INDEX IF NOT EXISTS site_alt_names_gin
    ON site USING gin (alt_names);

COMMENT ON TABLE site IS
    'Archaeological site boundary, names, narrative, and primary paleoclimate pointer.';
COMMENT ON COLUMN site.primary_paleo_climate_model_id IS
    'UUID pointer to the climate model for the primary active period; update when that period changes.';
COMMENT ON COLUMN site.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS occupational_period (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id uuid NOT NULL
        REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    geometry geography(Polygon, 4326) NOT NULL,
    absolute_date_range_edtf text NOT NULL
        CHECK (length(btrim(absolute_date_range_edtf)) > 0),
    year_bounds int4range NOT NULL CHECK (NOT isempty(year_bounds)),
    paleo_climate_model_id uuid,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT occupational_period_geometry_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_IsValid(geometry::geometry)
            AND ST_Area(geometry) > 0
        ),
    UNIQUE (site_id, name)
);

CREATE INDEX IF NOT EXISTS occupational_period_site_idx
    ON occupational_period (site_id);
CREATE INDEX IF NOT EXISTS occupational_period_geometry_gix
    ON occupational_period USING gist (geometry);
CREATE INDEX IF NOT EXISTS occupational_period_year_bounds_gix
    ON occupational_period USING gist (year_bounds);

COMMENT ON COLUMN occupational_period.absolute_date_range_edtf IS
    'Canonical EDTF date range; validate syntax and temporal consistency in the API.';
COMMENT ON COLUMN occupational_period.year_bounds IS
    'Normalized astronomical-year range for overlap queries; keep consistent with the EDTF value in the API.';
COMMENT ON COLUMN occupational_period.paleo_climate_model_id IS
    'UUID pointer for the period-specific paleoclimate layer; foreign key is deferred until that module is modeled.';

CREATE TABLE IF NOT EXISTS stratigraphic_unit (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id uuid NOT NULL
        REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    occupational_period_id uuid
        REFERENCES occupational_period (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    unit_code text NOT NULL CHECK (length(btrim(unit_code)) > 0),
    geometry geography(Polygon, 4326) NOT NULL,
    deposition_interpretation_uri text NOT NULL
        CHECK (deposition_interpretation_uri ~ '^https?://'),
    deposition_interpretation_notes text NOT NULL
        CHECK (length(btrim(deposition_interpretation_notes)) > 0),
    field_notes text NOT NULL CHECK (length(btrim(field_notes)) > 0),
    date_range_edtf text
        CHECK (date_range_edtf IS NULL OR length(btrim(date_range_edtf)) > 0),
    year_bounds int4range
        CHECK (year_bounds IS NULL OR NOT isempty(year_bounds)),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT stratigraphic_unit_geometry_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_IsValid(geometry::geometry)
            AND ST_Area(geometry) > 0
        ),
    CONSTRAINT stratigraphic_unit_date_pair_check
        CHECK ((date_range_edtf IS NULL) = (year_bounds IS NULL)),
    UNIQUE (site_id, unit_code)
);

CREATE INDEX IF NOT EXISTS stratigraphic_unit_site_idx
    ON stratigraphic_unit (site_id);
CREATE INDEX IF NOT EXISTS stratigraphic_unit_period_idx
    ON stratigraphic_unit (occupational_period_id)
    WHERE occupational_period_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS stratigraphic_unit_geometry_gix
    ON stratigraphic_unit USING gist (geometry);
CREATE INDEX IF NOT EXISTS stratigraphic_unit_year_bounds_gix
    ON stratigraphic_unit USING gist (year_bounds)
    WHERE year_bounds IS NOT NULL;

COMMENT ON TABLE stratigraphic_unit IS
    'Modeled stratigraphic volume with site-unique identifier and relational Harris Matrix edges.';
COMMENT ON COLUMN stratigraphic_unit.deposition_interpretation_uri IS
    'URI of an approved SKOS deposition concept.';
COMMENT ON COLUMN stratigraphic_unit.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS stratigraphic_relationship (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id uuid NOT NULL
        REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    related_unit_id uuid NOT NULL
        REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_type text NOT NULL
        CHECK (relationship_type IN ('above', 'below', 'contemporary')),
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT stratigraphic_relationship_not_self_check
        CHECK (unit_id <> related_unit_id),
    CONSTRAINT contemporary_relationship_canonical_check
        CHECK (relationship_type <> 'contemporary' OR unit_id < related_unit_id),
    UNIQUE (unit_id, related_unit_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS stratigraphic_relationship_related_idx
    ON stratigraphic_relationship (related_unit_id);

COMMENT ON TABLE stratigraphic_relationship IS
    'Normalized Harris Matrix edges. Above/below edges are checked as a directed acyclic graph; contemporary pairs are stored once in UUID order.';

CREATE OR REPLACE FUNCTION validate_stratigraphic_relationship()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    unit_site_id uuid;
    related_site_id uuid;
    lower_unit_id uuid;
    upper_unit_id uuid;
    excluded_relationship_id uuid;
    cycle_found boolean;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtext('pleroma.stratigraphic_relationship_graph')::bigint
    );

    SELECT site_id INTO unit_site_id
    FROM stratigraphic_unit
    WHERE id = NEW.unit_id;

    SELECT site_id INTO related_site_id
    FROM stratigraphic_unit
    WHERE id = NEW.related_unit_id;

    IF unit_site_id IS DISTINCT FROM related_site_id THEN
        RAISE EXCEPTION
            'Stratigraphic relationships must connect units from the same site'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type = 'contemporary' THEN
        RETURN NEW;
    ELSIF NEW.relationship_type = 'above' THEN
        lower_unit_id := NEW.related_unit_id;
        upper_unit_id := NEW.unit_id;
    ELSE
        lower_unit_id := NEW.unit_id;
        upper_unit_id := NEW.related_unit_id;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        excluded_relationship_id := OLD.id;
    END IF;

    WITH RECURSIVE reachable (unit_id) AS (
        SELECT upper_unit_id
        UNION
        SELECT CASE
            WHEN relationship.relationship_type = 'above'
                THEN relationship.unit_id
            ELSE relationship.related_unit_id
        END
        FROM stratigraphic_relationship AS relationship
        JOIN reachable
          ON reachable.unit_id = CASE
              WHEN relationship.relationship_type = 'above'
                  THEN relationship.related_unit_id
              ELSE relationship.unit_id
          END
        WHERE relationship.relationship_type IN ('above', 'below')
          AND (
              excluded_relationship_id IS NULL
              OR relationship.id <> excluded_relationship_id
          )
    )
    SELECT EXISTS (
        SELECT 1
        FROM reachable
        WHERE unit_id = lower_unit_id
    )
    INTO cycle_found;

    IF cycle_found THEN
        RAISE EXCEPTION
            'Stratigraphic relationship would create a Harris Matrix cycle (unit %, related unit %)',
            NEW.unit_id,
            NEW.related_unit_id
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS stratigraphic_relationship_validate
    ON stratigraphic_relationship;
CREATE TRIGGER stratigraphic_relationship_validate
BEFORE INSERT OR UPDATE ON stratigraphic_relationship
FOR EACH ROW EXECUTE FUNCTION validate_stratigraphic_relationship();

CREATE TABLE IF NOT EXISTS find (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id uuid NOT NULL
        REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    occupational_period_id uuid
        REFERENCES occupational_period (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    stratigraphic_unit_id uuid
        REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    location geography(Point, 4326) NOT NULL,
    inventory_institution text NOT NULL
        CHECK (length(btrim(inventory_institution)) > 0),
    inventory_id text NOT NULL CHECK (length(btrim(inventory_id)) > 0),
    object_type_uri text NOT NULL CHECK (object_type_uri ~ '^https?://'),
    physical_description text NOT NULL
        CHECK (length(btrim(physical_description)) > 0),
    iconography_analysis text,
    material_type_uri text NOT NULL CHECK (material_type_uri ~ '^https?://'),
    source_resource_node_id uuid
        REFERENCES resource_node (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    provenance_chain_id uuid NOT NULL UNIQUE
        REFERENCES provenance_chain (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT find_location_check
        CHECK (NOT ST_IsEmpty(location::geometry) AND ST_IsValid(location::geometry)),
    UNIQUE (inventory_institution, inventory_id)
);

CREATE INDEX IF NOT EXISTS find_site_idx ON find (site_id);
CREATE INDEX IF NOT EXISTS find_period_idx ON find (occupational_period_id)
    WHERE occupational_period_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS find_stratigraphic_unit_idx ON find (stratigraphic_unit_id)
    WHERE stratigraphic_unit_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS find_location_gix ON find USING gist (location);
CREATE INDEX IF NOT EXISTS find_object_type_idx ON find (object_type_uri);
CREATE INDEX IF NOT EXISTS find_material_type_idx ON find (material_type_uri);

COMMENT ON TABLE find IS
    'Portable archaeological object, institutionally inventoried and linked to its context, evidence, and provenance.';
COMMENT ON COLUMN find.object_type_uri IS
    'URI of an approved Getty AAT concept.';
COMMENT ON COLUMN find.material_type_uri IS
    'URI of an approved SKOS material concept.';
COMMENT ON COLUMN find.source_resource_node_id IS
    'Optional geological/resource provenance source.';
COMMENT ON COLUMN find.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS feature (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id uuid NOT NULL
        REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    occupational_period_id uuid
        REFERENCES occupational_period (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    stratigraphic_unit_id uuid
        REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    geometry geography(Geometry, 4326) NOT NULL,
    feature_type_uri text NOT NULL CHECK (feature_type_uri ~ '^https?://'),
    contextual_description text NOT NULL
        CHECK (length(btrim(contextual_description)) > 0),
    interpretation_notes text,
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT feature_geometry_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_IsValid(geometry::geometry)
        )
);

CREATE INDEX IF NOT EXISTS feature_site_idx ON feature (site_id);
CREATE INDEX IF NOT EXISTS feature_period_idx ON feature (occupational_period_id)
    WHERE occupational_period_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS feature_stratigraphic_unit_idx ON feature (stratigraphic_unit_id)
    WHERE stratigraphic_unit_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS feature_geometry_gix ON feature USING gist (geometry);
CREATE INDEX IF NOT EXISTS feature_type_idx ON feature (feature_type_uri);

COMMENT ON TABLE feature IS
    'Non-portable physical manifestation within a site, with an independently modeled spatial geometry.';
COMMENT ON COLUMN feature.feature_type_uri IS
    'URI of an approved Getty AAT concept.';
COMMENT ON COLUMN feature.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE OR REPLACE FUNCTION validate_site_hierarchy_context()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    parent_site_id uuid;
    period_site_id uuid;
    unit_site_id uuid;
BEGIN
    IF TG_TABLE_NAME = 'stratigraphic_unit'
       AND NEW.occupational_period_id IS NOT NULL THEN
        SELECT site_id INTO period_site_id
        FROM occupational_period
        WHERE id = NEW.occupational_period_id;
        IF period_site_id IS DISTINCT FROM NEW.site_id THEN
            RAISE EXCEPTION
                'Stratigraphic unit and occupational period must belong to the same site'
                USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME IN ('find', 'feature') THEN
        IF NEW.occupational_period_id IS NOT NULL THEN
            SELECT site_id INTO period_site_id
            FROM occupational_period
            WHERE id = NEW.occupational_period_id;
            IF period_site_id IS DISTINCT FROM NEW.site_id THEN
                RAISE EXCEPTION
                    'Record and occupational period must belong to the same site'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
        IF NEW.stratigraphic_unit_id IS NOT NULL THEN
            SELECT site_id INTO unit_site_id
            FROM stratigraphic_unit
            WHERE id = NEW.stratigraphic_unit_id;
            IF unit_site_id IS DISTINCT FROM NEW.site_id THEN
                RAISE EXCEPTION
                    'Record and stratigraphic unit must belong to the same site'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS stratigraphic_unit_context_check ON stratigraphic_unit;
CREATE TRIGGER stratigraphic_unit_context_check
BEFORE INSERT OR UPDATE ON stratigraphic_unit
FOR EACH ROW EXECUTE FUNCTION validate_site_hierarchy_context();

DROP TRIGGER IF EXISTS find_context_check ON find;
CREATE TRIGGER find_context_check
BEFORE INSERT OR UPDATE ON find
FOR EACH ROW EXECUTE FUNCTION validate_site_hierarchy_context();

DROP TRIGGER IF EXISTS feature_context_check ON feature;
CREATE TRIGGER feature_context_check
BEFORE INSERT OR UPDATE ON feature
FOR EACH ROW EXECUTE FUNCTION validate_site_hierarchy_context();

CREATE OR REPLACE FUNCTION validate_find_provenance()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    chain_subject_type text;
    chain_subject_id uuid;
BEGIN
    SELECT subject_type, subject_id
    INTO chain_subject_type, chain_subject_id
    FROM provenance_chain
    WHERE id = NEW.provenance_chain_id;

    IF chain_subject_type IS DISTINCT FROM 'find'
       OR chain_subject_id IS DISTINCT FROM NEW.id THEN
        RAISE EXCEPTION
            'Find provenance chain subject type and UUID must match this Find'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS find_provenance_check ON find;
CREATE TRIGGER find_provenance_check
BEFORE INSERT OR UPDATE ON find
FOR EACH ROW EXECUTE FUNCTION validate_find_provenance();

CREATE TABLE IF NOT EXISTS site_bibliography (
    site_id uuid NOT NULL REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (site_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS site_bibliography_reference_idx
    ON site_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS occupational_period_bibliography (
    occupational_period_id uuid NOT NULL
        REFERENCES occupational_period (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (occupational_period_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS occupational_period_bibliography_reference_idx
    ON occupational_period_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS stratigraphic_unit_bibliography (
    stratigraphic_unit_id uuid NOT NULL
        REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (stratigraphic_unit_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS stratigraphic_unit_bibliography_reference_idx
    ON stratigraphic_unit_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS find_bibliography (
    find_id uuid NOT NULL REFERENCES find (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (find_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS find_bibliography_reference_idx
    ON find_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS feature_bibliography (
    feature_id uuid NOT NULL REFERENCES feature (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (feature_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS feature_bibliography_reference_idx
    ON feature_bibliography (bibliographic_reference_id);

CREATE OR REPLACE FUNCTION require_published_site_hierarchy_citation()
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
        WHEN 'site' THEN
            entity_table := 'site';
            bibliography_table := 'site_bibliography';
            foreign_key_column := 'site_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'site_bibliography' THEN
            entity_table := 'site';
            bibliography_table := 'site_bibliography';
            foreign_key_column := 'site_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.site_id, NEW.site_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.site_id];
            ELSE
                target_ids := ARRAY[NEW.site_id];
            END IF;
        WHEN 'occupational_period' THEN
            entity_table := 'occupational_period';
            bibliography_table := 'occupational_period_bibliography';
            foreign_key_column := 'occupational_period_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'occupational_period_bibliography' THEN
            entity_table := 'occupational_period';
            bibliography_table := 'occupational_period_bibliography';
            foreign_key_column := 'occupational_period_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.occupational_period_id, NEW.occupational_period_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.occupational_period_id];
            ELSE
                target_ids := ARRAY[NEW.occupational_period_id];
            END IF;
        WHEN 'stratigraphic_unit' THEN
            entity_table := 'stratigraphic_unit';
            bibliography_table := 'stratigraphic_unit_bibliography';
            foreign_key_column := 'stratigraphic_unit_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'stratigraphic_unit_bibliography' THEN
            entity_table := 'stratigraphic_unit';
            bibliography_table := 'stratigraphic_unit_bibliography';
            foreign_key_column := 'stratigraphic_unit_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.stratigraphic_unit_id, NEW.stratigraphic_unit_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.stratigraphic_unit_id];
            ELSE
                target_ids := ARRAY[NEW.stratigraphic_unit_id];
            END IF;
        WHEN 'find' THEN
            entity_table := 'find';
            bibliography_table := 'find_bibliography';
            foreign_key_column := 'find_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'find_bibliography' THEN
            entity_table := 'find';
            bibliography_table := 'find_bibliography';
            foreign_key_column := 'find_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.find_id, NEW.find_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.find_id];
            ELSE
                target_ids := ARRAY[NEW.find_id];
            END IF;
        WHEN 'feature' THEN
            entity_table := 'feature';
            bibliography_table := 'feature_bibliography';
            foreign_key_column := 'feature_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'feature_bibliography' THEN
            entity_table := 'feature';
            bibliography_table := 'feature_bibliography';
            foreign_key_column := 'feature_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.feature_id, NEW.feature_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.feature_id];
            ELSE
                target_ids := ARRAY[NEW.feature_id];
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
                    'Published site-hierarchy record % in % requires at least one bibliographic reference',
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
    FOREACH entity_table IN ARRAY ARRAY[
        'site',
        'occupational_period',
        'stratigraphic_unit',
        'find',
        'feature'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_requires_citation ON %I',
            entity_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_requires_citation
             AFTER INSERT OR UPDATE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_site_hierarchy_citation()',
            entity_table
        );
    END LOOP;

    FOREACH bibliography_table IN ARRAY ARRAY[
        'site_bibliography',
        'occupational_period_bibliography',
        'stratigraphic_unit_bibliography',
        'find_bibliography',
        'feature_bibliography'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_citation_required ON %I',
            bibliography_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_citation_required
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_site_hierarchy_citation()',
            bibliography_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_site_hierarchy_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS site_set_updated_at ON site;
CREATE TRIGGER site_set_updated_at
BEFORE UPDATE ON site
FOR EACH ROW EXECUTE FUNCTION set_site_hierarchy_updated_at();

DROP TRIGGER IF EXISTS occupational_period_set_updated_at ON occupational_period;
CREATE TRIGGER occupational_period_set_updated_at
BEFORE UPDATE ON occupational_period
FOR EACH ROW EXECUTE FUNCTION set_site_hierarchy_updated_at();

DROP TRIGGER IF EXISTS stratigraphic_unit_set_updated_at ON stratigraphic_unit;
CREATE TRIGGER stratigraphic_unit_set_updated_at
BEFORE UPDATE ON stratigraphic_unit
FOR EACH ROW EXECUTE FUNCTION set_site_hierarchy_updated_at();

DROP TRIGGER IF EXISTS find_set_updated_at ON find;
CREATE TRIGGER find_set_updated_at
BEFORE UPDATE ON find
FOR EACH ROW EXECUTE FUNCTION set_site_hierarchy_updated_at();

DROP TRIGGER IF EXISTS feature_set_updated_at ON feature;
CREATE TRIGGER feature_set_updated_at
BEFORE UPDATE ON feature
FOR EACH ROW EXECUTE FUNCTION set_site_hierarchy_updated_at();

DO $$
DECLARE
    foreign_key record;
BEGIN
    FOR foreign_key IN
        SELECT *
        FROM (
            VALUES
                ('civilization_capital_city', 'civilization_capital_city_site_fk',
                 'FOREIGN KEY (site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('historical_person_find', 'historical_person_find_find_fk',
                 'FOREIGN KEY (find_id) REFERENCES find (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('bio_sample', 'bio_sample_site_fk',
                 'FOREIGN KEY (site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('bio_sample', 'bio_sample_stratigraphic_unit_fk',
                 'FOREIGN KEY (stratigraphic_unit_id) REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('chronometric_sample', 'chronometric_sample_stratigraphic_unit_fk',
                 'FOREIGN KEY (stratigraphic_unit_id) REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('provenance_chain', 'provenance_chain_stratigraphic_unit_fk',
                 'FOREIGN KEY (stratigraphic_unit_id) REFERENCES stratigraphic_unit (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('regional_chronicle_site', 'regional_chronicle_site_site_fk',
                 'FOREIGN KEY (site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('cluster_history_site', 'cluster_history_site_site_fk',
                 'FOREIGN KEY (site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('site_history', 'site_history_site_fk',
                 'FOREIGN KEY (site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('conservation_log', 'conservation_log_find_fk',
                 'FOREIGN KEY (find_id) REFERENCES find (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('movement_vector', 'movement_vector_origin_site_fk',
                 'FOREIGN KEY (origin_site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('movement_vector', 'movement_vector_destination_site_fk',
                 'FOREIGN KEY (destination_site_id) REFERENCES site (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('liturgical_event', 'liturgical_event_temple_feature_fk',
                 'FOREIGN KEY (associated_temple_feature_id) REFERENCES feature (id) ON UPDATE RESTRICT ON DELETE RESTRICT'),
                ('liturgical_event', 'liturgical_event_geo_alignment_fk',
                 'FOREIGN KEY (astronomical_alignment_geo_feature_id) REFERENCES geo_feature_temporal (id) ON UPDATE RESTRICT ON DELETE RESTRICT')
        ) AS definitions (table_name, constraint_name, constraint_definition)
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = to_regclass(foreign_key.table_name)
              AND conname = foreign_key.constraint_name
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I %s',
                foreign_key.table_name,
                foreign_key.constraint_name,
                foreign_key.constraint_definition
            );
        END IF;
    END LOOP;
END;
$$;

CREATE OR REPLACE VIEW site_hierarchy_site_metrics AS
SELECT
    site.id AS site_id,
    count(DISTINCT occupational_period.id) AS occupational_period_count,
    count(DISTINCT stratigraphic_unit.id) AS stratigraphic_unit_count,
    count(DISTINCT find.id) AS find_count,
    count(DISTINCT feature.id) AS feature_count
FROM site
LEFT JOIN occupational_period ON occupational_period.site_id = site.id
LEFT JOIN stratigraphic_unit ON stratigraphic_unit.site_id = site.id
LEFT JOIN find ON find.site_id = site.id
LEFT JOIN feature ON feature.site_id = site.id
GROUP BY site.id;
