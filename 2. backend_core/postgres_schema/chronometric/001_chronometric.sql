CREATE TABLE IF NOT EXISTS calibration_curve (
    code text PRIMARY KEY,
    description text NOT NULL
);

INSERT INTO calibration_curve (code, description)
VALUES
    ('IntCal20', 'Northern Hemisphere atmospheric radiocarbon calibration curve'),
    ('Marine20', 'Marine radiocarbon calibration curve'),
    ('SHCal20', 'Southern Hemisphere atmospheric radiocarbon calibration curve')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS chronometric_method (
    code text PRIMARY KEY,
    label text NOT NULL
);

INSERT INTO chronometric_method (code, label)
VALUES
    ('ams_c14', 'AMS C14'),
    ('conventional_c14', 'Conventional C14'),
    ('osl', 'Optically stimulated luminescence (OSL)'),
    ('tl', 'Thermoluminescence (TL)'),
    ('u_series', 'U-series'),
    ('dendrochronology', 'Dendrochronology'),
    ('archaeomagnetism', 'Archaeomagnetism'),
    ('k_ar', 'K-Ar')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS chronometric_sample (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lab_institution text NOT NULL CHECK (length(btrim(lab_institution)) > 0),
    lab_code text NOT NULL CHECK (length(btrim(lab_code)) > 0),
    method_code text NOT NULL
        REFERENCES chronometric_method (code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calibration_curve_code text
        REFERENCES calibration_curve (code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    raw_date_bp numeric NOT NULL,
    error_margin_1sigma numeric NOT NULL CHECK (error_margin_1sigma > 0),
    material_context text NOT NULL CHECK (length(btrim(material_context)) > 0),
    material_type_uri text
        CHECK (material_type_uri IS NULL OR material_type_uri ~ '^https?://'),
    sample_entity_type text,
    sample_entity_id uuid,
    stratigraphic_unit_id uuid,
    surface_collection_context text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chronometric_sample_lab_code_unique
        UNIQUE (lab_institution, lab_code),
    CONSTRAINT chronometric_sample_entity_reference_check CHECK (
        (sample_entity_type IS NULL AND sample_entity_id IS NULL)
        OR (
            sample_entity_type IS NOT NULL
            AND length(btrim(sample_entity_type)) > 0
            AND sample_entity_id IS NOT NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS chronometric_sample_method_idx
    ON chronometric_sample (method_code);
CREATE INDEX IF NOT EXISTS chronometric_sample_entity_idx
    ON chronometric_sample (sample_entity_type, sample_entity_id)
    WHERE sample_entity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS chronometric_sample_stratigraphic_unit_idx
    ON chronometric_sample (stratigraphic_unit_id)
    WHERE stratigraphic_unit_id IS NOT NULL;

COMMENT ON TABLE chronometric_sample IS
    'Original chronometric measurement. Raw date, analytical method, and 1-sigma error are immutable after insertion.';
COMMENT ON COLUMN chronometric_sample.raw_date_bp IS
    'Uncalibrated measurement in years Before Present; never replace with a calibrated result.';
COMMENT ON COLUMN chronometric_sample.material_context IS
    'Description of the dated material and context.';
COMMENT ON COLUMN chronometric_sample.stratigraphic_unit_id IS
    'UUID reference to a Stratigraphic_Unit; foreign key is deferred until the site-hierarchy schema is installed.';

CREATE OR REPLACE FUNCTION prevent_chronometric_measurement_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
        RAISE EXCEPTION
            'Original chronometric samples are immutable; create a new sample record for a corrected measurement'
            USING ERRCODE = '55000';
    END IF;

    IF ROW(
        NEW.lab_code,
        NEW.method_code,
        NEW.calibration_curve_code,
        NEW.raw_date_bp,
        NEW.error_margin_1sigma
    ) IS DISTINCT FROM ROW(
        OLD.lab_code,
        OLD.method_code,
        OLD.calibration_curve_code,
        OLD.raw_date_bp,
        OLD.error_margin_1sigma
    ) THEN
        RAISE EXCEPTION
            'Original chronometric measurement fields are immutable; create a new sample record for a corrected measurement'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS chronometric_sample_measurement_immutable
    ON chronometric_sample;
CREATE TRIGGER chronometric_sample_measurement_immutable
BEFORE UPDATE OR DELETE ON chronometric_sample
FOR EACH ROW EXECUTE FUNCTION prevent_chronometric_measurement_change();

DROP TRIGGER IF EXISTS chronometric_sample_no_truncate ON chronometric_sample;
CREATE TRIGGER chronometric_sample_no_truncate
BEFORE TRUNCATE ON chronometric_sample
FOR EACH STATEMENT EXECUTE FUNCTION prevent_chronometric_measurement_change();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'temporal_distribution'
          AND typnamespace = current_schema()::regnamespace
    ) THEN
        CREATE TYPE temporal_distribution AS (
            p_start numeric,
            p_end numeric,
            probability_curve jsonb
        );
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION is_valid_temporal_distribution(distribution_value temporal_distribution)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    point jsonb;
    current_year numeric;
    probability numeric;
    previous_year numeric := NULL;
BEGIN
    IF (distribution_value).p_start IS NULL
       OR (distribution_value).p_end IS NULL
       OR (distribution_value).p_start > (distribution_value).p_end
       OR (distribution_value).probability_curve IS NULL THEN
        RETURN false;
    END IF;

    IF jsonb_typeof((distribution_value).probability_curve) <> 'array' THEN
        RETURN false;
    END IF;
    IF jsonb_array_length((distribution_value).probability_curve) = 0 THEN
        RETURN false;
    END IF;

    FOR point IN
        SELECT element
        FROM jsonb_array_elements((distribution_value).probability_curve) AS curve(element)
    LOOP
        IF jsonb_typeof(point) <> 'array' THEN
            RETURN false;
        END IF;
        IF jsonb_array_length(point) <> 2 THEN
            RETURN false;
        END IF;
        IF jsonb_typeof(point -> 0) <> 'number'
           OR jsonb_typeof(point -> 1) <> 'number' THEN
            RETURN false;
        END IF;

        current_year := (point ->> 0)::numeric;
        probability := (point ->> 1)::numeric;
        IF current_year < (distribution_value).p_start
           OR current_year > (distribution_value).p_end
           OR probability < 0
           OR probability > 1
           OR (previous_year IS NOT NULL AND current_year <= previous_year) THEN
            RETURN false;
        END IF;
        previous_year := current_year;
    END LOOP;

    RETURN true;
END;
$$;

CREATE TABLE IF NOT EXISTS calibration_result (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sample_id uuid NOT NULL
        REFERENCES chronometric_sample (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    curve_code text NOT NULL
        REFERENCES calibration_curve (code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calibrated_distribution temporal_distribution NOT NULL
        CHECK (is_valid_temporal_distribution(calibrated_distribution)),
    software_name text NOT NULL CHECK (length(btrim(software_name)) > 0),
    software_version text NOT NULL CHECK (length(btrim(software_version)) > 0),
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(parameters) = 'object'),
    result_uri text
        CHECK (result_uri IS NULL OR result_uri ~ '^(https?|s3|minio)://'),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS calibration_result_sample_idx
    ON calibration_result (sample_id, created_at DESC);
CREATE INDEX IF NOT EXISTS calibration_result_curve_idx
    ON calibration_result (curve_code);
CREATE INDEX IF NOT EXISTS calibration_result_distribution_bounds_idx
    ON calibration_result (
        ((calibrated_distribution).p_start),
        ((calibrated_distribution).p_end)
    );

COMMENT ON TABLE calibration_result IS
    'Append-only calibrated output. Recalibration creates a new row and preserves all previous results and raw sample values.';
COMMENT ON COLUMN calibration_result.calibrated_distribution IS
    'P_Start, P_End, and an ordered JSON array of [year, probability] points; probabilities are in [0,1].';
COMMENT ON COLUMN calibration_result.created_by IS
    'Authenticated actor UUID supplied by the application; link to the users table when its identity schema is established.';

CREATE OR REPLACE FUNCTION prevent_calibration_result_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Calibration results are immutable; insert a new result for recalibration'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS calibration_result_append_only ON calibration_result;
CREATE TRIGGER calibration_result_append_only
BEFORE UPDATE OR DELETE ON calibration_result
FOR EACH ROW EXECUTE FUNCTION prevent_calibration_result_mutation();

DROP TRIGGER IF EXISTS calibration_result_no_truncate ON calibration_result;
CREATE TRIGGER calibration_result_no_truncate
BEFORE TRUNCATE ON calibration_result
FOR EACH STATEMENT EXECUTE FUNCTION prevent_calibration_result_mutation();

CREATE TABLE IF NOT EXISTS chronology_set (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE CHECK (length(btrim(name)) > 0),
    description text,
    year_offset integer NOT NULL DEFAULT 0,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE chronology_set IS
    'Named chronological school or interpretation set; apply year_offset only when presenting dates, never by rewriting source measurements or calibration results.';

CREATE TABLE IF NOT EXISTS chronology_assertion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chronology_set_id uuid NOT NULL
        REFERENCES chronology_set (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    calibration_result_id uuid NOT NULL
        REFERENCES calibration_result (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    certainty_score numeric NOT NULL
        CHECK (certainty_score >= 0 AND certainty_score <= 1),
    interpretation_notes text,
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (chronology_set_id, calibration_result_id)
);

CREATE INDEX IF NOT EXISTS chronology_assertion_set_idx
    ON chronology_assertion (chronology_set_id);
CREATE INDEX IF NOT EXISTS chronology_assertion_result_idx
    ON chronology_assertion (calibration_result_id);
CREATE INDEX IF NOT EXISTS chronology_assertion_low_certainty_idx
    ON chronology_assertion (certainty_score)
    WHERE certainty_score < 0.5;

COMMENT ON TABLE chronology_assertion IS
    'A set-specific chronological assertion with independently recorded certainty; scores below 0.5 should receive the public uncertainty indicator.';

CREATE OR REPLACE FUNCTION set_chronology_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS chronology_set_set_updated_at ON chronology_set;
CREATE TRIGGER chronology_set_set_updated_at
BEFORE UPDATE ON chronology_set
FOR EACH ROW EXECUTE FUNCTION set_chronology_set_updated_at();
