CREATE TABLE IF NOT EXISTS bio_sample (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sample_type text NOT NULL
        CHECK (sample_type IN (
            'bio_sample',
            'human_sample',
            'flora_specimen',
            'fauna_specimen'
        )),
    site_id uuid NOT NULL,
    stratigraphic_unit_id uuid,
    surface_collection_context text,
    scientific_context text NOT NULL
        CHECK (length(btrim(scientific_context)) > 0),
    significance text NOT NULL CHECK (length(btrim(significance)) > 0),
    primary_lab_output_uri text NOT NULL
        CHECK (primary_lab_output_uri ~ '^(https?|s3|minio)://'),
    primary_lab_output_checksum_sha256 text NOT NULL
        CHECK (primary_lab_output_checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'),
    provenance_chain_id uuid NOT NULL UNIQUE
        REFERENCES provenance_chain (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT bio_sample_collection_context_check CHECK (
        stratigraphic_unit_id IS NOT NULL
        OR NULLIF(btrim(surface_collection_context), '') IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS bio_sample_site_idx
    ON bio_sample (site_id);
CREATE INDEX IF NOT EXISTS bio_sample_stratigraphic_unit_idx
    ON bio_sample (stratigraphic_unit_id)
    WHERE stratigraphic_unit_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS bio_sample_type_idx
    ON bio_sample (sample_type);

COMMENT ON TABLE bio_sample IS
    'Shared biological-sample record; all samples require scientific context, significance, site/context, and a linked custody chain.';
COMMENT ON COLUMN bio_sample.site_id IS
    'UUID reference to Site; foreign key is deferred until the site-hierarchy schema exists.';
COMMENT ON COLUMN bio_sample.stratigraphic_unit_id IS
    'UUID reference to Stratigraphic_Unit; foreign key is deferred until the site-hierarchy schema exists.';

CREATE OR REPLACE FUNCTION validate_bio_sample_provenance()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    chain_subject_type text;
    chain_subject_id uuid;
    chain_stratigraphic_unit_id uuid;
    chain_surface_context text;
BEGIN
    SELECT subject_type, subject_id, stratigraphic_unit_id, surface_collection_context
    INTO chain_subject_type, chain_subject_id,
         chain_stratigraphic_unit_id, chain_surface_context
    FROM provenance_chain
    WHERE id = NEW.provenance_chain_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'A biological sample requires an existing provenance chain'
            USING ERRCODE = '23503';
    END IF;

    IF chain_subject_type IS DISTINCT FROM NEW.sample_type
       OR chain_subject_id IS DISTINCT FROM NEW.id THEN
        RAISE EXCEPTION
            'The provenance chain subject type and UUID must match the biological sample'
            USING ERRCODE = '23514';
    END IF;

    IF chain_stratigraphic_unit_id IS DISTINCT FROM NEW.stratigraphic_unit_id
       OR NULLIF(btrim(chain_surface_context), '')
          IS DISTINCT FROM NULLIF(btrim(NEW.surface_collection_context), '') THEN
        RAISE EXCEPTION
            'The provenance chain collection context must match the biological sample'
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'UPDATE' AND NEW.sample_type IS DISTINCT FROM OLD.sample_type THEN
        RAISE EXCEPTION
            'A biological sample type is immutable; create the correct subtype record instead'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS bio_sample_validate_provenance ON bio_sample;
CREATE TRIGGER bio_sample_validate_provenance
BEFORE INSERT OR UPDATE ON bio_sample
FOR EACH ROW EXECUTE FUNCTION validate_bio_sample_provenance();

CREATE TABLE IF NOT EXISTS human_sample (
    bio_sample_id uuid PRIMARY KEY
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    nagpra_compliance_reviewed boolean NOT NULL DEFAULT false,
    nagpra_compliance_notes text,
    descendant_consultation_status text NOT NULL DEFAULT 'not_started'
        CHECK (descendant_consultation_status IN (
            'not_started',
            'in_progress',
            'completed',
            'not_applicable'
        )),
    consultation_community text,
    repatriation_request_status text NOT NULL DEFAULT 'none'
        CHECK (repatriation_request_status IN (
            'none',
            'requested',
            'under_review',
            'approved',
            'declined',
            'completed'
        )),
    repatriation_request_reference text,
    ethics_notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS flora_specimen (
    bio_sample_id uuid PRIMARY KEY
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    scientific_name text NOT NULL CHECK (length(btrim(scientific_name)) > 0),
    gbif_taxon_key bigint NOT NULL CHECK (gbif_taxon_key > 0),
    identification_notes text,
    identified_by text,
    identified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS flora_specimen_gbif_taxon_idx
    ON flora_specimen (gbif_taxon_key);

CREATE TABLE IF NOT EXISTS fauna_specimen (
    bio_sample_id uuid PRIMARY KEY
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    scientific_name text NOT NULL CHECK (length(btrim(scientific_name)) > 0),
    gbif_taxon_key bigint NOT NULL CHECK (gbif_taxon_key > 0),
    identification_notes text,
    identified_by text,
    identified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fauna_specimen_gbif_taxon_idx
    ON fauna_specimen (gbif_taxon_key);

CREATE OR REPLACE FUNCTION validate_bio_sample_subtype()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    expected_type text;
    actual_type text;
BEGIN
    expected_type := TG_ARGV[0];
    SELECT sample_type
    INTO actual_type
    FROM bio_sample
    WHERE id = NEW.bio_sample_id;

    IF actual_type IS DISTINCT FROM expected_type THEN
        RAISE EXCEPTION
            'Subtype record requires bio_sample.sample_type = %',
            expected_type
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS human_sample_type_check ON human_sample;
CREATE TRIGGER human_sample_type_check
BEFORE INSERT OR UPDATE ON human_sample
FOR EACH ROW EXECUTE FUNCTION validate_bio_sample_subtype('human_sample');

DROP TRIGGER IF EXISTS flora_specimen_type_check ON flora_specimen;
CREATE TRIGGER flora_specimen_type_check
BEFORE INSERT OR UPDATE ON flora_specimen
FOR EACH ROW EXECUTE FUNCTION validate_bio_sample_subtype('flora_specimen');

DROP TRIGGER IF EXISTS fauna_specimen_type_check ON fauna_specimen;
CREATE TRIGGER fauna_specimen_type_check
BEFORE INSERT OR UPDATE ON fauna_specimen
FOR EACH ROW EXECUTE FUNCTION validate_bio_sample_subtype('fauna_specimen');

CREATE OR REPLACE FUNCTION require_bio_sample_subtype()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    sample_ids uuid[];
    sample_id uuid;
    sample_kind text;
    has_human boolean;
    has_flora boolean;
    has_fauna boolean;
BEGIN
    IF TG_TABLE_NAME = 'bio_sample' THEN
        sample_ids := ARRAY[NEW.id];
    ELSIF TG_OP = 'UPDATE' THEN
        sample_ids := ARRAY[OLD.bio_sample_id, NEW.bio_sample_id];
    ELSIF TG_OP = 'DELETE' THEN
        sample_ids := ARRAY[OLD.bio_sample_id];
    ELSE
        sample_ids := ARRAY[NEW.bio_sample_id];
    END IF;

    FOREACH sample_id IN ARRAY sample_ids LOOP
        SELECT sample_type
        INTO sample_kind
        FROM bio_sample
        WHERE id = sample_id;

        IF NOT FOUND THEN
            CONTINUE;
        END IF;

        SELECT EXISTS (
            SELECT 1 FROM human_sample WHERE bio_sample_id = sample_id
        ) INTO has_human;
        SELECT EXISTS (
            SELECT 1 FROM flora_specimen WHERE bio_sample_id = sample_id
        ) INTO has_flora;
        SELECT EXISTS (
            SELECT 1 FROM fauna_specimen WHERE bio_sample_id = sample_id
        ) INTO has_fauna;

        IF (sample_kind = 'human_sample' AND
            (NOT has_human OR has_flora OR has_fauna))
           OR (sample_kind = 'flora_specimen' AND
            (NOT has_flora OR has_human OR has_fauna))
           OR (sample_kind = 'fauna_specimen' AND
            (NOT has_fauna OR has_human OR has_flora))
           OR (sample_kind = 'bio_sample' AND
            (has_human OR has_flora OR has_fauna)) THEN
            RAISE EXCEPTION
                'Biological sample % must have exactly the subtype record matching sample_type %',
                sample_id,
                sample_kind
                USING ERRCODE = '23514';
        END IF;
    END LOOP;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS bio_sample_subtype_required ON bio_sample;
CREATE CONSTRAINT TRIGGER bio_sample_subtype_required
AFTER INSERT OR UPDATE ON bio_sample
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_bio_sample_subtype();

DROP TRIGGER IF EXISTS human_sample_subtype_required ON human_sample;
CREATE CONSTRAINT TRIGGER human_sample_subtype_required
AFTER INSERT OR UPDATE OR DELETE ON human_sample
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_bio_sample_subtype();

DROP TRIGGER IF EXISTS flora_specimen_subtype_required ON flora_specimen;
CREATE CONSTRAINT TRIGGER flora_specimen_subtype_required
AFTER INSERT OR UPDATE OR DELETE ON flora_specimen
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_bio_sample_subtype();

DROP TRIGGER IF EXISTS fauna_specimen_subtype_required ON fauna_specimen;
CREATE CONSTRAINT TRIGGER fauna_specimen_subtype_required
AFTER INSERT OR UPDATE OR DELETE ON fauna_specimen
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_bio_sample_subtype();

CREATE TABLE IF NOT EXISTS sample_lab_output (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bio_sample_id uuid NOT NULL
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    output_type text NOT NULL
        CHECK (output_type IN (
            'genomic',
            'spectral',
            'microscopy',
            'other'
        )),
    file_format text NOT NULL CHECK (length(btrim(file_format)) > 0),
    storage_uri text NOT NULL
        CHECK (storage_uri ~ '^(https?|s3|minio)://'),
    checksum_sha256 text NOT NULL
        CHECK (checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'),
    media_type text,
    description text,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS sample_lab_output_sample_idx
    ON sample_lab_output (bio_sample_id, output_type);
CREATE INDEX IF NOT EXISTS sample_lab_output_checksum_idx
    ON sample_lab_output (checksum_sha256);

COMMENT ON TABLE sample_lab_output IS
    'Pointer metadata for raw laboratory output in MinIO/S3; binary data is never stored in PostgreSQL.';

CREATE TABLE IF NOT EXISTS genomic_dataset (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bio_sample_id uuid NOT NULL
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    output_id uuid NOT NULL
        REFERENCES sample_lab_output (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    reference_assembly text,
    sequencing_method text NOT NULL CHECK (length(btrim(sequencing_method)) > 0),
    dataset_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(dataset_metadata) = 'object'),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (output_id)
);

CREATE INDEX IF NOT EXISTS genomic_dataset_sample_idx
    ON genomic_dataset (bio_sample_id);

CREATE OR REPLACE FUNCTION validate_genomic_dataset_output()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    output_sample_id uuid;
    output_type text;
BEGIN
    SELECT bio_sample_id, output_type
    INTO output_sample_id, output_type
    FROM sample_lab_output
    WHERE id = NEW.output_id;

    IF output_sample_id IS DISTINCT FROM NEW.bio_sample_id
       OR output_type IS DISTINCT FROM 'genomic' THEN
        RAISE EXCEPTION
            'Genomic dataset must reference a genomic output belonging to the same sample'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS genomic_dataset_validate_output ON genomic_dataset;
CREATE TRIGGER genomic_dataset_validate_output
BEFORE INSERT OR UPDATE ON genomic_dataset
FOR EACH ROW EXECUTE FUNCTION validate_genomic_dataset_output();

CREATE TABLE IF NOT EXISTS haplogroup_assignment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bio_sample_id uuid NOT NULL
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    marker_type text NOT NULL
        CHECK (marker_type IN ('mitochondrial', 'y_chromosomal', 'other')),
    haplogroup_label text NOT NULL CHECK (length(btrim(haplogroup_label)) > 0),
    authority_uri text CHECK (authority_uri IS NULL OR authority_uri ~ '^https?://'),
    confidence_lower numeric NOT NULL CHECK (confidence_lower BETWEEN 0 AND 1),
    confidence_upper numeric NOT NULL CHECK (confidence_upper BETWEEN 0 AND 1),
    tree_media_asset_id uuid,
    analysis_output_id uuid
        REFERENCES sample_lab_output (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    assigned_by text,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    notes text,
    CONSTRAINT haplogroup_confidence_interval_check
        CHECK (confidence_lower <= confidence_upper)
);

CREATE INDEX IF NOT EXISTS haplogroup_assignment_sample_idx
    ON haplogroup_assignment (bio_sample_id);
CREATE INDEX IF NOT EXISTS haplogroup_assignment_label_idx
    ON haplogroup_assignment (haplogroup_label);

COMMENT ON COLUMN haplogroup_assignment.tree_media_asset_id IS
    'UUID reference to an IIIF-annotated SVG Media_Asset, if a phylogenetic tree is available.';

CREATE TABLE IF NOT EXISTS dispersion_analysis (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_type text NOT NULL
        CHECK (analysis_type IN ('genome', 'flora', 'fauna')),
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    notebook_uri text NOT NULL
        CHECK (notebook_uri ~ '^(https?|s3|minio)://'),
    notebook_revision text NOT NULL CHECK (length(btrim(notebook_revision)) > 0),
    environment_reference text NOT NULL
        CHECK (length(btrim(environment_reference)) > 0),
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(parameters) = 'object'),
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'complete', 'failed')),
    started_at timestamptz,
    completed_at timestamptz,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dispersion_analysis_time_check CHECK (
        completed_at IS NULL
        OR started_at IS NULL
        OR completed_at >= started_at
    ),
    CONSTRAINT dispersion_analysis_status_time_check CHECK (
        status NOT IN ('running', 'complete')
        OR started_at IS NOT NULL
    ),
    CONSTRAINT dispersion_analysis_completed_time_check CHECK (
        status <> 'complete'
        OR completed_at IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS dispersion_analysis_sample (
    dispersion_analysis_id uuid NOT NULL
        REFERENCES dispersion_analysis (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    bio_sample_id uuid NOT NULL
        REFERENCES bio_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    PRIMARY KEY (dispersion_analysis_id, bio_sample_id)
);

CREATE INDEX IF NOT EXISTS dispersion_analysis_sample_sample_idx
    ON dispersion_analysis_sample (bio_sample_id);

CREATE TABLE IF NOT EXISTS dispersion_analysis_region (
    dispersion_analysis_id uuid NOT NULL
        REFERENCES dispersion_analysis (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    regional_chronicle_id uuid NOT NULL,
    PRIMARY KEY (dispersion_analysis_id, regional_chronicle_id)
);

CREATE INDEX IF NOT EXISTS dispersion_analysis_region_region_idx
    ON dispersion_analysis_region (regional_chronicle_id);

COMMENT ON COLUMN dispersion_analysis_region.regional_chronicle_id IS
    'UUID reference to Regional_Chronicle; foreign key is deferred until the historiographical schema exists.';

CREATE TABLE IF NOT EXISTS dispersion_analysis_media_asset (
    dispersion_analysis_id uuid NOT NULL
        REFERENCES dispersion_analysis (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    media_asset_id uuid NOT NULL,
    asset_role text NOT NULL
        CHECK (asset_role IN ('interactive_visualization', 'phylogenetic_tree', 'other')),
    PRIMARY KEY (dispersion_analysis_id, media_asset_id)
);

COMMENT ON TABLE dispersion_analysis_media_asset IS
    'Generated visualizations and phylogenetic trees are stored as Media_Assets; this table stores only their UUID references.';

CREATE OR REPLACE FUNCTION set_hard_sciences_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS bio_sample_set_updated_at ON bio_sample;
CREATE TRIGGER bio_sample_set_updated_at
BEFORE UPDATE ON bio_sample
FOR EACH ROW EXECUTE FUNCTION set_hard_sciences_updated_at();

DROP TRIGGER IF EXISTS dispersion_analysis_set_updated_at ON dispersion_analysis;
CREATE TRIGGER dispersion_analysis_set_updated_at
BEFORE UPDATE ON dispersion_analysis
FOR EACH ROW EXECUTE FUNCTION set_hard_sciences_updated_at();
