import { randomUUID } from "node:crypto";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const JUSTIFICATION_FIELD = "_pleroma_justification";
const SYSTEM_COLLECTIONS = new Set([
  "activity",
  "collections",
  "comments",
  "dashboards",
  "extensions",
  "fields",
  "files",
  "flows",
  "folders",
  "notifications",
  "operations",
  "panels",
  "permissions",
  "presets",
  "relations",
  "revisions",
  "roles",
  "sessions",
  "settings",
  "translations",
  "users",
  "webhooks",
]);

export function isUuid(value) {
  return typeof value === "string" && UUID_PATTERN.test(value);
}

function isSystemCollection(collection) {
  return collection.startsWith("directus_") || SYSTEM_COLLECTIONS.has(collection);
}

function parseRoleIds(value) {
  return new Set(
    (value ?? "")
      .split(",")
      .map((roleId) => roleId.trim())
      .filter(Boolean),
  );
}

function requireWriteContext(context) {
  const accountability = context?.accountability;
  if (!isUuid(accountability?.user)) {
    throw new Error("Pleroma writes require an authenticated actor UUID.");
  }
  if (typeof context?.database !== "function") {
    throw new Error("Pleroma governance hook requires the current database transaction.");
  }
  return accountability;
}

function takeJustification(record) {
  if (
    typeof record[JUSTIFICATION_FIELD] !== "string" ||
    record[JUSTIFICATION_FIELD].trim().length === 0
  ) {
    throw new Error(
      `Every Pleroma write requires a non-empty ${JUSTIFICATION_FIELD} value.`,
    );
  }
  const justification = record[JUSTIFICATION_FIELD].trim();
  const cleanRecord = { ...record };
  delete cleanRecord[JUSTIFICATION_FIELD];
  return { cleanRecord, justification };
}

function assertCanPublish(payload, accountability, env) {
  const publicationField = env.PLEROMA_PUBLICATION_FIELD ?? "status";
  if (
    typeof payload[publicationField] !== "string" ||
    payload[publicationField].toLowerCase() !== "published"
  ) {
    return;
  }

  const publisherRoles = parseRoleIds(env.PLEROMA_PUBLISHER_ROLE_IDS);
  if (!accountability.admin && !publisherRoles.has(accountability.role)) {
    throw new Error("Publishing requires a Domain Specialist or Principal Investigator role.");
  }
}

function makeAuditRow({
  actorId,
  collection,
  recordId,
  operation,
  previousState,
  justification,
}) {
  return {
    actor_uuid: actorId,
    recorded_at: new Date(),
    operation_type: operation,
    collection_name: collection,
    record_key: recordId,
    previous_state: previousState,
    justification,
  };
}

export default function register({ filter }, { env = {}, logger }) {
  const auditTable = env.PLEROMA_AUDIT_TABLE ?? "pleroma_audit_log";
  const primaryKey = env.PLEROMA_PRIMARY_KEY_FIELD ?? "id";
  const excludedCollections = new Set(
    (env.PLEROMA_UNAUDITED_COLLECTIONS ?? "")
      .split(",")
      .map((collection) => collection.trim())
      .filter(Boolean),
  );

  function isGoverned(collection) {
    return (
      typeof collection === "string" &&
      collection !== auditTable &&
      !isSystemCollection(collection) &&
      !excludedCollections.has(collection)
    );
  }

  function rejectAuditMutation(collection) {
    if (collection === auditTable) {
      throw new Error("The Pleroma audit log is append-only and cannot be changed through Directus.");
    }
  }

  filter("items.create", async (payload, meta, context) => {
    const collection = meta?.collection;
    rejectAuditMutation(collection);
    if (!isGoverned(collection)) return payload;

    const accountability = requireWriteContext(context);
    const records = Array.isArray(payload) ? payload : [payload];
    if (records.length === 0 || records.some((record) => !record || typeof record !== "object" || Array.isArray(record))) {
      throw new Error("Pleroma create payload must contain one or more record objects.");
    }

    const transaction = context.database;
    const auditRows = [];
    const cleanRecords = records.map((record) => {
      const { cleanRecord, justification } = takeJustification(record);
      const id = cleanRecord[primaryKey] ?? randomUUID();
      if (!isUuid(id)) {
        throw new Error(`Pleroma record ${primaryKey} must be a UUID.`);
      }
      cleanRecord[primaryKey] = id;
      assertCanPublish(cleanRecord, accountability, env);
      auditRows.push(
        makeAuditRow({
          actorId: accountability.user,
          collection,
          recordId: id,
          operation: "create",
          previousState: null,
          justification,
        }),
      );
      return cleanRecord;
    });

    await transaction(auditTable).insert(auditRows);
    return Array.isArray(payload) ? cleanRecords : cleanRecords[0];
  });

  filter("items.update", async (payload, meta, context) => {
    const collection = meta?.collection;
    rejectAuditMutation(collection);
    if (!isGoverned(collection)) return payload;

    const accountability = requireWriteContext(context);
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new Error("Pleroma update payload must be a record object.");
    }
    if (Object.hasOwn(payload, primaryKey)) {
      throw new Error(`Pleroma record ${primaryKey} cannot be changed.`);
    }
    const keys = meta?.keys;
    if (!Array.isArray(keys) || keys.length === 0 || keys.some((key) => !isUuid(key))) {
      throw new Error("Pleroma updates require one or more UUID record keys.");
    }

    const { cleanRecord, justification } = takeJustification(payload);
    assertCanPublish(cleanRecord, accountability, env);

    const transaction = context.database;
    const previousStates = await transaction(collection)
      .whereIn(primaryKey, keys)
      .select("*");
    if (previousStates.length !== keys.length) {
      throw new Error("Pleroma update audit failed: one or more target records were not found.");
    }

    await transaction(auditTable).insert(
      previousStates.map((previousState) =>
        makeAuditRow({
          actorId: accountability.user,
          collection,
          recordId: previousState[primaryKey],
          operation: "update",
          previousState,
          justification,
        }),
      ),
    );
    return cleanRecord;
  });

  filter("items.delete", (payload, meta) => {
    const collection = meta?.collection;
    rejectAuditMutation(collection);
    if (isGoverned(collection)) {
      throw new Error(
        "Hard deletes are disabled for Pleroma records. Use a reviewed correction or tombstone workflow.",
      );
    }
    return payload;
  });

  logger?.info?.(
    `Pleroma governance hook registered (audit table: ${auditTable}).`,
  );
}
