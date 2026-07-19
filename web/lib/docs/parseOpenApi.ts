import {
  HTTP_METHODS,
  isReferenceObject,
  type HttpMethod,
  type OpenAPIDocument,
  type OperationObject,
  type ParameterObject,
  type SchemaOrRef,
} from "@/lib/docs/openapiTypes";
import {
  schemaToFieldRows,
  successResponseSchema,
  type SchemaFieldRow,
} from "@/lib/docs/resolveSchema";

export type DocsParameter = {
  name: string;
  in: ParameterObject["in"];
  type: string;
  required: boolean;
  description: string;
};

export type DocsEndpoint = {
  id: string;
  method: HttpMethod;
  path: string;
  summary: string;
  tag: string;
  parameters: DocsParameter[];
  responseFields: SchemaFieldRow[];
  responseTitle: string;
  curl: string;
};

export type DocsTagGroup = {
  tag: string;
  endpoints: DocsEndpoint[];
};

function paramType(schema: SchemaOrRef | undefined): string {
  if (!schema) {
    return "unknown";
  }
  if (isReferenceObject(schema)) {
    const name = schema.$ref.split("/").pop();
    return name ?? "ref";
  }
  if (schema.enum?.length) {
    return schema.enum.map((v) => JSON.stringify(v)).join(" | ");
  }
  if (Array.isArray(schema.type)) {
    return schema.type.join(" | ");
  }
  return schema.type ?? "unknown";
}

function slugify(path: string, method: string): string {
  return `${method}-${path}`
    .toLowerCase()
    .replace(/[{}]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function sampleValue(name: string, type: string, location: string): string {
  if (name === "network") {
    return "mainnet";
  }
  if (name === "limit" || name === "per_page") {
    return "25";
  }
  if (name === "page") {
    return "1";
  }
  if (name === "before" || name === "from" || name === "to") {
    return "0";
  }
  if (name === "metric") {
    return "difficulty";
  }
  if (type.includes("integer") || type === "number") {
    return "0";
  }
  if (location === "path") {
    return `{${name}}`;
  }
  return "…";
}

export function buildCurl(
  origin: string,
  path: string,
  parameters: DocsParameter[],
): string {
  let resolved = path;
  const query: string[] = [];
  for (const p of parameters) {
    const sample = sampleValue(p.name, p.type, p.in);
    if (p.in === "path") {
      const encoded =
        sample.startsWith("{") && sample.endsWith("}")
          ? sample
          : encodeURIComponent(sample);
      resolved = resolved.replace(`{${p.name}}`, encoded);
    } else if (p.in === "query" && p.required) {
      query.push(`${encodeURIComponent(p.name)}=${encodeURIComponent(sample)}`);
    }
  }
  // Prefer mainnet sample even if path still has {network}
  resolved = resolved.replace("{network}", "mainnet");
  const url = `${origin.replace(/\/$/, "")}${resolved}${
    query.length ? `?${query.join("&")}` : ""
  }`;
  return `curl -sS '${url}'`;
}

function collectParameters(
  pathParams: ParameterObject[] | undefined,
  opParams: ParameterObject[] | undefined,
): DocsParameter[] {
  const merged = [...(pathParams ?? []), ...(opParams ?? [])];
  const byKey = new Map<string, DocsParameter>();
  for (const p of merged) {
    byKey.set(`${p.in}:${p.name}`, {
      name: p.name,
      in: p.in,
      type: paramType(p.schema),
      required: p.required ?? p.in === "path",
      description: p.description ?? "",
    });
  }
  return [...byKey.values()];
}

function responseTitle(doc: OpenAPIDocument, op: OperationObject): string {
  const schema = successResponseSchema(doc, op.responses);
  if (!schema) {
    return "(untyped)";
  }
  if (isReferenceObject(schema)) {
    return schema.$ref.split("/").pop() ?? "Response";
  }
  if (schema.type === "array" && schema.items) {
    if (isReferenceObject(schema.items)) {
      return `${schema.items.$ref.split("/").pop() ?? "Item"}[]`;
    }
    return "array";
  }
  if (schema.title) {
    return schema.title;
  }
  if (Array.isArray(schema.type)) {
    return schema.type.join(" | ");
  }
  return schema.type ?? "Response";
}

export function parseOpenApiDocument(
  doc: OpenAPIDocument,
  origin: string,
): DocsTagGroup[] {
  const endpoints: DocsEndpoint[] = [];

  for (const [path, item] of Object.entries(doc.paths ?? {})) {
    for (const method of HTTP_METHODS) {
      const op = item[method];
      if (!op) {
        continue;
      }
      const tag = op.tags?.[0] ?? "default";
      const parameters = collectParameters(item.parameters, op.parameters);
      const responseSchema = successResponseSchema(doc, op.responses);
      const responseFields = schemaToFieldRows(doc, responseSchema);
      endpoints.push({
        id: slugify(path, method),
        method,
        path,
        summary: op.summary ?? op.description ?? "",
        tag,
        parameters,
        responseFields,
        responseTitle: responseTitle(doc, op),
        curl: buildCurl(origin, path, parameters),
      });
    }
  }

  endpoints.sort((a, b) => {
    if (a.tag !== b.tag) {
      return a.tag.localeCompare(b.tag);
    }
    if (a.path !== b.path) {
      return a.path.localeCompare(b.path);
    }
    return a.method.localeCompare(b.method);
  });

  const groups = new Map<string, DocsEndpoint[]>();
  for (const ep of endpoints) {
    const list = groups.get(ep.tag) ?? [];
    list.push(ep);
    groups.set(ep.tag, list);
  }

  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([tag, eps]) => ({
      tag,
      endpoints: eps,
    }));
}

export function isOpenAPIDocument(value: unknown): value is OpenAPIDocument {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const v = value as Record<string, unknown>;
  return (
    typeof v.openapi === "string" &&
    typeof v.info === "object" &&
    v.info !== null &&
    typeof v.paths === "object" &&
    v.paths !== null
  );
}
