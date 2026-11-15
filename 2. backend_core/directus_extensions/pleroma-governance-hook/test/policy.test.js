import test from "node:test";
import assert from "node:assert/strict";

import register, { isUuid } from "../index.js";

const actorId = "550e8400-e29b-41d4-a716-446655440000";

function createHook(env = {}) {
  const filters = new Map();
  const auditRows = [];
  const tables = {
    sites: [
      {
        id: "123e4567-e89b-12d3-a456-426614174000",
        title: "Test site",
      },
    ],
  };
  const database = (table) => ({
    insert: async (rows) => {
      auditRows.push(...(Array.isArray(rows) ? rows : [rows]));
    },
    whereIn: (_field, keys) => ({
      select: async () => tables[table].filter((row) => keys.includes(row.id)),
    }),
  });
  register(
    { filter: (event, handler) => filters.set(event, handler) },
    { env, logger: { info() {} } },
  );
  const context = {
    accountability: { user: actorId, role: "contributor-role", admin: false },
    database,
  };
  return { filters, auditRows, context };
}

test("validates UUID actors", () => {
  assert.equal(isUuid(actorId), true);
  assert.equal(isUuid("anonymous"), false);
});

test("create writes audit in the transaction and removes justification metadata", async () => {
  const { filters, auditRows, context } = createHook();
  const result = await filters.get("items.create")(
    { title: "New site", _pleroma_justification: "Initial data entry" },
    { collection: "sites" },
    context,
  );

  assert.equal(isUuid(result.id), true);
  assert.equal("_pleroma_justification" in result, false);
  assert.equal(auditRows.length, 1);
  assert.equal(auditRows[0].actor_uuid, actorId);
  assert.equal(auditRows[0].operation_type, "create");
  assert.equal(auditRows[0].previous_state, null);
});

test("updates preserve the previous state in the audit record", async () => {
  const { filters, auditRows, context } = createHook();
  const result = await filters.get("items.update")(
    { title: "Updated site", _pleroma_justification: "Corrected transcription" },
    {
      collection: "sites",
      keys: ["123e4567-e89b-12d3-a456-426614174000"],
    },
    context,
  );

  assert.deepEqual(result, { title: "Updated site" });
  assert.equal(auditRows.length, 1);
  assert.deepEqual(auditRows[0].previous_state, {
    id: "123e4567-e89b-12d3-a456-426614174000",
    title: "Test site",
  });
  assert.equal(auditRows[0].justification, "Corrected transcription");
});

test("rejects anonymous writes, missing reasons, unauthorized publication, and hard deletes", async () => {
  const { filters, context } = createHook();
  await assert.rejects(
    filters.get("items.create")(
      { title: "Site" },
      { collection: "sites" },
      context,
    ),
    /justification/,
  );
  await assert.rejects(
    filters.get("items.create")(
      { title: "Site", _pleroma_justification: "Reason" },
      { collection: "sites" },
      { accountability: { user: null }, database: context.database },
    ),
    /authenticated actor UUID/,
  );
  await assert.rejects(
    filters.get("items.update")(
      { status: "published", _pleroma_justification: "Ready" },
      {
        collection: "sites",
        keys: ["123e4567-e89b-12d3-a456-426614174000"],
      },
      context,
    ),
    /Domain Specialist/,
  );
  assert.throws(
    () => filters.get("items.delete")([], { collection: "sites" }, context),
    /Hard deletes are disabled/,
  );
});
