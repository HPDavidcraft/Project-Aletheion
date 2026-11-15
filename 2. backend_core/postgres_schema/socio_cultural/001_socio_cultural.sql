CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS cultural_profile (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    cultural_entity_type_uri text NOT NULL
        CHECK (cultural_entity_type_uri ~ '^https?://'),
    body_text text NOT NULL CHECK (length(btrim(body_text)) > 0),
    time_span_edtf text
        CHECK (time_span_edtf IS NULL OR length(btrim(time_span_edtf)) > 0),
    time_bounds int4range
        CHECK (time_bounds IS NULL OR NOT isempty(time_bounds)),
    geographic_extent geography(MultiPolygon, 4326),
    media_gallery_id uuid NOT NULL,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cultural_profile_time_pair_check
        CHECK ((time_span_edtf IS NULL) = (time_bounds IS NULL)),
    CONSTRAINT cultural_profile_extent_check
        CHECK (
            geographic_extent IS NULL
            OR (
                NOT ST_IsEmpty(geographic_extent::geometry)
                AND ST_IsValid(geographic_extent::geometry)
                AND ST_Area(geographic_extent) > 0
            )
        )
);

CREATE INDEX IF NOT EXISTS cultural_profile_name_idx
    ON cultural_profile (name);
CREATE INDEX IF NOT EXISTS cultural_profile_entity_type_idx
    ON cultural_profile (cultural_entity_type_uri);
CREATE INDEX IF NOT EXISTS cultural_profile_time_bounds_gix
    ON cultural_profile USING gist (time_bounds)
    WHERE time_bounds IS NOT NULL;
CREATE INDEX IF NOT EXISTS cultural_profile_extent_gix
    ON cultural_profile USING gist (geographic_extent)
    WHERE geographic_extent IS NOT NULL;

COMMENT ON TABLE cultural_profile IS
    'Synthetic, sourced account of a defined cultural entity, with optional temporal and spatial extent.';
COMMENT ON COLUMN cultural_profile.cultural_entity_type_uri IS
    'URI for an approved controlled-vocabulary concept; vocabulary membership is validated by the application.';
COMMENT ON COLUMN cultural_profile.time_span_edtf IS
    'Canonical EDTF time span; validate syntax and consistency with time_bounds in the API.';
COMMENT ON COLUMN cultural_profile.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS societal_aspect (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cultural_profile_id uuid NOT NULL
        REFERENCES cultural_profile (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    aspect_type_uri text NOT NULL CHECK (aspect_type_uri ~ '^https?://'),
    mechanism_description text NOT NULL
        CHECK (length(btrim(mechanism_description)) > 0),
    significance text NOT NULL CHECK (length(btrim(significance)) > 0),
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (cultural_profile_id, name)
);

CREATE INDEX IF NOT EXISTS societal_aspect_profile_idx
    ON societal_aspect (cultural_profile_id);
CREATE INDEX IF NOT EXISTS societal_aspect_type_idx
    ON societal_aspect (aspect_type_uri);

COMMENT ON TABLE societal_aspect IS
    'A discrete, evidenced facet of a Cultural_Profile, such as economy, kinship, warfare, art, or agriculture.';
COMMENT ON COLUMN societal_aspect.aspect_type_uri IS
    'URI for an approved controlled-vocabulary concept; vocabulary membership is validated by the application.';

CREATE TABLE IF NOT EXISTS societal_aspect_evidence_link (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    societal_aspect_id uuid NOT NULL
        REFERENCES societal_aspect (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_type_uri text NOT NULL
        CHECK (relationship_type_uri ~ '^https?://'),
    find_id uuid
        REFERENCES find (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    feature_id uuid
        REFERENCES feature (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    bio_sample_id uuid
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    evidence_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT societal_aspect_evidence_target_check
        CHECK (num_nonnulls(find_id, feature_id, bio_sample_id) = 1)
);

CREATE INDEX IF NOT EXISTS societal_aspect_evidence_aspect_idx
    ON societal_aspect_evidence_link (societal_aspect_id);
CREATE INDEX IF NOT EXISTS societal_aspect_evidence_find_idx
    ON societal_aspect_evidence_link (find_id)
    WHERE find_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS societal_aspect_evidence_feature_idx
    ON societal_aspect_evidence_link (feature_id)
    WHERE feature_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS societal_aspect_evidence_bio_sample_idx
    ON societal_aspect_evidence_link (bio_sample_id)
    WHERE bio_sample_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS societal_aspect_evidence_find_unique
    ON societal_aspect_evidence_link
        (societal_aspect_id, find_id, relationship_type_uri)
    WHERE find_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS societal_aspect_evidence_feature_unique
    ON societal_aspect_evidence_link
        (societal_aspect_id, feature_id, relationship_type_uri)
    WHERE feature_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS societal_aspect_evidence_bio_sample_unique
    ON societal_aspect_evidence_link
        (societal_aspect_id, bio_sample_id, relationship_type_uri)
    WHERE bio_sample_id IS NOT NULL;

COMMENT ON TABLE societal_aspect_evidence_link IS
    'Typed, referentially constrained evidence links to exactly one Find, Feature, or Bio_Sample.';
COMMENT ON COLUMN societal_aspect_evidence_link.relationship_type_uri IS
    'URI for an approved controlled-vocabulary relationship concept; vocabulary membership is validated by the application.';

CREATE TABLE IF NOT EXISTS cultural_profile_bibliography (
    cultural_profile_id uuid NOT NULL
        REFERENCES cultural_profile (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
        cultural_profile_id,
        bibliographic_reference_id,
        citation_type
    ),
    CONSTRAINT cultural_profile_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS cultural_profile_bibliography_reference_idx
    ON cultural_profile_bibliography (bibliographic_reference_id);

COMMENT ON TABLE cultural_profile_bibliography IS
    'Source citations for Cultural_Profile records; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS societal_aspect_bibliography (
    societal_aspect_id uuid NOT NULL
        REFERENCES societal_aspect (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
        societal_aspect_id,
        bibliographic_reference_id,
        citation_type
    ),
    CONSTRAINT societal_aspect_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS societal_aspect_bibliography_reference_idx
    ON societal_aspect_bibliography (bibliographic_reference_id);

COMMENT ON TABLE societal_aspect_bibliography IS
    'Source citations for Societal_Aspect interpretations; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE OR REPLACE FUNCTION require_socio_cultural_evidence_and_citations()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    profile_ids uuid[] := ARRAY[]::uuid[];
    aspect_ids uuid[] := ARRAY[]::uuid[];
    profile_id uuid;
    aspect_id uuid;
    parent_profile_id uuid;
    parent_status text;
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'cultural_profile' THEN
            IF TG_OP = 'UPDATE' THEN
                profile_ids := array_append(profile_ids, OLD.id);
            END IF;
            profile_ids := array_append(profile_ids, NEW.id);
        WHEN 'societal_aspect' THEN
            IF TG_OP = 'UPDATE' THEN
                aspect_ids := array_append(aspect_ids, OLD.id);
            END IF;
            aspect_ids := array_append(aspect_ids, NEW.id);
        WHEN 'cultural_profile_bibliography' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                profile_ids := array_append(
                    profile_ids,
                    OLD.cultural_profile_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                profile_ids := array_append(
                    profile_ids,
                    NEW.cultural_profile_id
                );
            END IF;
        WHEN 'societal_aspect_bibliography' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                aspect_ids := array_append(
                    aspect_ids,
                    OLD.societal_aspect_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                aspect_ids := array_append(
                    aspect_ids,
                    NEW.societal_aspect_id
                );
            END IF;
        WHEN 'societal_aspect_evidence_link' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                aspect_ids := array_append(
                    aspect_ids,
                    OLD.societal_aspect_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                aspect_ids := array_append(
                    aspect_ids,
                    NEW.societal_aspect_id
                );
            END IF;
    END CASE;

    FOREACH aspect_id IN ARRAY aspect_ids LOOP
        SELECT societal_aspect.cultural_profile_id
        INTO parent_profile_id
        FROM societal_aspect
        WHERE societal_aspect.id = aspect_id;

        IF parent_profile_id IS NOT NULL THEN
            profile_ids := array_append(profile_ids, parent_profile_id);
        END IF;
    END LOOP;

    FOREACH profile_id IN ARRAY profile_ids LOOP
        SELECT cultural_profile.publication_status
        INTO parent_status
        FROM cultural_profile
        WHERE cultural_profile.id = profile_id;

        IF parent_status = 'published' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM cultural_profile_bibliography
                WHERE cultural_profile_bibliography.cultural_profile_id = profile_id
            ) THEN
                RAISE EXCEPTION
                    'Published Cultural_Profile % requires at least one bibliographic reference',
                    profile_id
                    USING ERRCODE = '23514';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM societal_aspect
                JOIN societal_aspect_evidence_link
                  ON societal_aspect_evidence_link.societal_aspect_id =
                     societal_aspect.id
                WHERE societal_aspect.cultural_profile_id = profile_id
                  AND societal_aspect.publication_status = 'published'
            ) THEN
                RAISE EXCEPTION
                    'Published Cultural_Profile % requires at least one published Societal_Aspect with anchored evidence',
                    profile_id
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END LOOP;

    FOREACH aspect_id IN ARRAY aspect_ids LOOP
        SELECT societal_aspect.publication_status,
               societal_aspect.cultural_profile_id
        INTO parent_status, parent_profile_id
        FROM societal_aspect
        WHERE societal_aspect.id = aspect_id;

        IF parent_status = 'published' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM societal_aspect_evidence_link
                WHERE societal_aspect_evidence_link.societal_aspect_id = aspect_id
            ) THEN
                RAISE EXCEPTION
                    'Published Societal_Aspect % requires at least one typed evidence link',
                    aspect_id
                    USING ERRCODE = '23514';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM societal_aspect_bibliography
                WHERE societal_aspect_bibliography.societal_aspect_id = aspect_id
            ) THEN
                RAISE EXCEPTION
                    'Published Societal_Aspect % requires at least one bibliographic reference',
                    aspect_id
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
        'cultural_profile',
        'societal_aspect'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS publication_requires_socio_cultural_evidence ON %I',
            entity_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER publication_requires_socio_cultural_evidence
             AFTER INSERT OR UPDATE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_socio_cultural_evidence_and_citations()',
            entity_table
        );
    END LOOP;

    FOREACH relation_table IN ARRAY ARRAY[
        'cultural_profile_bibliography',
        'societal_aspect_bibliography',
        'societal_aspect_evidence_link'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS relation_requires_socio_cultural_evidence ON %I',
            relation_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER relation_requires_socio_cultural_evidence
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_socio_cultural_evidence_and_citations()',
            relation_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_socio_cultural_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS cultural_profile_set_updated_at ON cultural_profile;
CREATE TRIGGER cultural_profile_set_updated_at
BEFORE UPDATE ON cultural_profile
FOR EACH ROW EXECUTE FUNCTION set_socio_cultural_updated_at();

DROP TRIGGER IF EXISTS societal_aspect_set_updated_at ON societal_aspect;
CREATE TRIGGER societal_aspect_set_updated_at
BEFORE UPDATE ON societal_aspect
FOR EACH ROW EXECUTE FUNCTION set_socio_cultural_updated_at();

CREATE OR REPLACE VIEW socio_cultural_evidence_context AS
SELECT
    evidence.id AS evidence_link_id,
    aspect.id AS societal_aspect_id,
    aspect.cultural_profile_id,
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
FROM societal_aspect_evidence_link AS evidence
JOIN societal_aspect AS aspect
  ON aspect.id = evidence.societal_aspect_id
JOIN find ON find.id = evidence.find_id
LEFT JOIN stratigraphic_unit
  ON stratigraphic_unit.id = find.stratigraphic_unit_id
LEFT JOIN occupational_period
  ON occupational_period.id = find.occupational_period_id
WHERE evidence.find_id IS NOT NULL

UNION ALL

SELECT
    evidence.id AS evidence_link_id,
    aspect.id AS societal_aspect_id,
    aspect.cultural_profile_id,
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
FROM societal_aspect_evidence_link AS evidence
JOIN societal_aspect AS aspect
  ON aspect.id = evidence.societal_aspect_id
JOIN feature ON feature.id = evidence.feature_id
LEFT JOIN stratigraphic_unit
  ON stratigraphic_unit.id = feature.stratigraphic_unit_id
LEFT JOIN occupational_period
  ON occupational_period.id = feature.occupational_period_id
WHERE evidence.feature_id IS NOT NULL

UNION ALL

SELECT
    evidence.id AS evidence_link_id,
    aspect.id AS societal_aspect_id,
    aspect.cultural_profile_id,
    'bio_sample'::text AS evidence_entity_type,
    bio_sample.id AS evidence_entity_id,
    evidence.relationship_type_uri,
    bio_sample.site_id,
    COALESCE(
        stratigraphic_unit.geometry::geometry,
        site.boundary::geometry
    ) AS evidence_location,
    stratigraphic_unit.year_bounds AS evidence_year_bounds,
    stratigraphic_unit.date_range_edtf AS evidence_time_edtf
FROM societal_aspect_evidence_link AS evidence
JOIN societal_aspect AS aspect
  ON aspect.id = evidence.societal_aspect_id
JOIN bio_sample ON bio_sample.id = evidence.bio_sample_id
JOIN site ON site.id = bio_sample.site_id
LEFT JOIN stratigraphic_unit
  ON stratigraphic_unit.id = bio_sample.stratigraphic_unit_id
WHERE evidence.bio_sample_id IS NOT NULL;

COMMENT ON VIEW socio_cultural_evidence_context IS
    'Typed evidence report context with site, location, and available temporal bounds. Restrict access according to provenance and sensitive-sample policies; Trust Scores are supplied by the trust service.';
