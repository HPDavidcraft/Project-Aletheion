CREATE TABLE IF NOT EXISTS crm_standard_registry (
    standard_code text PRIMARY KEY,
    standard_name text NOT NULL,
    namespace_uri text NOT NULL CHECK (namespace_uri ~ '^https?://'),
    documentation_uri text NOT NULL CHECK (documentation_uri ~ '^https?://'),
    adopted_release text,
    verification_status text NOT NULL DEFAULT 'unverified'
        CHECK (verification_status IN ('unverified', 'verified')),
    reviewed_by uuid,
    reviewed_at timestamptz,
    notes text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT crm_standard_review_check CHECK (
        verification_status <> 'verified'
        OR (
            adopted_release IS NOT NULL
            AND length(btrim(adopted_release)) > 0
            AND reviewed_by IS NOT NULL
            AND reviewed_at IS NOT NULL
        )
    )
);

INSERT INTO crm_standard_registry (
    standard_code,
    standard_name,
    namespace_uri,
    documentation_uri,
    adopted_release,
    notes
)
VALUES
    (
        'cidoc-crm',
        'CIDOC Conceptual Reference Model',
        'http://www.cidoc-crm.org/cidoc-crm/',
        'https://www.cidoc-crm.org/',
        NULL,
        'Core ontology; project guidelines identify ISO 21127. Pin and verify the adopted release before production.'
    ),
    (
        'crmarchaeo',
        'CIDOC CRM Archaeological Excavation Model',
        'http://www.cidoc-crm.org/cidoc-crm/CRMarchaeo/',
        'https://www.cidoc-crm.org/crmarchaeo',
        NULL,
        'The guidelines also use the name CRMba. Confirm the selected release and namespace during ontology review.'
    ),
    (
        'crmsci',
        'CIDOC CRM Scientific Observation Model',
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/',
        'https://www.cidoc-crm.org/crmsci',
        NULL,
        'Pin and verify the adopted release before production.'
    ),
    (
        'crmgeo',
        'CIDOC CRM Geospatial Model',
        'http://www.cidoc-crm.org/cidoc-crm/CRMgeo/',
        'https://www.cidoc-crm.org/crmgeo',
        NULL,
        'Pin and verify the adopted release before production.'
    ),
    (
        'crminf',
        'CIDOC CRM Argumentation Model',
        'http://www.cidoc-crm.org/cidoc-crm/CRMinf/',
        'https://www.cidoc-crm.org/crminf',
        NULL,
        'Pin and verify the adopted release before production.'
    ),
    (
        'frbroo',
        'FRBR Object-Oriented Model',
        'http://iflastandards.info/ns/fr/frbr/frbroo/',
        'https://www.ifla.org/',
        NULL,
        'The project uses this profile for bibliographic and textual entities; pin and verify its adopted release.'
    )
ON CONFLICT (standard_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS crm_term_registry (
    term_uri text PRIMARY KEY CHECK (term_uri ~ '^https?://'),
    standard_code text NOT NULL
        REFERENCES crm_standard_registry (standard_code)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    term_code text NOT NULL CHECK (length(btrim(term_code)) > 0),
    term_kind text NOT NULL CHECK (term_kind IN ('class', 'property')),
    preferred_label text NOT NULL CHECK (length(btrim(preferred_label)) > 0),
    source_reference text NOT NULL CHECK (length(btrim(source_reference)) > 0),
    verification_status text NOT NULL DEFAULT 'unverified'
        CHECK (verification_status IN ('unverified', 'verified', 'deprecated')),
    reviewed_by uuid,
    reviewed_at timestamptz,
    notes text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (standard_code, term_code),
    UNIQUE (term_uri, term_kind),
    CONSTRAINT crm_term_review_check CHECK (
        verification_status <> 'verified'
        OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS crm_term_registry_standard_kind_idx
    ON crm_term_registry (standard_code, term_kind);
CREATE INDEX IF NOT EXISTS crm_term_registry_status_idx
    ON crm_term_registry (verification_status);

CREATE OR REPLACE FUNCTION require_verified_crm_standard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    parent_status text;
    parent_release text;
BEGIN
    IF NEW.verification_status <> 'verified' THEN
        RETURN NEW;
    END IF;

    SELECT verification_status, adopted_release
    INTO parent_status, parent_release
    FROM crm_standard_registry
    WHERE standard_code = NEW.standard_code;

    IF parent_status <> 'verified'
       OR parent_release IS NULL
       OR length(btrim(parent_release)) = 0 THEN
        RAISE EXCEPTION
            'A CRM term cannot be verified until its standard release is pinned and verified'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS crm_term_registry_require_verified_standard
    ON crm_term_registry;
CREATE TRIGGER crm_term_registry_require_verified_standard
BEFORE INSERT OR UPDATE
ON crm_term_registry
FOR EACH ROW EXECUTE FUNCTION require_verified_crm_standard();

INSERT INTO crm_term_registry (
    term_uri,
    standard_code,
    term_code,
    term_kind,
    preferred_label,
    source_reference,
    notes
)
VALUES
    (
        'http://www.cidoc-crm.org/cidoc-crm/E27_Site',
        'cidoc-crm',
        'E27',
        'class',
        'Site',
        'Pleroma Guidelines v1.0 §4.6',
        'Project Site class mapping.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/E22_Human-Made_Object',
        'cidoc-crm',
        'E22',
        'class',
        'Human-Made Object',
        'Pleroma Guidelines v1.0 §4.6',
        'Project Find class mapping.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/E52_Time-Span',
        'cidoc-crm',
        'E52',
        'class',
        'Time-Span',
        'Pleroma Guidelines v1.0 §3.2',
        'Included as an explicitly named core CRM example.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/E53_Place',
        'cidoc-crm',
        'E53',
        'class',
        'Place',
        'Pleroma Guidelines v1.0 §3.2',
        'Included as an explicitly named core CRM example.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMarchaeo/A2_Stratigraphic_Volume_Unit',
        'crmarchaeo',
        'A2',
        'class',
        'Stratigraphic Volume Unit',
        'Pleroma Guidelines v1.0 §§3.2 and 4.6',
        'Guidelines describe A2 as contained in A8 Stratigraphic Unit.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMarchaeo/A8_Stratigraphic_Unit',
        'crmarchaeo',
        'A8',
        'class',
        'Stratigraphic Unit',
        'Pleroma Guidelines v1.0 §3.2',
        'Included for the documented A2/A8 containment mapping.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S2_Sample',
        'crmsci',
        'S2',
        'class',
        'Sample',
        'Pleroma Guidelines v1.0 §3.2',
        'Applied to biological and chronometric samples where appropriate.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S4_Observation',
        'crmsci',
        'S4',
        'class',
        'Observation',
        'Pleroma Guidelines v1.0 §§3.2 and 4.10',
        'Project Material_Analysis_Event mapping.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S6_Data_Object',
        'crmsci',
        'S6',
        'class',
        'Data Object',
        'Pleroma Guidelines v1.0 §3.2',
        'Example output of a scientific observation.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMgeo/SP1_Phenomenal_Spacetime_Volume',
        'crmgeo',
        'SP1',
        'class',
        'Phenomenal Spacetime Volume',
        'Pleroma Guidelines v1.0 §3.2',
        'Included as an explicitly named CRMgeo example.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMgeo/SP2_Phenomenal_Place',
        'crmgeo',
        'SP2',
        'class',
        'Phenomenal Place',
        'Pleroma Guidelines v1.0 §3.2',
        'Included as an explicitly named CRMgeo example.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMinf/I1_Argumentation',
        'crminf',
        'I1',
        'class',
        'Argumentation',
        'Pleroma Guidelines v1.0 §3.2',
        'Project Interpretation_Hypothesis mapping.'
    ),
    (
        'http://www.cidoc-crm.org/cidoc-crm/CRMinf/I4_Proposition_Set',
        'crminf',
        'I4',
        'class',
        'Proposition Set',
        'Pleroma Guidelines v1.0 §3.2',
        'Included in the project hypothesis representation.'
    ),
    (
        'http://iflastandards.info/ns/fr/frbr/frbroo/F4_Manifestation_Singleton',
        'frbroo',
        'F4',
        'class',
        'Manifestation Singleton',
        'Pleroma Guidelines v1.0 §3.2',
        'Project Text_Witness mapping.'
    )
ON CONFLICT (term_uri) DO NOTHING;

CREATE TABLE IF NOT EXISTS pleroma_class_mapping (
    project_class_uri text NOT NULL CHECK (project_class_uri ~ '^https?://'),
    crm_class_uri text NOT NULL,
    crm_term_kind text NOT NULL DEFAULT 'class'
        CHECK (crm_term_kind = 'class'),
    mapping_relation text NOT NULL DEFAULT 'subClassOf'
        CHECK (mapping_relation IN ('subClassOf', 'exactMatch', 'closeMatch')),
    rationale text NOT NULL CHECK (length(btrim(rationale)) > 0),
    source_reference text NOT NULL CHECK (length(btrim(source_reference)) > 0),
    mapping_status text NOT NULL DEFAULT 'proposed'
        CHECK (mapping_status IN ('proposed', 'verified', 'deprecated')),
    reviewed_by uuid,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_class_uri, crm_class_uri),
    CONSTRAINT pleroma_class_mapping_term_fk
        FOREIGN KEY (crm_class_uri, crm_term_kind)
        REFERENCES crm_term_registry (term_uri, term_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT pleroma_class_mapping_review_check CHECK (
        mapping_status <> 'verified'
        OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS pleroma_class_mapping_status_idx
    ON pleroma_class_mapping (mapping_status);

CREATE OR REPLACE FUNCTION require_verified_crm_class_term()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    term_status text;
BEGIN
    IF NEW.mapping_status <> 'verified' THEN
        RETURN NEW;
    END IF;

    SELECT verification_status
    INTO term_status
    FROM crm_term_registry
    WHERE term_uri = NEW.crm_class_uri
      AND term_kind = 'class';

    IF term_status <> 'verified' THEN
        RAISE EXCEPTION
            'A Pleroma class mapping requires a verified CRM class term'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pleroma_class_mapping_require_verified_term
    ON pleroma_class_mapping;
CREATE TRIGGER pleroma_class_mapping_require_verified_term
BEFORE INSERT OR UPDATE
ON pleroma_class_mapping
FOR EACH ROW EXECUTE FUNCTION require_verified_crm_class_term();

INSERT INTO pleroma_class_mapping (
    project_class_uri,
    crm_class_uri,
    rationale,
    source_reference
)
VALUES
    (
        'https://pleroma.project-aletheion.org/ontology/Site',
        'http://www.cidoc-crm.org/cidoc-crm/E27_Site',
        'Pleroma Site is explicitly identified as CIDOC CRM E27 Site.',
        'Pleroma Guidelines v1.0 §4.6'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/Find',
        'http://www.cidoc-crm.org/cidoc-crm/E22_Human-Made_Object',
        'Pleroma Find is explicitly identified as CIDOC CRM E22 Man-Made Object.',
        'Pleroma Guidelines v1.0 §4.6'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/StratigraphicUnit',
        'http://www.cidoc-crm.org/cidoc-crm/CRMarchaeo/A2_Stratigraphic_Volume_Unit',
        'Pleroma Stratigraphic_Unit is explicitly identified as CRMarchaeo A2.',
        'Pleroma Guidelines v1.0 §4.6'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/BioSample',
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S2_Sample',
        'Pleroma biological samples use the CRMsci sample model.',
        'Pleroma Guidelines v1.0 §§3.2 and 4.5'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/ChronometricSample',
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S2_Sample',
        'A chronometric sample is modeled as a scientific sample.',
        'Pleroma Guidelines v1.0 §§3.2 and 4.10'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/MaterialAnalysisEvent',
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S4_Observation',
        'Pleroma Material_Analysis_Event is explicitly identified as CRMsci S4.',
        'Pleroma Guidelines v1.0 §§3.2 and 4.10'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/MaterialAnalysisResult',
        'http://www.cidoc-crm.org/cidoc-crm/CRMsci/S6_Data_Object',
        'The guidelines identify S6 Data Object as an observation output.',
        'Pleroma Guidelines v1.0 §3.2'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/InterpretationHypothesis',
        'http://www.cidoc-crm.org/cidoc-crm/CRMinf/I1_Argumentation',
        'Pleroma Interpretation_Hypothesis uses the CRMinf argumentation model.',
        'Pleroma Guidelines v1.0 §3.2'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/HypothesisPropositionSet',
        'http://www.cidoc-crm.org/cidoc-crm/CRMinf/I4_Proposition_Set',
        'Hypothesis proposition sets use the CRMinf I4 class named in the guidelines.',
        'Pleroma Guidelines v1.0 §3.2'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/GeoFeatureTemporal',
        'http://www.cidoc-crm.org/cidoc-crm/CRMgeo/SP2_Phenomenal_Place',
        'Temporal geographic features use the CRMgeo place model.',
        'Pleroma Guidelines v1.0 §§3.2 and 4.8'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/SpatiotemporalExtent',
        'http://www.cidoc-crm.org/cidoc-crm/CRMgeo/SP1_Phenomenal_Spacetime_Volume',
        'Spatiotemporal extents use the CRMgeo class named in the guidelines.',
        'Pleroma Guidelines v1.0 §3.2'
    ),
    (
        'https://pleroma.project-aletheion.org/ontology/TextWitness',
        'http://iflastandards.info/ns/fr/frbr/frbroo/F4_Manifestation_Singleton',
        'Pleroma Text_Witness uses the FRBRoo class named in the guidelines.',
        'Pleroma Guidelines v1.0 §§3.2 and 4.12'
    )
ON CONFLICT (project_class_uri, crm_class_uri) DO NOTHING;

CREATE TABLE IF NOT EXISTS pleroma_property_mapping (
    project_property_uri text NOT NULL CHECK (project_property_uri ~ '^https?://'),
    crm_property_uri text NOT NULL,
    crm_term_kind text NOT NULL DEFAULT 'property'
        CHECK (crm_term_kind = 'property'),
    mapping_relation text NOT NULL DEFAULT 'exactMatch'
        CHECK (mapping_relation IN ('exactMatch', 'closeMatch')),
    rationale text NOT NULL CHECK (length(btrim(rationale)) > 0),
    source_reference text NOT NULL CHECK (length(btrim(source_reference)) > 0),
    mapping_status text NOT NULL DEFAULT 'proposed'
        CHECK (mapping_status IN ('proposed', 'verified', 'deprecated')),
    reviewed_by uuid,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_property_uri, crm_property_uri),
    CONSTRAINT pleroma_property_mapping_term_fk
        FOREIGN KEY (crm_property_uri, crm_term_kind)
        REFERENCES crm_term_registry (term_uri, term_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT pleroma_property_mapping_review_check CHECK (
        mapping_status <> 'verified'
        OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS pleroma_property_mapping_status_idx
    ON pleroma_property_mapping (mapping_status);

CREATE OR REPLACE FUNCTION require_verified_crm_property_term()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    term_status text;
BEGIN
    IF NEW.mapping_status <> 'verified' THEN
        RETURN NEW;
    END IF;

    SELECT verification_status
    INTO term_status
    FROM crm_term_registry
    WHERE term_uri = NEW.crm_property_uri
      AND term_kind = 'property';

    IF term_status <> 'verified' THEN
        RAISE EXCEPTION
            'A Pleroma property mapping requires a verified CRM property term'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pleroma_property_mapping_require_verified_term
    ON pleroma_property_mapping;
CREATE TRIGGER pleroma_property_mapping_require_verified_term
BEFORE INSERT OR UPDATE
ON pleroma_property_mapping
FOR EACH ROW EXECUTE FUNCTION require_verified_crm_property_term();

CREATE OR REPLACE FUNCTION set_crm_mapping_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS crm_standard_registry_set_updated_at ON crm_standard_registry;
CREATE TRIGGER crm_standard_registry_set_updated_at
BEFORE UPDATE ON crm_standard_registry
FOR EACH ROW EXECUTE FUNCTION set_crm_mapping_updated_at();

DROP TRIGGER IF EXISTS crm_term_registry_set_updated_at ON crm_term_registry;
CREATE TRIGGER crm_term_registry_set_updated_at
BEFORE UPDATE ON crm_term_registry
FOR EACH ROW EXECUTE FUNCTION set_crm_mapping_updated_at();

DROP TRIGGER IF EXISTS pleroma_class_mapping_set_updated_at ON pleroma_class_mapping;
CREATE TRIGGER pleroma_class_mapping_set_updated_at
BEFORE UPDATE ON pleroma_class_mapping
FOR EACH ROW EXECUTE FUNCTION set_crm_mapping_updated_at();

DROP TRIGGER IF EXISTS pleroma_property_mapping_set_updated_at ON pleroma_property_mapping;
CREATE TRIGGER pleroma_property_mapping_set_updated_at
BEFORE UPDATE ON pleroma_property_mapping
FOR EACH ROW EXECUTE FUNCTION set_crm_mapping_updated_at();
