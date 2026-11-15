CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS regional_chronicle (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    region_polygon geography(Polygon, 4326) NOT NULL,
    time_span_edtf text NOT NULL CHECK (length(btrim(time_span_edtf)) > 0),
    time_bounds int4range NOT NULL CHECK (NOT isempty(time_bounds)),
    general_survey text NOT NULL CHECK (length(btrim(general_survey)) > 0),
    geopolitical_context text NOT NULL
        CHECK (length(btrim(geopolitical_context)) > 0),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT regional_chronicle_polygon_check
        CHECK (
            NOT ST_IsEmpty(region_polygon::geometry)
            AND ST_IsValid(region_polygon::geometry)
            AND ST_Area(region_polygon) > 0
        )
);

CREATE INDEX IF NOT EXISTS regional_chronicle_polygon_gix
    ON regional_chronicle USING gist (region_polygon);
CREATE INDEX IF NOT EXISTS regional_chronicle_time_span_idx
    ON regional_chronicle (time_span_edtf);
CREATE INDEX IF NOT EXISTS regional_chronicle_time_bounds_gix
    ON regional_chronicle USING gist (time_bounds);
CREATE INDEX IF NOT EXISTS regional_chronicle_name_idx
    ON regional_chronicle (name);

COMMENT ON TABLE regional_chronicle IS
    'Geographically and temporally bounded regional survey with mandatory narrative, gallery, and bibliography links.';
COMMENT ON COLUMN regional_chronicle.time_bounds IS
    'Normalized astronomical-year range for overlap queries; the API keeps it consistent with the canonical EDTF value.';
COMMENT ON COLUMN regional_chronicle.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS regional_chronicle_site (
    regional_chronicle_id uuid NOT NULL
        REFERENCES regional_chronicle (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    site_id uuid NOT NULL,
    relationship_notes text,
    PRIMARY KEY (regional_chronicle_id, site_id)
);

CREATE INDEX IF NOT EXISTS regional_chronicle_site_site_idx
    ON regional_chronicle_site (site_id);

COMMENT ON TABLE regional_chronicle_site IS
    'Contained Site UUIDs; Site foreign key is deferred until the site-hierarchy schema exists.';

CREATE TABLE IF NOT EXISTS cluster_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    interaction_type text NOT NULL
        CHECK (interaction_type IN (
            'trade',
            'warfare',
            'migration',
            'cultural_diffusion',
            'environmental_co_response'
        )),
    interaction_analysis text NOT NULL
        CHECK (length(btrim(interaction_analysis)) > 0),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cluster_history_interaction_type_idx
    ON cluster_history (interaction_type);

CREATE TABLE IF NOT EXISTS cluster_history_site (
    cluster_history_id uuid NOT NULL
        REFERENCES cluster_history (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    site_id uuid NOT NULL,
    participation_notes text,
    PRIMARY KEY (cluster_history_id, site_id)
);

CREATE INDEX IF NOT EXISTS cluster_history_site_site_idx
    ON cluster_history_site (site_id);

COMMENT ON TABLE cluster_history_site IS
    'Normalized participating Site UUIDs used for graph traversal and spatial network analysis.';
COMMENT ON COLUMN cluster_history.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS cluster_history_media_asset (
    cluster_history_id uuid NOT NULL
        REFERENCES cluster_history (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    media_asset_id uuid NOT NULL,
    asset_role text NOT NULL DEFAULT 'network_graph'
        CHECK (asset_role IN ('network_graph', 'other')),
    PRIMARY KEY (cluster_history_id, media_asset_id)
);

COMMENT ON TABLE cluster_history_media_asset IS
    'Network graph and supporting Media_Asset UUIDs; binary media remains outside PostgreSQL.';

CREATE TABLE IF NOT EXISTS site_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id uuid NOT NULL UNIQUE,
    discovery_history text NOT NULL
        CHECK (length(btrim(discovery_history)) > 0),
    occupational_narrative text NOT NULL
        CHECK (length(btrim(occupational_narrative)) > 0),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    version_number integer NOT NULL DEFAULT 1 CHECK (version_number > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE site_history IS
    'One narrative history per Site. Version increments on every update; the immutable governance audit log preserves each prior state.';
COMMENT ON COLUMN site_history.site_id IS
    'Unique Site UUID; foreign key is deferred until the site-hierarchy schema exists.';
COMMENT ON COLUMN site_history.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS historical_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    event_date_edtf text NOT NULL CHECK (length(btrim(event_date_edtf)) > 0),
    event_year_bounds int4range NOT NULL
        CHECK (NOT isempty(event_year_bounds)),
    description text,
    interpretation text,
    analysis text,
    location geography(Geometry, 4326),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT historical_event_published_sections_check CHECK (
        publication_status <> 'published'
        OR (
            description IS NOT NULL
            AND
            length(btrim(description)) > 0
            AND interpretation IS NOT NULL
            AND length(btrim(interpretation)) > 0
            AND analysis IS NOT NULL
            AND length(btrim(analysis)) > 0
        )
    ),
    CONSTRAINT historical_event_location_check CHECK (
        location IS NULL
        OR (
            NOT ST_IsEmpty(location::geometry)
            AND ST_IsValid(location::geometry)
        )
    )
);

CREATE INDEX IF NOT EXISTS historical_event_date_idx
    ON historical_event (event_date_edtf);
CREATE INDEX IF NOT EXISTS historical_event_year_bounds_gix
    ON historical_event USING gist (event_year_bounds);
CREATE INDEX IF NOT EXISTS historical_event_location_gix
    ON historical_event USING gist (location)
    WHERE location IS NOT NULL;
CREATE INDEX IF NOT EXISTS historical_event_status_idx
    ON historical_event (publication_status);

COMMENT ON TABLE historical_event IS
    'Discrete datable occurrence, distinct from a continuous Occupational_Period.';
COMMENT ON COLUMN historical_event.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';
COMMENT ON COLUMN historical_event.event_date_edtf IS
    'Canonical EDTF date or range; syntax and temporal interpretation are validated by the API.';
COMMENT ON COLUMN historical_event.event_year_bounds IS
    'Normalized astronomical-year range for overlap queries; the API keeps it consistent with the canonical EDTF value.';

CREATE TABLE IF NOT EXISTS historical_event_regional_chronicle (
    historical_event_id uuid NOT NULL
        REFERENCES historical_event (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    regional_chronicle_id uuid NOT NULL
        REFERENCES regional_chronicle (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_notes text,
    PRIMARY KEY (historical_event_id, regional_chronicle_id)
);

CREATE INDEX IF NOT EXISTS historical_event_regional_chronicle_region_idx
    ON historical_event_regional_chronicle (regional_chronicle_id);

CREATE TABLE IF NOT EXISTS historical_event_cluster_history (
    historical_event_id uuid NOT NULL
        REFERENCES historical_event (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    cluster_history_id uuid NOT NULL
        REFERENCES cluster_history (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_notes text,
    PRIMARY KEY (historical_event_id, cluster_history_id)
);

CREATE INDEX IF NOT EXISTS historical_event_cluster_history_cluster_idx
    ON historical_event_cluster_history (cluster_history_id);

CREATE TABLE IF NOT EXISTS historical_event_site_history (
    historical_event_id uuid NOT NULL
        REFERENCES historical_event (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    site_history_id uuid NOT NULL
        REFERENCES site_history (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_notes text,
    PRIMARY KEY (historical_event_id, site_history_id)
);

CREATE INDEX IF NOT EXISTS historical_event_site_history_site_idx
    ON historical_event_site_history (site_history_id);

CREATE TABLE IF NOT EXISTS regional_chronicle_bibliography (
    regional_chronicle_id uuid NOT NULL
        REFERENCES regional_chronicle (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (regional_chronicle_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS regional_chronicle_bibliography_reference_idx
    ON regional_chronicle_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS cluster_history_bibliography (
    cluster_history_id uuid NOT NULL
        REFERENCES cluster_history (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (cluster_history_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS cluster_history_bibliography_reference_idx
    ON cluster_history_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS site_history_bibliography (
    site_history_id uuid NOT NULL
        REFERENCES site_history (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (site_history_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS site_history_bibliography_reference_idx
    ON site_history_bibliography (bibliographic_reference_id);

CREATE TABLE IF NOT EXISTS historical_event_bibliography (
    historical_event_id uuid NOT NULL
        REFERENCES historical_event (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (historical_event_id, bibliographic_reference_id, citation_type)
);

CREATE INDEX IF NOT EXISTS historical_event_bibliography_reference_idx
    ON historical_event_bibliography (bibliographic_reference_id);

COMMENT ON TABLE historical_event_bibliography IS
    'Bibliographic anchors; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE OR REPLACE FUNCTION require_published_historiographical_citation()
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
    has_sites boolean;
    has_network_graph boolean;
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'regional_chronicle' THEN
            entity_table := 'regional_chronicle';
            bibliography_table := 'regional_chronicle_bibliography';
            foreign_key_column := 'regional_chronicle_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'regional_chronicle_bibliography' THEN
            entity_table := 'regional_chronicle';
            bibliography_table := 'regional_chronicle_bibliography';
            foreign_key_column := 'regional_chronicle_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.regional_chronicle_id, NEW.regional_chronicle_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.regional_chronicle_id];
            ELSE
                target_ids := ARRAY[NEW.regional_chronicle_id];
            END IF;
        WHEN 'cluster_history' THEN
            entity_table := 'cluster_history';
            bibliography_table := 'cluster_history_bibliography';
            foreign_key_column := 'cluster_history_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'cluster_history_bibliography' THEN
            entity_table := 'cluster_history';
            bibliography_table := 'cluster_history_bibliography';
            foreign_key_column := 'cluster_history_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.cluster_history_id, NEW.cluster_history_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.cluster_history_id];
            ELSE
                target_ids := ARRAY[NEW.cluster_history_id];
            END IF;
        WHEN 'cluster_history_site' THEN
            entity_table := 'cluster_history';
            bibliography_table := 'cluster_history_bibliography';
            foreign_key_column := 'cluster_history_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.cluster_history_id, NEW.cluster_history_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.cluster_history_id];
            ELSE
                target_ids := ARRAY[NEW.cluster_history_id];
            END IF;
        WHEN 'cluster_history_media_asset' THEN
            entity_table := 'cluster_history';
            bibliography_table := 'cluster_history_bibliography';
            foreign_key_column := 'cluster_history_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.cluster_history_id, NEW.cluster_history_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.cluster_history_id];
            ELSE
                target_ids := ARRAY[NEW.cluster_history_id];
            END IF;
        WHEN 'site_history' THEN
            entity_table := 'site_history';
            bibliography_table := 'site_history_bibliography';
            foreign_key_column := 'site_history_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'site_history_bibliography' THEN
            entity_table := 'site_history';
            bibliography_table := 'site_history_bibliography';
            foreign_key_column := 'site_history_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.site_history_id, NEW.site_history_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.site_history_id];
            ELSE
                target_ids := ARRAY[NEW.site_history_id];
            END IF;
        WHEN 'historical_event' THEN
            entity_table := 'historical_event';
            bibliography_table := 'historical_event_bibliography';
            foreign_key_column := 'historical_event_id';
            target_ids := ARRAY[NEW.id];
        WHEN 'historical_event_bibliography' THEN
            entity_table := 'historical_event';
            bibliography_table := 'historical_event_bibliography';
            foreign_key_column := 'historical_event_id';
            IF TG_OP = 'UPDATE' THEN
                target_ids := ARRAY[OLD.historical_event_id, NEW.historical_event_id];
            ELSIF TG_OP = 'DELETE' THEN
                target_ids := ARRAY[OLD.historical_event_id];
            ELSE
                target_ids := ARRAY[NEW.historical_event_id];
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
            IF entity_table = 'cluster_history' THEN
                SELECT EXISTS (
                    SELECT 1
                    FROM cluster_history_site
                    WHERE cluster_history_id = target_id
                )
                INTO has_sites;
                SELECT EXISTS (
                    SELECT 1
                    FROM cluster_history_media_asset
                    WHERE cluster_history_id = target_id
                      AND asset_role = 'network_graph'
                )
                INTO has_network_graph;

                IF NOT has_sites OR NOT has_network_graph THEN
                    RAISE EXCEPTION
                        'A published Cluster_History requires participating sites and a network-graph Media_Asset'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            EXECUTE format(
                'SELECT EXISTS (SELECT 1 FROM %I WHERE %I = $1)',
                bibliography_table,
                foreign_key_column
            )
            INTO has_citation
            USING target_id;

            IF NOT has_citation THEN
                RAISE EXCEPTION
                    'Published historiographical record % in % requires at least one bibliographic reference',
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
    table_name text;
    citation_table text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'regional_chronicle',
        'cluster_history',
        'site_history',
        'historical_event'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_requires_citation ON %I',
            table_name
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_requires_citation
             AFTER INSERT OR UPDATE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_historiographical_citation()',
            table_name
        );
    END LOOP;

    FOREACH citation_table IN ARRAY ARRAY[
        'regional_chronicle_bibliography',
        'cluster_history_bibliography',
        'cluster_history_site',
        'cluster_history_media_asset',
        'site_history_bibliography',
        'historical_event_bibliography'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_citation_required ON %I',
            citation_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_citation_required
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_historiographical_citation()',
            citation_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_historiographical_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    IF TG_TABLE_NAME = 'site_history' THEN
        NEW.version_number = OLD.version_number + 1;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS regional_chronicle_set_updated_at ON regional_chronicle;
CREATE TRIGGER regional_chronicle_set_updated_at
BEFORE UPDATE ON regional_chronicle
FOR EACH ROW EXECUTE FUNCTION set_historiographical_updated_at();

DROP TRIGGER IF EXISTS cluster_history_set_updated_at ON cluster_history;
CREATE TRIGGER cluster_history_set_updated_at
BEFORE UPDATE ON cluster_history
FOR EACH ROW EXECUTE FUNCTION set_historiographical_updated_at();

DROP TRIGGER IF EXISTS site_history_set_updated_at ON site_history;
CREATE TRIGGER site_history_set_updated_at
BEFORE UPDATE ON site_history
FOR EACH ROW EXECUTE FUNCTION set_historiographical_updated_at();

DROP TRIGGER IF EXISTS historical_event_set_updated_at ON historical_event;
CREATE TRIGGER historical_event_set_updated_at
BEFORE UPDATE ON historical_event
FOR EACH ROW EXECUTE FUNCTION set_historiographical_updated_at();
