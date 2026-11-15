CREATE TABLE IF NOT EXISTS temporal_uncertainty_case (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_entity_type_uri text NOT NULL
        CHECK (subject_entity_type_uri ~ '^https?://'),
    subject_entity_id uuid NOT NULL,
    temporal_property_uri text NOT NULL
        CHECK (temporal_property_uri ~ '^https?://'),
    description text,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS temporal_uncertainty_case_subject_idx
    ON temporal_uncertainty_case
        (subject_entity_type_uri, subject_entity_id, temporal_property_uri);

COMMENT ON TABLE temporal_uncertainty_case IS
    'Groups competing or revised date assertions for one temporal property on a domain entity; cross-module subject resolution is enforced by the API.';
COMMENT ON COLUMN temporal_uncertainty_case.temporal_property_uri IS
    'URI identifying the date-bearing property of the subject entity.';

CREATE TABLE IF NOT EXISTS temporal_distribution_assertion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    temporal_uncertainty_case_id uuid NOT NULL
        REFERENCES temporal_uncertainty_case (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    version_number integer NOT NULL CHECK (version_number > 0),
    supersedes_assertion_id uuid
        REFERENCES temporal_distribution_assertion (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    date_edtf text NOT NULL CHECK (length(btrim(date_edtf)) > 0),
    year_bounds int4range NOT NULL CHECK (NOT isempty(year_bounds)),
    probability_distribution temporal_distribution,
    certainty_score numeric NOT NULL
        CHECK (certainty_score >= 0 AND certainty_score <= 1),
    interpretation_notes text,
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT temporal_distribution_assertion_version_unique
        UNIQUE (temporal_uncertainty_case_id, version_number),
    CONSTRAINT temporal_distribution_assertion_supersedes_unique
        UNIQUE (supersedes_assertion_id),
    CONSTRAINT temporal_distribution_assertion_not_self_superseding
        CHECK (supersedes_assertion_id IS NULL OR supersedes_assertion_id <> id),
    CONSTRAINT temporal_distribution_assertion_distribution_check
        CHECK (
            probability_distribution IS NULL
            OR is_valid_temporal_distribution(probability_distribution)
        )
);

CREATE INDEX IF NOT EXISTS temporal_distribution_assertion_case_idx
    ON temporal_distribution_assertion
        (temporal_uncertainty_case_id, version_number DESC);
CREATE INDEX IF NOT EXISTS temporal_distribution_assertion_year_bounds_gix
    ON temporal_distribution_assertion USING gist (year_bounds);
CREATE INDEX IF NOT EXISTS temporal_distribution_assertion_published_idx
    ON temporal_distribution_assertion
        (temporal_uncertainty_case_id, created_at DESC)
    WHERE publication_status = 'published';

COMMENT ON TABLE temporal_distribution_assertion IS
    'Versioned date assertion preserving canonical EDTF, normalized query bounds, optional non-uniform probability curve, and an independent certainty score.';
COMMENT ON COLUMN temporal_distribution_assertion.date_edtf IS
    'Canonical EDTF value; syntax and consistency with year_bounds are validated by the API.';
COMMENT ON COLUMN temporal_distribution_assertion.year_bounds IS
    'Normalized astronomical-year range for indexing; the API keeps it consistent with EDTF and any probability distribution.';
COMMENT ON COLUMN temporal_distribution_assertion.probability_distribution IS
    'Optional shared Temporal_Distribution composite; its ordered probability points are validated by is_valid_temporal_distribution.';
COMMENT ON COLUMN temporal_distribution_assertion.certainty_score IS
    'A qualified assertion-level score from 0 to 1, distinct from probability values at individual years.';

CREATE TABLE IF NOT EXISTS temporal_distribution_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    temporal_distribution_assertion_id uuid NOT NULL
        REFERENCES temporal_distribution_assertion (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    evidence_role text NOT NULL
        CHECK (evidence_role IN ('supporting', 'opposing')),
    chronometric_sample_id uuid
        REFERENCES chronometric_sample (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    calibration_result_id uuid
        REFERENCES calibration_result (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    text_witness_id uuid
        REFERENCES text_witness (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    bibliographic_reference_id uuid,
    evidence_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT temporal_distribution_evidence_target_check
        CHECK (num_nonnulls(
            chronometric_sample_id,
            calibration_result_id,
            text_witness_id,
            bibliographic_reference_id
        ) = 1)
);

CREATE INDEX IF NOT EXISTS temporal_distribution_evidence_assertion_idx
    ON temporal_distribution_evidence (temporal_distribution_assertion_id);
CREATE INDEX IF NOT EXISTS temporal_distribution_evidence_sample_idx
    ON temporal_distribution_evidence (chronometric_sample_id)
    WHERE chronometric_sample_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS temporal_distribution_evidence_result_idx
    ON temporal_distribution_evidence (calibration_result_id)
    WHERE calibration_result_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS temporal_distribution_evidence_witness_idx
    ON temporal_distribution_evidence (text_witness_id)
    WHERE text_witness_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS temporal_distribution_evidence_reference_idx
    ON temporal_distribution_evidence (bibliographic_reference_id)
    WHERE bibliographic_reference_id IS NOT NULL;

COMMENT ON TABLE temporal_distribution_evidence IS
    'Typed sources for date assertions; each row references exactly one chronometric sample, calibration result, textual witness, or bibliographic reference.';
COMMENT ON COLUMN temporal_distribution_evidence.bibliographic_reference_id IS
    'UUID reference to Bibliographic_Reference; the foreign key is deferred until the universal-entities schema exists.';

CREATE OR REPLACE FUNCTION validate_temporal_distribution_assertion_lineage()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    prior_case_id uuid;
    prior_version integer;
BEGIN
    IF TG_OP = 'UPDATE'
       AND ROW(
           NEW.temporal_uncertainty_case_id,
           NEW.version_number,
           NEW.supersedes_assertion_id
       ) IS DISTINCT FROM ROW(
           OLD.temporal_uncertainty_case_id,
           OLD.version_number,
           OLD.supersedes_assertion_id
       ) THEN
        RAISE EXCEPTION
            'Temporal assertion version identity and lineage are immutable; create a new assertion version'
            USING ERRCODE = '55000';
    END IF;

    IF NEW.supersedes_assertion_id IS NULL THEN
        IF NEW.version_number <> 1 THEN
            RAISE EXCEPTION
                'The first assertion in a temporal uncertainty case must have version number 1'
                USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;

    SELECT temporal_uncertainty_case_id, version_number
    INTO prior_case_id, prior_version
    FROM temporal_distribution_assertion
    WHERE id = NEW.supersedes_assertion_id;

    IF prior_case_id IS DISTINCT FROM NEW.temporal_uncertainty_case_id THEN
        RAISE EXCEPTION
            'A temporal assertion may only supersede an assertion in the same uncertainty case'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.version_number <> prior_version + 1 THEN
        RAISE EXCEPTION
            'A superseding temporal assertion must increment the prior version number by one'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS temporal_distribution_assertion_validate_lineage
    ON temporal_distribution_assertion;
CREATE TRIGGER temporal_distribution_assertion_validate_lineage
BEFORE INSERT OR UPDATE ON temporal_distribution_assertion
FOR EACH ROW EXECUTE FUNCTION validate_temporal_distribution_assertion_lineage();

CREATE OR REPLACE FUNCTION require_published_temporal_distribution_evidence()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    assertion_ids uuid[] := ARRAY[]::uuid[];
    assertion_id uuid;
    publication_state text;
BEGIN
    IF TG_TABLE_NAME = 'temporal_distribution_assertion' THEN
        IF TG_OP = 'UPDATE' THEN
            assertion_ids := array_append(assertion_ids, OLD.id);
        END IF;
        assertion_ids := array_append(assertion_ids, NEW.id);
    ELSE
        IF TG_OP IN ('UPDATE', 'DELETE') THEN
            assertion_ids := array_append(
                assertion_ids,
                OLD.temporal_distribution_assertion_id
            );
        END IF;
        IF TG_OP <> 'DELETE' THEN
            assertion_ids := array_append(
                assertion_ids,
                NEW.temporal_distribution_assertion_id
            );
        END IF;
    END IF;

    FOREACH assertion_id IN ARRAY assertion_ids LOOP
        SELECT publication_status
        INTO publication_state
        FROM temporal_distribution_assertion
        WHERE id = assertion_id;

        IF publication_state = 'published'
           AND NOT EXISTS (
               SELECT 1
               FROM temporal_distribution_evidence
               WHERE temporal_distribution_assertion_id = assertion_id
                 AND evidence_role = 'supporting'
           ) THEN
            RAISE EXCEPTION
                'Published temporal distribution assertion % requires at least one supporting evidence link',
                assertion_id
                USING ERRCODE = '23514';
        END IF;
    END LOOP;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS publication_requires_temporal_evidence
    ON temporal_distribution_assertion;
CREATE CONSTRAINT TRIGGER publication_requires_temporal_evidence
AFTER INSERT OR UPDATE ON temporal_distribution_assertion
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_published_temporal_distribution_evidence();

DROP TRIGGER IF EXISTS evidence_requires_published_temporal_support
    ON temporal_distribution_evidence;
CREATE CONSTRAINT TRIGGER evidence_requires_published_temporal_support
AFTER INSERT OR UPDATE OR DELETE ON temporal_distribution_evidence
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_published_temporal_distribution_evidence();

CREATE OR REPLACE VIEW temporal_distribution_probability_points AS
SELECT
    assertion.id AS temporal_distribution_assertion_id,
    assertion.temporal_uncertainty_case_id,
    (point.value ->> 0)::numeric AS year,
    (point.value ->> 1)::numeric AS probability,
    (point.value ->> 1)::numeric < 0.3 AS reduced_opacity
FROM temporal_distribution_assertion AS assertion
CROSS JOIN LATERAL jsonb_array_elements(
    (assertion.probability_distribution).probability_curve
) AS point(value)
WHERE assertion.probability_distribution IS NOT NULL;

COMMENT ON VIEW temporal_distribution_probability_points IS
    'One row per validated year/probability point; reduced_opacity flags probabilities below 0.3 for the time-slider rendering contract.';
