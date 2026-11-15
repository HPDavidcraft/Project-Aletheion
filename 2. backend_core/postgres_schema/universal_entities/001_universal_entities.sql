CREATE TABLE IF NOT EXISTS media_gallery (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_entity_type text NOT NULL
        CHECK (length(btrim(parent_entity_type)) > 0),
    parent_entity_id uuid NOT NULL,
    caption text NOT NULL CHECK (length(btrim(caption)) > 0),
    coverage_statement text NOT NULL
        CHECK (length(btrim(coverage_statement)) > 0),
    rights_holder text NOT NULL CHECK (length(btrim(rights_holder)) > 0),
    gallery_status text NOT NULL DEFAULT 'draft'
        CHECK (gallery_status IN ('draft', 'ready')),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT media_gallery_parent_unique
        UNIQUE (parent_entity_type, parent_entity_id)
);

CREATE INDEX IF NOT EXISTS media_gallery_parent_idx
    ON media_gallery (parent_entity_type, parent_entity_id);
CREATE INDEX IF NOT EXISTS media_gallery_status_idx
    ON media_gallery (gallery_status);

COMMENT ON TABLE media_gallery IS
    'One-to-one media container for a parent domain record. The polymorphic parent link is verified by per-table triggers once that record is created.';
COMMENT ON COLUMN media_gallery.parent_entity_type IS
    'Parent table/entity identifier, matching the database table name used by the parent-link trigger.';

CREATE OR REPLACE FUNCTION prevent_media_gallery_ready_regression()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.gallery_status = 'ready'
       AND (
           NEW.gallery_status <> 'ready'
           OR NEW.parent_entity_type IS DISTINCT FROM OLD.parent_entity_type
           OR NEW.parent_entity_id IS DISTINCT FROM OLD.parent_entity_id
       ) THEN
        RAISE EXCEPTION
            'A ready Media_Gallery cannot be downgraded or reassigned'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS media_gallery_ready_identity_immutable ON media_gallery;
CREATE TRIGGER media_gallery_ready_identity_immutable
BEFORE UPDATE OF gallery_status, parent_entity_type, parent_entity_id
ON media_gallery
FOR EACH ROW EXECUTE FUNCTION prevent_media_gallery_ready_regression();

CREATE TABLE IF NOT EXISTS media_asset (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    media_gallery_id uuid NOT NULL
        REFERENCES media_gallery (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    asset_type text NOT NULL
        CHECK (asset_type IN (
            'photograph',
            'drawing',
            'plan',
            'section',
            '3d_model',
            'audio',
            'video',
            'rti'
        )),
    source_object_uri text NOT NULL
        CHECK (source_object_uri ~ '^(s3|minio)://'),
    checksum_sha256 text NOT NULL
        CHECK (checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'),
    mime_type text NOT NULL CHECK (length(btrim(mime_type)) > 0),
    file_size_bytes bigint NOT NULL CHECK (file_size_bytes > 0),
    resolution_description text,
    is_archival_master boolean NOT NULL DEFAULT false,
    is_lossless boolean NOT NULL DEFAULT false,
    rights_statement_uri text NOT NULL
        CHECK (rights_statement_uri ~ '^https?://'),
    iiif_service_uri text
        CHECK (iiif_service_uri IS NULL OR iiif_service_uri ~ '^https?://'),
    iiif_manifest_uri text
        CHECK (iiif_manifest_uri IS NULL OR iiif_manifest_uri ~ '^https?://'),
    exif_xmp_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(exif_xmp_metadata) = 'object'),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT media_asset_archival_lossless_check
        CHECK (NOT is_archival_master OR is_lossless),
    CONSTRAINT media_asset_archival_resolution_check
        CHECK (
            NOT is_archival_master
            OR NULLIF(btrim(resolution_description), '') IS NOT NULL
        ),
    CONSTRAINT media_asset_image_iiif_check
        CHECK (
            asset_type NOT IN (
                'photograph',
                'drawing',
                'plan',
                'section',
                'rti'
            )
            OR (
                iiif_service_uri IS NOT NULL
                AND iiif_manifest_uri IS NOT NULL
            )
        ),
    UNIQUE (media_gallery_id, checksum_sha256)
);

CREATE INDEX IF NOT EXISTS media_asset_gallery_idx
    ON media_asset (media_gallery_id);
CREATE INDEX IF NOT EXISTS media_asset_type_idx
    ON media_asset (asset_type);
CREATE INDEX IF NOT EXISTS media_asset_checksum_idx
    ON media_asset (checksum_sha256);

COMMENT ON TABLE media_asset IS
    'External-storage asset metadata only; binary content is held in S3/MinIO. Image assets require Cantaloupe IIIF service and manifest pointers.';
COMMENT ON COLUMN media_asset.source_object_uri IS
    'Private source-object pointer; image delivery must use iiif_service_uri through Cantaloupe.';
COMMENT ON COLUMN media_asset.rights_statement_uri IS
    'URI identifying the asset rights statement.';
COMMENT ON COLUMN media_asset.iiif_service_uri IS
    'Cantaloupe IIIF Image API service URI; required for image and RTI assets.';
COMMENT ON COLUMN media_asset.iiif_manifest_uri IS
    'IIIF Presentation manifest URI; required for image and RTI assets.';

CREATE TABLE IF NOT EXISTS media_asset_annotation_version (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    media_asset_id uuid NOT NULL
        REFERENCES media_asset (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    version_number integer NOT NULL CHECK (version_number > 0),
    annotation_layer jsonb NOT NULL
        CHECK (
            jsonb_typeof(annotation_layer) = 'object'
            AND annotation_layer ? '@context'
            AND annotation_layer ? 'type'
            AND annotation_layer ->> 'type' = 'AnnotationPage'
            AND annotation_layer ? 'items'
            AND jsonb_typeof(annotation_layer -> 'items') = 'array'
        ),
    created_by uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (media_asset_id, version_number)
);

CREATE INDEX IF NOT EXISTS media_asset_annotation_version_asset_idx
    ON media_asset_annotation_version (media_asset_id, version_number DESC);

COMMENT ON TABLE media_asset_annotation_version IS
    'Append-only IIIF-compatible annotation layer history; edits create a new monotonically numbered version.';

CREATE OR REPLACE FUNCTION prevent_media_annotation_version_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Media annotation versions are immutable; create a new version instead'
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS media_asset_annotation_version_append_only
    ON media_asset_annotation_version;
CREATE TRIGGER media_asset_annotation_version_append_only
BEFORE UPDATE OR DELETE ON media_asset_annotation_version
FOR EACH ROW EXECUTE FUNCTION prevent_media_annotation_version_mutation();

DROP TRIGGER IF EXISTS media_asset_annotation_version_no_truncate
    ON media_asset_annotation_version;
CREATE TRIGGER media_asset_annotation_version_no_truncate
BEFORE TRUNCATE ON media_asset_annotation_version
FOR EACH STATEMENT EXECUTE FUNCTION prevent_media_annotation_version_mutation();

CREATE OR REPLACE FUNCTION validate_media_annotation_version_sequence()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    latest_version integer;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtext('pleroma.media_annotation:' || NEW.media_asset_id::text)::bigint
    );

    SELECT max(version_number)
    INTO latest_version
    FROM media_asset_annotation_version
    WHERE media_asset_id = NEW.media_asset_id;

    IF NEW.version_number IS DISTINCT FROM COALESCE(latest_version, 0) + 1 THEN
        RAISE EXCEPTION
            'Media annotation versions must be added sequentially; expected version %, received %',
            COALESCE(latest_version, 0) + 1,
            NEW.version_number
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER media_asset_annotation_version_validate_sequence
BEFORE INSERT ON media_asset_annotation_version
FOR EACH ROW EXECUTE FUNCTION validate_media_annotation_version_sequence();

CREATE OR REPLACE VIEW media_asset_current_annotation AS
SELECT DISTINCT ON (media_asset_id)
    media_asset_id,
    version_number,
    annotation_layer,
    created_by,
    created_at
FROM media_asset_annotation_version
ORDER BY media_asset_id, version_number DESC;

CREATE TABLE IF NOT EXISTS bibliographic_reference (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    zotero_key uuid NOT NULL UNIQUE,
    reference_type text NOT NULL
        CHECK (reference_type IN (
            'book',
            'book_section',
            'journal_article',
            'excavation_report',
            'database_dataset',
            'thesis',
            'manuscript',
            'webpage',
            'other'
        )),
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    creators jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(creators) = 'array'),
    publication_year integer,
    publisher text,
    container_title text,
    doi text
        CHECK (doi IS NULL OR doi ~* '^10\.[0-9]{4,9}/[^[:space:]]+$'),
    doi_status text NOT NULL DEFAULT 'not_checked'
        CHECK (doi_status IN ('not_checked', 'not_available', 'available')),
    url text CHECK (url IS NULL OR url ~ '^https?://'),
    zotero_library_uri text
        CHECK (zotero_library_uri IS NULL OR zotero_library_uri ~ '^https?://'),
    zotero_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(zotero_metadata) = 'object'),
    zotero_synced_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT bibliographic_reference_doi_status_check
        CHECK (
            (doi_status = 'available' AND doi IS NOT NULL)
            OR (doi_status <> 'available' AND doi IS NULL)
        )
);

CREATE INDEX IF NOT EXISTS bibliographic_reference_type_idx
    ON bibliographic_reference (reference_type);
CREATE INDEX IF NOT EXISTS bibliographic_reference_title_idx
    ON bibliographic_reference (title);
CREATE INDEX IF NOT EXISTS bibliographic_reference_doi_idx
    ON bibliographic_reference (doi)
    WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS bibliographic_reference_sync_idx
    ON bibliographic_reference (zotero_synced_at);

COMMENT ON TABLE bibliographic_reference IS
    'Locally cached Zotero record; Zotero_Key is mandatory and nightly synchronization is managed by the integration service.';
COMMENT ON COLUMN bibliographic_reference.doi_status IS
    'The Zotero sync/API verifies DOI availability. Records marked available must include a syntactically valid DOI.';

CREATE TABLE IF NOT EXISTS universal_entity_bibliography (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type_uri text NOT NULL CHECK (entity_type_uri ~ '^https?://'),
    entity_id uuid NOT NULL,
    bibliographic_reference_id uuid NOT NULL
        REFERENCES bibliographic_reference (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
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
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT universal_entity_bibliography_page_check
        CHECK (page_number IS NULL OR length(btrim(page_number)) > 0),
    UNIQUE (
        entity_type_uri,
        entity_id,
        bibliographic_reference_id,
        citation_type
    )
);

CREATE INDEX IF NOT EXISTS universal_entity_bibliography_entity_idx
    ON universal_entity_bibliography (entity_type_uri, entity_id);
CREATE INDEX IF NOT EXISTS universal_entity_bibliography_reference_idx
    ON universal_entity_bibliography (bibliographic_reference_id);

COMMENT ON TABLE universal_entity_bibliography IS
    'Generic citation junction for domain entities; existing domain-specific citation tables remain available and receive real Bibliographic_Reference foreign keys below.';

CREATE OR REPLACE FUNCTION validate_media_gallery_parent()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    gallery_parent_type text;
    gallery_parent_id uuid;
    gallery_state text;
BEGIN
    SELECT parent_entity_type, parent_entity_id, gallery_status
    INTO gallery_parent_type, gallery_parent_id, gallery_state
    FROM media_gallery
    WHERE id = NEW.media_gallery_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'A parent record must reference an existing Media_Gallery'
            USING ERRCODE = '23503';
    END IF;

    IF gallery_state <> 'ready' THEN
        RAISE EXCEPTION
            'A parent record may only reference a ready Media_Gallery'
            USING ERRCODE = '23514';
    END IF;

    IF gallery_parent_type IS DISTINCT FROM TG_TABLE_NAME
       OR gallery_parent_id IS DISTINCT FROM NEW.id THEN
        RAISE EXCEPTION
            'Media_Gallery % must identify parent %.%',
            NEW.media_gallery_id,
            TG_TABLE_NAME,
            NEW.id
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION require_ready_media_gallery_assets()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    gallery_ids uuid[] := ARRAY[]::uuid[];
    gallery_id uuid;
    gallery_state text;
BEGIN
    IF TG_TABLE_NAME = 'media_gallery' THEN
        IF TG_OP = 'UPDATE' THEN
            gallery_ids := array_append(gallery_ids, OLD.id);
        END IF;
        gallery_ids := array_append(gallery_ids, NEW.id);
    ELSE
        IF TG_OP IN ('UPDATE', 'DELETE') THEN
            gallery_ids := array_append(gallery_ids, OLD.media_gallery_id);
        END IF;
        IF TG_OP <> 'DELETE' THEN
            gallery_ids := array_append(gallery_ids, NEW.media_gallery_id);
        END IF;
    END IF;

    FOREACH gallery_id IN ARRAY gallery_ids LOOP
        SELECT media_gallery.gallery_status
        INTO gallery_state
        FROM media_gallery
        WHERE media_gallery.id = gallery_id;

        IF gallery_state = 'ready' AND NOT EXISTS (
            SELECT 1
            FROM media_asset
            WHERE media_asset.media_gallery_id = gallery_id
        ) THEN
            RAISE EXCEPTION
                'Ready Media_Gallery % must contain at least one Media_Asset',
                gallery_id
                USING ERRCODE = '23514';
        END IF;
    END LOOP;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS media_gallery_ready_requires_asset ON media_gallery;
CREATE CONSTRAINT TRIGGER media_gallery_ready_requires_asset
AFTER INSERT OR UPDATE ON media_gallery
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_ready_media_gallery_assets();

DROP TRIGGER IF EXISTS media_asset_change_preserves_ready_gallery
    ON media_asset;
CREATE CONSTRAINT TRIGGER media_asset_change_preserves_ready_gallery
AFTER INSERT OR UPDATE OR DELETE ON media_asset
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION require_ready_media_gallery_assets();

CREATE OR REPLACE FUNCTION set_universal_entities_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS media_gallery_set_updated_at ON media_gallery;
CREATE TRIGGER media_gallery_set_updated_at
BEFORE UPDATE ON media_gallery
FOR EACH ROW EXECUTE FUNCTION set_universal_entities_updated_at();

DROP TRIGGER IF EXISTS media_asset_set_updated_at ON media_asset;
CREATE TRIGGER media_asset_set_updated_at
BEFORE UPDATE ON media_asset
FOR EACH ROW EXECUTE FUNCTION set_universal_entities_updated_at();

DROP TRIGGER IF EXISTS bibliographic_reference_set_updated_at
    ON bibliographic_reference;
CREATE TRIGGER bibliographic_reference_set_updated_at
BEFORE UPDATE ON bibliographic_reference
FOR EACH ROW EXECUTE FUNCTION set_universal_entities_updated_at();

DO $$
DECLARE
    target record;
    constraint_name text;
    referenced_table text;
BEGIN
    FOR target IN
        SELECT
            relation.relname AS table_name,
            attribute.attname AS column_name
        FROM pg_class AS relation
        JOIN pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        JOIN pg_attribute AS attribute
          ON attribute.attrelid = relation.oid
        WHERE namespace.nspname = current_schema()
          AND relation.relkind IN ('r', 'p')
          AND attribute.attnum > 0
          AND NOT attribute.attisdropped
          AND attribute.attname IN (
              'media_gallery_id',
              'bibliographic_reference_id',
              'media_asset_id',
              'tree_media_asset_id'
          )
          AND relation.relname NOT IN (
              'media_asset',
              'media_asset_annotation_version',
              'universal_entity_bibliography'
          )
    LOOP
        referenced_table := CASE target.column_name
            WHEN 'media_gallery_id' THEN 'media_gallery'
            WHEN 'bibliographic_reference_id' THEN 'bibliographic_reference'
            ELSE 'media_asset'
        END;
        constraint_name := 'universal_fk_' ||
            substr(md5(target.table_name || ':' || target.column_name), 1, 24);

        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = to_regclass(target.table_name)
              AND conname = constraint_name
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %I (id) ON UPDATE RESTRICT ON DELETE RESTRICT',
                target.table_name,
                constraint_name,
                target.column_name,
                referenced_table
            );
        END IF;
    END LOOP;

    FOR target IN
        SELECT
            relation.relname AS table_name
        FROM pg_class AS relation
        JOIN pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        JOIN pg_attribute AS gallery_column
          ON gallery_column.attrelid = relation.oid
         AND gallery_column.attname = 'media_gallery_id'
         AND gallery_column.attnum > 0
         AND NOT gallery_column.attisdropped
        JOIN pg_attribute AS id_column
          ON id_column.attrelid = relation.oid
         AND id_column.attname = 'id'
         AND id_column.attnum > 0
         AND NOT id_column.attisdropped
        WHERE namespace.nspname = current_schema()
          AND relation.relkind IN ('r', 'p')
          AND relation.relname <> 'media_asset'
    LOOP
        constraint_name := 'universal_gallery_parent_' ||
            substr(md5(target.table_name), 1, 16);
        IF NOT EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgrelid = to_regclass(target.table_name)
              AND tgname = constraint_name
              AND NOT tgisinternal
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER %I BEFORE INSERT OR UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION validate_media_gallery_parent()',
                constraint_name,
                target.table_name
            );
        END IF;
    END LOOP;
END;
$$;

CREATE OR REPLACE VIEW media_gallery_assets AS
SELECT
    gallery.id AS media_gallery_id,
    gallery.parent_entity_type,
    gallery.parent_entity_id,
    gallery.gallery_status,
    asset.id AS media_asset_id,
    asset.asset_type,
    asset.rights_statement_uri,
    asset.iiif_service_uri,
    asset.iiif_manifest_uri,
    asset_annotation.version_number AS annotation_version,
    asset_annotation.annotation_layer
FROM media_gallery AS gallery
LEFT JOIN media_asset AS asset
  ON asset.media_gallery_id = gallery.id
LEFT JOIN media_asset_current_annotation AS asset_annotation
  ON asset_annotation.media_asset_id = asset.id;
