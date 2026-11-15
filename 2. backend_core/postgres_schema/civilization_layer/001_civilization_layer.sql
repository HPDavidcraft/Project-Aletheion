CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS civilization_complex (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    time_span_edtf text NOT NULL CHECK (length(btrim(time_span_edtf)) > 0),
    body_text text NOT NULL CHECK (length(btrim(body_text)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS civilization_complex_name_idx
    ON civilization_complex (name);
CREATE INDEX IF NOT EXISTS civilization_complex_time_span_idx
    ON civilization_complex (time_span_edtf);

COMMENT ON TABLE civilization_complex IS
    'Civilizational container with continuity across one or more political phases.';
COMMENT ON COLUMN civilization_complex.time_span_edtf IS
    'Canonical EDTF time span; validate on write in the API.';

CREATE TABLE IF NOT EXISTS polity_phase (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    civilization_complex_id uuid NOT NULL
        REFERENCES civilization_complex (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    time_span_edtf text NOT NULL CHECK (length(btrim(time_span_edtf)) > 0),
    territorial_extent geography(MultiPolygon, 4326) NOT NULL,
    display_order integer NOT NULL DEFAULT 0,
    paleo_climate_model_id uuid,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT polity_phase_geometry_check
        CHECK (
            NOT ST_IsEmpty(territorial_extent::geometry)
            AND ST_IsValid(territorial_extent::geometry)
            AND ST_Area(territorial_extent) > 0
        ),
    UNIQUE (civilization_complex_id, name)
);

CREATE INDEX IF NOT EXISTS polity_phase_civilization_order_idx
    ON polity_phase (civilization_complex_id, display_order);
CREATE INDEX IF NOT EXISTS polity_phase_time_span_idx
    ON polity_phase (time_span_edtf);
CREATE INDEX IF NOT EXISTS polity_phase_extent_gix
    ON polity_phase USING gist (territorial_extent);

COMMENT ON TABLE polity_phase IS
    'Discrete political configuration in a civilization, with a WGS 84 multipolygon for time-scrubbed map display.';
COMMENT ON COLUMN polity_phase.time_span_edtf IS
    'Canonical EDTF time span; validate temporal ordering and syntax in the API.';
COMMENT ON COLUMN polity_phase.paleo_climate_model_id IS
    'UUID reference to a paleoclimate model; add the foreign key when that domain schema exists.';

CREATE TABLE IF NOT EXISTS historical_person (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    preferred_name text NOT NULL CHECK (length(btrim(preferred_name)) > 0),
    alternate_names jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(alternate_names) = 'array'),
    birth_date_edtf text CHECK (
        birth_date_edtf IS NULL OR length(btrim(birth_date_edtf)) > 0
    ),
    death_date_edtf text CHECK (
        death_date_edtf IS NULL OR length(btrim(death_date_edtf)) > 0
    ),
    role_uri text NOT NULL CHECK (role_uri ~ '^https?://'),
    biography text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS historical_person_name_idx
    ON historical_person (preferred_name);
CREATE INDEX IF NOT EXISTS historical_person_role_idx
    ON historical_person (role_uri);

COMMENT ON TABLE historical_person IS
    'Documented individual with EDTF dates and a role from a governed SKOS vocabulary.';
COMMENT ON COLUMN historical_person.role_uri IS
    'URI of an approved SKOS concept; vocabulary membership is validated by the application.';
COMMENT ON COLUMN historical_person.birth_date_edtf IS
    'Canonical EDTF date; syntax and birth/death consistency are validated by the API.';

CREATE TABLE IF NOT EXISTS civilization_ruler (
    civilization_complex_id uuid NOT NULL
        REFERENCES civilization_complex (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    historical_person_id uuid NOT NULL
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    list_position integer NOT NULL CHECK (list_position >= 0),
    reign_date_range_edtf text NOT NULL
        CHECK (length(btrim(reign_date_range_edtf)) > 0),
    notes text,
    PRIMARY KEY (civilization_complex_id, historical_person_id, list_position),
    UNIQUE (civilization_complex_id, list_position)
);

CREATE INDEX IF NOT EXISTS civilization_ruler_person_idx
    ON civilization_ruler (historical_person_id);

COMMENT ON TABLE civilization_ruler IS
    'Ordered ruler list for a civilization; reign dates are EDTF expressions.';

CREATE TABLE IF NOT EXISTS civilization_capital_city (
    civilization_complex_id uuid NOT NULL
        REFERENCES civilization_complex (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    site_id uuid NOT NULL,
    validity_date_range_edtf text NOT NULL
        CHECK (length(btrim(validity_date_range_edtf)) > 0),
    display_name text,
    notes text,
    PRIMARY KEY (civilization_complex_id, site_id, validity_date_range_edtf)
);

CREATE INDEX IF NOT EXISTS civilization_capital_site_idx
    ON civilization_capital_city (site_id);

COMMENT ON TABLE civilization_capital_city IS
    'Capital Site UUIDs with EDTF validity ranges; the Site foreign key is deferred until the site-hierarchy schema exists.';

CREATE TABLE IF NOT EXISTS civilization_bibliography (
    civilization_complex_id uuid NOT NULL
        REFERENCES civilization_complex (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (civilization_complex_id, bibliographic_reference_id, citation_type),
    CONSTRAINT civilization_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS civilization_bibliography_reference_idx
    ON civilization_bibliography (bibliographic_reference_id);

COMMENT ON TABLE civilization_bibliography IS
    'Bibliographic anchors; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS historical_person_event (
    historical_person_id uuid NOT NULL
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    historical_event_id uuid NOT NULL,
    relationship_type_uri text NOT NULL CHECK (relationship_type_uri ~ '^https?://'),
    notes text,
    PRIMARY KEY (historical_person_id, historical_event_id, relationship_type_uri)
);

CREATE INDEX IF NOT EXISTS historical_person_event_event_idx
    ON historical_person_event (historical_event_id);

COMMENT ON TABLE historical_person_event IS
    'Typed links to Historical_Event records; the event foreign key is deferred until the historiographical schema exists.';

CREATE TABLE IF NOT EXISTS historical_person_expedition_vector (
    historical_person_id uuid NOT NULL
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    movement_vector_id uuid NOT NULL,
    relationship_type_uri text NOT NULL CHECK (relationship_type_uri ~ '^https?://'),
    notes text,
    PRIMARY KEY (historical_person_id, movement_vector_id, relationship_type_uri)
);

CREATE INDEX IF NOT EXISTS historical_person_expedition_vector_vector_idx
    ON historical_person_expedition_vector (movement_vector_id);

COMMENT ON TABLE historical_person_expedition_vector IS
    'Links people to expedition Movement_Vector records; the vector foreign key is deferred until the 4D-GIS schema is installed.';

CREATE TABLE IF NOT EXISTS historical_person_battle (
    historical_person_id uuid NOT NULL
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    battle_id uuid NOT NULL,
    relationship_type_uri text NOT NULL CHECK (relationship_type_uri ~ '^https?://'),
    notes text,
    PRIMARY KEY (historical_person_id, battle_id, relationship_type_uri)
);

CREATE INDEX IF NOT EXISTS historical_person_battle_battle_idx
    ON historical_person_battle (battle_id);

COMMENT ON TABLE historical_person_battle IS
    'Links people to Battle records; the battle foreign key is deferred until that module is modeled.';

CREATE TABLE IF NOT EXISTS historical_person_text_witness (
    historical_person_id uuid NOT NULL
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    text_witness_id uuid NOT NULL,
    relationship_type_uri text NOT NULL CHECK (relationship_type_uri ~ '^https?://'),
    notes text,
    PRIMARY KEY (historical_person_id, text_witness_id, relationship_type_uri)
);

CREATE INDEX IF NOT EXISTS historical_person_text_witness_witness_idx
    ON historical_person_text_witness (text_witness_id);

COMMENT ON TABLE historical_person_text_witness IS
    'Links people to primary Text_Witness records; the witness foreign key is deferred until the source-critical schema exists.';

CREATE TABLE IF NOT EXISTS historical_person_find (
    historical_person_id uuid NOT NULL
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    find_id uuid NOT NULL,
    relationship_type_uri text NOT NULL CHECK (relationship_type_uri ~ '^https?://'),
    notes text,
    PRIMARY KEY (historical_person_id, find_id, relationship_type_uri)
);

CREATE INDEX IF NOT EXISTS historical_person_find_find_idx
    ON historical_person_find (find_id);

COMMENT ON TABLE historical_person_find IS
    'Dedicated association from a person to findable material culture; the Find foreign key is deferred until the site-hierarchy schema exists.';

CREATE OR REPLACE FUNCTION set_civilization_layer_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS civilization_complex_set_updated_at ON civilization_complex;
CREATE TRIGGER civilization_complex_set_updated_at
BEFORE UPDATE ON civilization_complex
FOR EACH ROW EXECUTE FUNCTION set_civilization_layer_updated_at();

DROP TRIGGER IF EXISTS polity_phase_set_updated_at ON polity_phase;
CREATE TRIGGER polity_phase_set_updated_at
BEFORE UPDATE ON polity_phase
FOR EACH ROW EXECUTE FUNCTION set_civilization_layer_updated_at();

DROP TRIGGER IF EXISTS historical_person_set_updated_at ON historical_person;
CREATE TRIGGER historical_person_set_updated_at
BEFORE UPDATE ON historical_person
FOR EACH ROW EXECUTE FUNCTION set_civilization_layer_updated_at();
