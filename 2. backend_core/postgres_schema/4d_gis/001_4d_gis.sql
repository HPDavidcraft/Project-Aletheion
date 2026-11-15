CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS geo_feature_temporal (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    geometry geography(Geometry, 4326) NOT NULL,
    feature_type_uri text NOT NULL
        CHECK (feature_type_uri ~ '^https?://'),
    valid_time_range tsrange NOT NULL
        CHECK (NOT isempty(valid_time_range)),
    ancient_name text,
    modern_name text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT geo_feature_temporal_geometry_type_check
        CHECK (ST_GeometryType(geometry::geometry) IN ('ST_LineString', 'ST_Polygon')),
    CONSTRAINT geo_feature_temporal_geometry_valid_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_IsValid(geometry::geometry)
            AND (
                (ST_GeometryType(geometry::geometry) = 'ST_LineString' AND ST_Length(geometry) > 0)
                OR (ST_GeometryType(geometry::geometry) = 'ST_Polygon' AND ST_Area(geometry) > 0)
            )
        )
);

CREATE INDEX IF NOT EXISTS geo_feature_temporal_geometry_gix
    ON geo_feature_temporal USING gist (geometry);
CREATE INDEX IF NOT EXISTS geo_feature_temporal_time_range_gix
    ON geo_feature_temporal USING gist (valid_time_range);
CREATE INDEX IF NOT EXISTS geo_feature_temporal_feature_type_idx
    ON geo_feature_temporal (feature_type_uri);

COMMENT ON TABLE geo_feature_temporal IS
    'Time-varying geographic features. EDTF-to-tsrange resolution is performed by the application before persistence.';
COMMENT ON COLUMN geo_feature_temporal.feature_type_uri IS
    'URI of an approved SKOS concept; validate concept membership through the vocabulary service.';
COMMENT ON COLUMN geo_feature_temporal.valid_time_range IS
    'PostgreSQL timestamp range used for temporal overlap queries; timestamps are stored without time-zone offsets.';

CREATE TABLE IF NOT EXISTS resource_node (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    geometry geography(Geometry, 4326) NOT NULL,
    resource_type_uri text NOT NULL
        CHECK (resource_type_uri ~ '^https?://'),
    active_dates_edtf text NOT NULL
        CHECK (length(btrim(active_dates_edtf)) > 0),
    description text,
    iconography_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT resource_node_geometry_type_check
        CHECK (
            ST_GeometryType(geometry::geometry) IN (
                'ST_Point',
                'ST_MultiPoint',
                'ST_Polygon',
                'ST_MultiPolygon'
            )
        ),
    CONSTRAINT resource_node_geometry_valid_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_IsValid(geometry::geometry)
            AND (
                ST_GeometryType(geometry::geometry) IN ('ST_Point', 'ST_MultiPoint')
                OR ST_Area(geometry) > 0
            )
        )
);

CREATE INDEX IF NOT EXISTS resource_node_geometry_gix
    ON resource_node USING gist (geometry);
CREATE INDEX IF NOT EXISTS resource_node_resource_type_idx
    ON resource_node (resource_type_uri);

COMMENT ON TABLE resource_node IS
    'Documented natural-resource source, such as a quarry, ore deposit, agricultural zone, fishery, or timber area.';
COMMENT ON COLUMN resource_node.resource_type_uri IS
    'URI of an approved SKOS concept; validate concept membership through the vocabulary service.';
COMMENT ON COLUMN resource_node.active_dates_edtf IS
    'EDTF range validated by the API before persistence.';

CREATE TABLE IF NOT EXISTS resource_node_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_node_id uuid NOT NULL
        REFERENCES resource_node (id) ON DELETE RESTRICT,
    evidence_entity_type text NOT NULL
        CHECK (length(btrim(evidence_entity_type)) > 0),
    evidence_entity_id uuid NOT NULL,
    relationship_type_uri text NOT NULL
        CHECK (relationship_type_uri ~ '^https?://'),
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (
        resource_node_id,
        evidence_entity_type,
        evidence_entity_id,
        relationship_type_uri
    )
);

CREATE INDEX IF NOT EXISTS resource_node_evidence_entity_idx
    ON resource_node_evidence (evidence_entity_type, evidence_entity_id);
CREATE INDEX IF NOT EXISTS resource_node_evidence_relation_idx
    ON resource_node_evidence (relationship_type_uri);

COMMENT ON TABLE resource_node_evidence IS
    'Typed extraction or iconographic evidence links. The referenced entity UUID belongs to another Pleroma domain table.';
COMMENT ON COLUMN resource_node_evidence.relationship_type_uri IS
    'URI of an approved SKOS concept describing the evidence relationship.';

CREATE TABLE IF NOT EXISTS movement_vector (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    geometry geography(LineString, 4326) NOT NULL,
    movement_category_uri text NOT NULL
        CHECK (movement_category_uri ~ '^https?://'),
    route_source text NOT NULL
        CHECK (route_source IN ('documented', 'inferred', 'LCP_computed')),
    valid_time_range tsrange
        CHECK (valid_time_range IS NULL OR NOT isempty(valid_time_range)),
    origin_site_id uuid,
    destination_site_id uuid,
    subtype_attributes jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(subtype_attributes) = 'object'),
    lcp_energy_model text
        CHECK (lcp_energy_model IN ('tobler_hiking', 'pandolf_load_carrying')),
    dem_source_uri text,
    cost_surface_uri text,
    lcp_parameters jsonb
        CHECK (lcp_parameters IS NULL OR jsonb_typeof(lcp_parameters) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT movement_vector_geometry_valid_check
        CHECK (
            NOT ST_IsEmpty(geometry::geometry)
            AND ST_NPoints(geometry::geometry) >= 2
            AND ST_IsValid(geometry::geometry)
            AND ST_Length(geometry) > 0
        ),
    CONSTRAINT movement_vector_lcp_provenance_check
        CHECK (
            (
                route_source = 'LCP_computed'
                AND lcp_energy_model IS NOT NULL
                AND dem_source_uri IS NOT NULL
                AND cost_surface_uri IS NOT NULL
                AND lcp_parameters IS NOT NULL
            )
            OR (
                route_source <> 'LCP_computed'
                AND lcp_energy_model IS NULL
                AND dem_source_uri IS NULL
                AND cost_surface_uri IS NULL
                AND lcp_parameters IS NULL
            )
        ),
    CONSTRAINT movement_vector_lcp_uri_check
        CHECK (
            route_source <> 'LCP_computed'
            OR (
                dem_source_uri ~ '^https?://'
                AND cost_surface_uri ~ '^(https?|s3|minio)://'
            )
        )
);

CREATE INDEX IF NOT EXISTS movement_vector_geometry_gix
    ON movement_vector USING gist (geometry);
CREATE INDEX IF NOT EXISTS movement_vector_time_range_gix
    ON movement_vector USING gist (valid_time_range);
CREATE INDEX IF NOT EXISTS movement_vector_category_idx
    ON movement_vector (movement_category_uri);
CREATE INDEX IF NOT EXISTS movement_vector_origin_site_idx
    ON movement_vector (origin_site_id);
CREATE INDEX IF NOT EXISTS movement_vector_destination_site_idx
    ON movement_vector (destination_site_id);

COMMENT ON TABLE movement_vector IS
    'Directed movement path for trade, expedition, migration, raw-material flow, or environmental dispersal.';
COMMENT ON COLUMN movement_vector.geometry IS
    'Directed path as a WGS 84 LineString; coordinate order carries direction.';
COMMENT ON COLUMN movement_vector.movement_category_uri IS
    'URI of an approved SKOS movement-category concept.';
COMMENT ON COLUMN movement_vector.subtype_attributes IS
    'Category-specific properties such as commodities, volume estimates, leader, campaign outcome, population, or species.';
COMMENT ON COLUMN movement_vector.lcp_parameters IS
    'Reproducible GRASS GIS cost-path parameters; required for LCP_computed routes.';
COMMENT ON COLUMN movement_vector.origin_site_id IS
    'UUID reference to a Site in the site_hierarchy domain; add a foreign key when that schema is installed.';
COMMENT ON COLUMN movement_vector.destination_site_id IS
    'UUID reference to a Site in the site_hierarchy domain; add a foreign key when that schema is installed.';

CREATE OR REPLACE FUNCTION set_4d_gis_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS geo_feature_temporal_set_updated_at ON geo_feature_temporal;
CREATE TRIGGER geo_feature_temporal_set_updated_at
BEFORE UPDATE ON geo_feature_temporal
FOR EACH ROW EXECUTE FUNCTION set_4d_gis_updated_at();

DROP TRIGGER IF EXISTS resource_node_set_updated_at ON resource_node;
CREATE TRIGGER resource_node_set_updated_at
BEFORE UPDATE ON resource_node
FOR EACH ROW EXECUTE FUNCTION set_4d_gis_updated_at();

DROP TRIGGER IF EXISTS movement_vector_set_updated_at ON movement_vector;
CREATE TRIGGER movement_vector_set_updated_at
BEFORE UPDATE ON movement_vector
FOR EACH ROW EXECUTE FUNCTION set_4d_gis_updated_at();
