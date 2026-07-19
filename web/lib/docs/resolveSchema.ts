import { annotateType } from "@/lib/docs/moneyFields";
import {
  isReferenceObject,
  isSchemaObject,
  type OpenAPIDocument,
  type SchemaObject,
  type SchemaOrRef,
} from "@/lib/docs/openapiTypes";

export type SchemaFieldRow = {
  name: string;
  type: string;
  description: string;
  depth: number;
};

const MAX_DEPTH = 6;

function schemaNameFromRef(ref: string): string | null {
  const prefix = "#/components/schemas/";
  if (!ref.startsWith(prefix)) {
    return null;
  }
  return decodeURIComponent(ref.slice(prefix.length));
}

export function resolveSchema(
  doc: OpenAPIDocument,
  schemaOrRef: SchemaOrRef | undefined,
  seen: Set<string> = new Set(),
): SchemaObject | null {
  if (!schemaOrRef) {
    return null;
  }
  if (isReferenceObject(schemaOrRef)) {
    const name = schemaNameFromRef(schemaOrRef.$ref);
    if (!name) {
      return null;
    }
    if (seen.has(name)) {
      return { type: "object", description: `circular ref → ${name}` };
    }
    const next = doc.components?.schemas?.[name];
    if (!next) {
      return { type: "object", description: `unresolved ref → ${name}` };
    }
    const nextSeen = new Set(seen);
    nextSeen.add(name);
    const resolved = resolveSchema(doc, next, nextSeen);
    if (!resolved) {
      return null;
    }
    return { ...resolved, title: resolved.title ?? name };
  }
  if (!isSchemaObject(schemaOrRef)) {
    return null;
  }
  return schemaOrRef;
}

function typeLabel(schema: SchemaObject): string {
  if (schema.enum && schema.enum.length > 0) {
    return schema.enum.map((v) => JSON.stringify(v)).join(" | ");
  }
  if (schema.anyOf?.length) {
    return "anyOf";
  }
  if (schema.oneOf?.length) {
    return "oneOf";
  }
  if (schema.allOf?.length) {
    return "allOf";
  }
  const t = schema.type;
  if (Array.isArray(t)) {
    return t.join(" | ");
  }
  if (t === "array") {
    return "array";
  }
  if (t) {
    return t;
  }
  if (schema.properties) {
    return "object";
  }
  if (schema.additionalProperties !== undefined) {
    return "object";
  }
  return "unknown";
}

function mergeAllOf(
  doc: OpenAPIDocument,
  parts: SchemaOrRef[],
  seen: Set<string>,
): SchemaObject {
  const merged: SchemaObject = { type: "object", properties: {}, required: [] };
  for (const part of parts) {
    const resolved = resolveSchema(doc, part, seen);
    if (!resolved) {
      continue;
    }
    if (resolved.properties) {
      merged.properties = { ...merged.properties, ...resolved.properties };
    }
    if (resolved.required) {
      merged.required = [...(merged.required ?? []), ...resolved.required];
    }
    if (resolved.description && !merged.description) {
      merged.description = resolved.description;
    }
  }
  return merged;
}

export function schemaToFieldRows(
  doc: OpenAPIDocument,
  schemaOrRef: SchemaOrRef | undefined,
  options?: { prefix?: string; depth?: number; seen?: Set<string> },
): SchemaFieldRow[] {
  const prefix = options?.prefix ?? "";
  const depth = options?.depth ?? 0;
  const seen = options?.seen ?? new Set();
  if (depth > MAX_DEPTH) {
    return [
      {
        name: prefix || "(root)",
        type: "…",
        description: "max depth reached",
        depth,
      },
    ];
  }

  let schema = resolveSchema(doc, schemaOrRef, seen);
  if (!schema) {
    return [];
  }

  if (schema.allOf?.length) {
    schema = mergeAllOf(doc, schema.allOf, seen);
  }

  const rows: SchemaFieldRow[] = [];
  const label = typeLabel(schema);

  if (schema.properties) {
    const required = new Set(schema.required ?? []);
    for (const [key, prop] of Object.entries(schema.properties)) {
      const name = prefix ? `${prefix}.${key}` : key;
      const resolved = resolveSchema(doc, prop, seen);
      if (!resolved) {
        rows.push({
          name,
          type: "unknown",
          description: "",
          depth,
        });
        continue;
      }

      let propSchema = resolved;
      if (propSchema.allOf?.length) {
        propSchema = mergeAllOf(doc, propSchema.allOf, seen);
      }

      const propType = typeLabel(propSchema);
      const annotated = annotateType(key, propType);
      const reqNote = required.has(key) ? "" : " optional";
      const desc =
        propSchema.description ??
        propSchema.title ??
        (isReferenceObject(prop)
          ? (schemaNameFromRef(prop.$ref) ?? "")
          : "");

      if (propType === "array" && propSchema.items) {
        const item = resolveSchema(doc, propSchema.items, seen);
        const itemType = item ? typeLabel(item) : "unknown";
        const itemAnnotated = annotateType(key, itemType);
        rows.push({
          name,
          type: `array<${itemAnnotated}>${reqNote}`,
          description: desc,
          depth,
        });
        if (item?.properties || item?.allOf) {
          rows.push(
            ...schemaToFieldRows(doc, propSchema.items, {
              prefix: `${name}[]`,
              depth: depth + 1,
              seen,
            }),
          );
        }
        continue;
      }

      if (propSchema.properties || propSchema.allOf) {
        rows.push({
          name,
          type: `${annotated}${reqNote}`,
          description: desc,
          depth,
        });
        rows.push(
          ...schemaToFieldRows(doc, propSchema, {
            prefix: name,
            depth: depth + 1,
            seen,
          }),
        );
        continue;
      }

      rows.push({
        name,
        type: `${annotated}${reqNote}`,
        description: desc,
        depth,
      });
    }
    return rows;
  }

  if (label === "array" && schema.items) {
    const item = resolveSchema(doc, schema.items, seen);
    const itemType = item ? typeLabel(item) : "unknown";
    rows.push({
      name: prefix || "(root)",
      type: `array<${annotateType(prefix || "items", itemType)}>`,
      description: schema.description ?? schema.title ?? "",
      depth,
    });
    if (item?.properties || item?.allOf) {
      rows.push(
        ...schemaToFieldRows(doc, schema.items, {
          prefix: prefix ? `${prefix}[]` : "[]",
          depth: depth + 1,
          seen,
        }),
      );
    }
    return rows;
  }

  rows.push({
    name: prefix || (schema.title ?? "(root)"),
    type: annotateType(prefix || schema.title || "", label),
    description: schema.description ?? "",
    depth,
  });
  return rows;
}

export function successResponseSchema(
  doc: OpenAPIDocument,
  responses: Record<string, unknown> | undefined,
): SchemaOrRef | undefined {
  if (!responses) {
    return undefined;
  }
  const ok =
    responses["200"] ??
    responses["201"] ??
    responses["default"];
  if (!ok || typeof ok !== "object") {
    return undefined;
  }
  if (isReferenceObject(ok)) {
    return undefined;
  }
  const content = (ok as { content?: Record<string, { schema?: SchemaOrRef }> })
    .content;
  if (!content) {
    return undefined;
  }
  const json =
    content["application/json"] ??
    content["application/problem+json"] ??
    Object.values(content)[0];
  return json?.schema;
}
