CREATE TABLE IF NOT EXISTS text_witness (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tradition_family_uri text NOT NULL
        CHECK (tradition_family_uri ~ '^https?://'),
    shelfmark text NOT NULL CHECK (length(btrim(shelfmark)) > 0),
    date_edtf text NOT NULL CHECK (length(btrim(date_edtf)) > 0),
    script_uri text NOT NULL CHECK (script_uri ~ '^https?://'),
    language_glottocode text NOT NULL
        CHECK (language_glottocode ~ '^[a-z0-9]{4,8}$'),
    variant_readings jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(variant_readings) = 'array'),
    interpolations jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(interpolations) = 'array'),
    manuscript_manifestation_uri text
        CHECK (
            manuscript_manifestation_uri IS NULL
            OR manuscript_manifestation_uri ~ '^https?://'
        ),
    media_gallery_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tradition_family_uri, shelfmark)
);

CREATE INDEX IF NOT EXISTS text_witness_tradition_idx
    ON text_witness (tradition_family_uri);
CREATE INDEX IF NOT EXISTS text_witness_language_idx
    ON text_witness (language_glottocode);
CREATE INDEX IF NOT EXISTS text_witness_variant_readings_gin
    ON text_witness USING gin (variant_readings);

COMMENT ON TABLE text_witness IS
    'A specific manuscript or epigraphic witness of a textual tradition, with structured variant readings and flagged interpolations.';
COMMENT ON COLUMN text_witness.tradition_family_uri IS
    'URI for an approved SKOS tradition-family concept; vocabulary membership is validated by the application.';
COMMENT ON COLUMN text_witness.date_edtf IS
    'Canonical EDTF date; validate syntax in the API.';
COMMENT ON COLUMN text_witness.script_uri IS
    'URI for an approved script concept; vocabulary membership is validated by the application.';
COMMENT ON COLUMN text_witness.language_glottocode IS
    'Glottolog language identifier; verify the code against the adopted Glottolog release.';
COMMENT ON COLUMN text_witness.variant_readings IS
    'JSON array of documented textual variants; validate each entry against the API payload schema.';
COMMENT ON COLUMN text_witness.interpolations IS
    'JSON array of passages flagged as possible interpolations; validate each entry against the API payload schema.';
COMMENT ON COLUMN text_witness.manuscript_manifestation_uri IS
    'Optional FRBRoo F4 Manifestation URI or project-resolvable identifier.';
COMMENT ON COLUMN text_witness.media_gallery_id IS
    'UUID reference to the required Media_Gallery; foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS text_witness_comparison (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    left_witness_id uuid NOT NULL
        REFERENCES text_witness (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    right_witness_id uuid NOT NULL
        REFERENCES text_witness (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'failed')),
    output_format text
        CHECK (output_format IS NULL OR output_format IN ('iiif_annotation', 'html')),
    output_uri text
        CHECK (output_uri IS NULL OR output_uri ~ '^https?://'),
    output_checksum_sha256 text
        CHECK (
            output_checksum_sha256 IS NULL
            OR output_checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'
        ),
    error_message text,
    requested_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CONSTRAINT text_witness_comparison_distinct_check
        CHECK (left_witness_id <> right_witness_id),
    CONSTRAINT text_witness_comparison_result_check CHECK (
        (status = 'completed'
            AND output_format IS NOT NULL
            AND output_uri IS NOT NULL
            AND output_checksum_sha256 IS NOT NULL
            AND completed_at IS NOT NULL
            AND error_message IS NULL)
        OR
        (status = 'failed'
            AND error_message IS NOT NULL
            AND length(btrim(error_message)) > 0
            AND output_format IS NULL
            AND output_uri IS NULL
            AND output_checksum_sha256 IS NULL
            AND completed_at IS NOT NULL)
        OR
        (status = 'pending'
            AND output_format IS NULL
            AND output_uri IS NULL
            AND output_checksum_sha256 IS NULL
            AND completed_at IS NULL
            AND error_message IS NULL)
    ),
    UNIQUE (left_witness_id, right_witness_id)
);

CREATE INDEX IF NOT EXISTS text_witness_comparison_right_idx
    ON text_witness_comparison (right_witness_id);
CREATE INDEX IF NOT EXISTS text_witness_comparison_status_idx
    ON text_witness_comparison (status);

COMMENT ON TABLE text_witness_comparison IS
    'Tracks a requested or completed comparison of two witnesses. Diff generation and IIIF annotation/HTML rendering are performed by the application.';
COMMENT ON COLUMN text_witness_comparison.output_uri IS
    'External IIIF annotation or HTML result pointer; binary comparison output is not stored in PostgreSQL.';

CREATE OR REPLACE FUNCTION validate_text_witness_comparison()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    left_tradition_uri text;
    right_tradition_uri text;
BEGIN
    SELECT tradition_family_uri
    INTO left_tradition_uri
    FROM text_witness
    WHERE id = NEW.left_witness_id;

    SELECT tradition_family_uri
    INTO right_tradition_uri
    FROM text_witness
    WHERE id = NEW.right_witness_id;

    IF left_tradition_uri IS DISTINCT FROM right_tradition_uri THEN
        RAISE EXCEPTION
            'Text witnesses may only be compared within the same tradition family'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS text_witness_comparison_same_tradition
    ON text_witness_comparison;
CREATE TRIGGER text_witness_comparison_same_tradition
BEFORE INSERT OR UPDATE ON text_witness_comparison
FOR EACH ROW EXECUTE FUNCTION validate_text_witness_comparison();

CREATE TABLE IF NOT EXISTS text_witness_bibliography (
    text_witness_id uuid NOT NULL
        REFERENCES text_witness (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    PRIMARY KEY (text_witness_id, bibliographic_reference_id, citation_type),
    CONSTRAINT text_witness_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS text_witness_bibliography_reference_idx
    ON text_witness_bibliography (bibliographic_reference_id);

COMMENT ON TABLE text_witness_bibliography IS
    'Bibliographic anchors for witness records; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS interpretation_hypothesis (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_entity_type_uri text NOT NULL
        CHECK (subject_entity_type_uri ~ '^https?://'),
    subject_entity_id uuid NOT NULL,
    proponent_historical_person_id uuid
        REFERENCES historical_person (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    modern_scholar_id uuid,
    argument text NOT NULL CHECK (length(btrim(argument)) > 0),
    conflict_resolution_tag text NOT NULL DEFAULT 'contested'
        CHECK (conflict_resolution_tag IN (
            'consensus',
            'minority',
            'contested',
            'superseded',
            'refuted'
        )),
    certainty_score numeric NOT NULL
        CHECK (certainty_score >= 0 AND certainty_score <= 1),
    publication_status text NOT NULL DEFAULT 'draft'
        CHECK (publication_status IN ('draft', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT interpretation_hypothesis_proponent_check
        CHECK (num_nonnulls(
            proponent_historical_person_id,
            modern_scholar_id
        ) = 1)
);

CREATE INDEX IF NOT EXISTS interpretation_hypothesis_subject_idx
    ON interpretation_hypothesis (subject_entity_type_uri, subject_entity_id);
CREATE INDEX IF NOT EXISTS interpretation_hypothesis_status_idx
    ON interpretation_hypothesis (conflict_resolution_tag);
CREATE INDEX IF NOT EXISTS interpretation_hypothesis_certainty_idx
    ON interpretation_hypothesis (certainty_score);

COMMENT ON TABLE interpretation_hypothesis IS
    'CRMinf-aligned scholarly interpretation kept distinct from its subject evidence; subject UUID resolution is enforced by the API because subjects span domain schemas.';
COMMENT ON COLUMN interpretation_hypothesis.subject_entity_type_uri IS
    'URI identifying the controlled entity class of the hypothesis subject.';
COMMENT ON COLUMN interpretation_hypothesis.modern_scholar_id IS
    'UUID of a modern scholar identity; the identity schema is not yet modeled, so existence and authorization are checked by the API.';
COMMENT ON COLUMN interpretation_hypothesis.certainty_score IS
    'Qualified scholarly certainty from 0 to 1; it is not an assertion that the interpretation is fact.';

CREATE TABLE IF NOT EXISTS interpretation_hypothesis_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id uuid NOT NULL
        REFERENCES interpretation_hypothesis (id)
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
    CONSTRAINT interpretation_hypothesis_evidence_target_check
        CHECK (num_nonnulls(find_id, feature_id, text_witness_id) = 1)
);

CREATE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_hypothesis_idx
    ON interpretation_hypothesis_evidence (hypothesis_id);
CREATE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_find_idx
    ON interpretation_hypothesis_evidence (find_id)
    WHERE find_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_feature_idx
    ON interpretation_hypothesis_evidence (feature_id)
    WHERE feature_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_witness_idx
    ON interpretation_hypothesis_evidence (text_witness_id)
    WHERE text_witness_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_find_unique
    ON interpretation_hypothesis_evidence
        (hypothesis_id, find_id, relationship_type_uri)
    WHERE find_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_feature_unique
    ON interpretation_hypothesis_evidence
        (hypothesis_id, feature_id, relationship_type_uri)
    WHERE feature_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS interpretation_hypothesis_evidence_witness_unique
    ON interpretation_hypothesis_evidence
        (hypothesis_id, text_witness_id, relationship_type_uri)
    WHERE text_witness_id IS NOT NULL;

COMMENT ON TABLE interpretation_hypothesis_evidence IS
    'Typed, referentially constrained evidence links to exactly one Find, Feature, or Text_Witness.';

CREATE TABLE IF NOT EXISTS interpretation_hypothesis_bibliography (
    hypothesis_id uuid NOT NULL
        REFERENCES interpretation_hypothesis (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    bibliographic_reference_id uuid NOT NULL,
    reference_stance text NOT NULL
        CHECK (reference_stance IN ('supporting', 'opposing')),
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
        hypothesis_id,
        bibliographic_reference_id,
        reference_stance,
        citation_type
    ),
    CONSTRAINT interpretation_hypothesis_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0)
);

CREATE INDEX IF NOT EXISTS interpretation_hypothesis_bibliography_reference_idx
    ON interpretation_hypothesis_bibliography (bibliographic_reference_id);
CREATE INDEX IF NOT EXISTS interpretation_hypothesis_bibliography_stance_idx
    ON interpretation_hypothesis_bibliography (hypothesis_id, reference_stance);

COMMENT ON TABLE interpretation_hypothesis_bibliography IS
    'Supporting and opposing citations; Bibliographic_Reference foreign key is deferred until the universal-entities schema exists.';

CREATE TABLE IF NOT EXISTS interpretation_hypothesis_opposition (
    hypothesis_id uuid NOT NULL
        REFERENCES interpretation_hypothesis (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    counter_hypothesis_id uuid NOT NULL
        REFERENCES interpretation_hypothesis (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    relationship_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (hypothesis_id, counter_hypothesis_id),
    CONSTRAINT interpretation_hypothesis_opposition_not_self_check
        CHECK (hypothesis_id <> counter_hypothesis_id)
);

CREATE INDEX IF NOT EXISTS interpretation_hypothesis_opposition_counter_idx
    ON interpretation_hypothesis_opposition (counter_hypothesis_id);

COMMENT ON TABLE interpretation_hypothesis_opposition IS
    'Directed links between counter-hypotheses; reciprocal records may be used when opposition is mutual.';

CREATE OR REPLACE FUNCTION require_published_hypothesis_support()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    hypothesis_ids uuid[] := ARRAY[]::uuid[];
    hypothesis_id uuid;
    publication_state text;
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'interpretation_hypothesis' THEN
            IF TG_OP = 'UPDATE' THEN
                hypothesis_ids := array_append(hypothesis_ids, OLD.id);
            END IF;
            hypothesis_ids := array_append(hypothesis_ids, NEW.id);
        WHEN 'interpretation_hypothesis_evidence' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                hypothesis_ids := array_append(
                    hypothesis_ids,
                    OLD.hypothesis_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                hypothesis_ids := array_append(
                    hypothesis_ids,
                    NEW.hypothesis_id
                );
            END IF;
        WHEN 'interpretation_hypothesis_bibliography' THEN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                hypothesis_ids := array_append(
                    hypothesis_ids,
                    OLD.hypothesis_id
                );
            END IF;
            IF TG_OP <> 'DELETE' THEN
                hypothesis_ids := array_append(
                    hypothesis_ids,
                    NEW.hypothesis_id
                );
            END IF;
    END CASE;

    FOREACH hypothesis_id IN ARRAY hypothesis_ids LOOP
        SELECT publication_status
        INTO publication_state
        FROM interpretation_hypothesis
        WHERE id = hypothesis_id;

        IF publication_state = 'published' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM interpretation_hypothesis_evidence
                WHERE interpretation_hypothesis_evidence.hypothesis_id =
                      hypothesis_id
            ) THEN
                RAISE EXCEPTION
                    'Published Interpretation_Hypothesis % requires at least one anchored Find, Feature, or Text_Witness evidence link',
                    hypothesis_id
                    USING ERRCODE = '23514';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM interpretation_hypothesis_bibliography
                WHERE interpretation_hypothesis_bibliography.hypothesis_id =
                      hypothesis_id
            ) THEN
                RAISE EXCEPTION
                    'Published Interpretation_Hypothesis % requires at least one supporting or opposing bibliographic reference',
                    hypothesis_id
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
    EXECUTE
        'DROP TRIGGER IF EXISTS publication_requires_hypothesis_support ON interpretation_hypothesis';
    EXECUTE
        'CREATE CONSTRAINT TRIGGER publication_requires_hypothesis_support
         AFTER INSERT OR UPDATE ON interpretation_hypothesis
         DEFERRABLE INITIALLY DEFERRED
         FOR EACH ROW EXECUTE FUNCTION require_published_hypothesis_support()';

    FOREACH relation_table IN ARRAY ARRAY[
        'interpretation_hypothesis_evidence',
        'interpretation_hypothesis_bibliography'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS relation_requires_hypothesis_support ON %I',
            relation_table
        );
        EXECUTE format(
            'CREATE CONSTRAINT TRIGGER relation_requires_hypothesis_support
             AFTER INSERT OR UPDATE OR DELETE ON %I
             DEFERRABLE INITIALLY DEFERRED
             FOR EACH ROW EXECUTE FUNCTION require_published_hypothesis_support()',
            relation_table
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION set_source_critical_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS text_witness_set_updated_at ON text_witness;
CREATE TRIGGER text_witness_set_updated_at
BEFORE UPDATE ON text_witness
FOR EACH ROW EXECUTE FUNCTION set_source_critical_updated_at();

DROP TRIGGER IF EXISTS interpretation_hypothesis_set_updated_at
    ON interpretation_hypothesis;
CREATE TRIGGER interpretation_hypothesis_set_updated_at
BEFORE UPDATE ON interpretation_hypothesis
FOR EACH ROW EXECUTE FUNCTION set_source_critical_updated_at();

CREATE OR REPLACE VIEW interpretation_hypothesis_debate_metrics AS
WITH citation_counts AS (
    SELECT
        hypothesis_id,
        count(DISTINCT bibliographic_reference_id) AS distinct_reference_count,
        count(DISTINCT bibliographic_reference_id)
            FILTER (WHERE reference_stance = 'supporting')
            AS supporting_reference_count,
        count(DISTINCT bibliographic_reference_id)
            FILTER (WHERE reference_stance = 'opposing')
            AS opposing_reference_count
    FROM interpretation_hypothesis_bibliography
    GROUP BY hypothesis_id
),
subject_proponents AS (
    SELECT
        subject_entity_type_uri,
        subject_entity_id,
        'historical_person'::text AS proponent_type,
        proponent_historical_person_id AS proponent_id
    FROM interpretation_hypothesis
    WHERE proponent_historical_person_id IS NOT NULL

    UNION

    SELECT
        subject_entity_type_uri,
        subject_entity_id,
        'modern_scholar'::text AS proponent_type,
        modern_scholar_id AS proponent_id
    FROM interpretation_hypothesis
    WHERE modern_scholar_id IS NOT NULL
),
subject_debate_counts AS (
    SELECT
        subject_entity_type_uri,
        subject_entity_id,
        count(DISTINCT (proponent_type, proponent_id)) AS subject_proponent_count
    FROM subject_proponents
    GROUP BY subject_entity_type_uri, subject_entity_id
)
SELECT
    hypothesis.id AS hypothesis_id,
    COALESCE(citation_counts.distinct_reference_count, 0)
        AS distinct_reference_count,
    COALESCE(citation_counts.supporting_reference_count, 0)
        AS supporting_reference_count,
    COALESCE(citation_counts.opposing_reference_count, 0)
        AS opposing_reference_count,
    subject_debate_counts.subject_proponent_count,
    count(DISTINCT opposition.counter_hypothesis_id)
        AS counter_hypothesis_count
FROM interpretation_hypothesis AS hypothesis
LEFT JOIN citation_counts
  ON citation_counts.hypothesis_id = hypothesis.id
JOIN subject_debate_counts
  ON subject_debate_counts.subject_entity_type_uri =
     hypothesis.subject_entity_type_uri
 AND subject_debate_counts.subject_entity_id = hypothesis.subject_entity_id
LEFT JOIN interpretation_hypothesis_opposition AS opposition
  ON opposition.hypothesis_id = hypothesis.id
GROUP BY
    hypothesis.id,
    citation_counts.distinct_reference_count,
    citation_counts.supporting_reference_count,
    citation_counts.opposing_reference_count,
    subject_debate_counts.subject_proponent_count;

COMMENT ON VIEW interpretation_hypothesis_debate_metrics IS
    'Per-hypothesis citations and counter-hypotheses plus distinct proponent identities across hypotheses about the same subject; an API-computed indicator must remain qualified.';
