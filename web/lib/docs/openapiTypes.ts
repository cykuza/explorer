/** Hand-rolled OpenAPI 3 subset used by the branded `/docs` page. */

export type ReferenceObject = {
  $ref: string;
};

export type SchemaObject = {
  type?: string | string[];
  format?: string;
  title?: string;
  description?: string;
  properties?: Record<string, SchemaOrRef>;
  items?: SchemaOrRef;
  required?: string[];
  enum?: unknown[];
  anyOf?: SchemaOrRef[];
  oneOf?: SchemaOrRef[];
  allOf?: SchemaOrRef[];
  additionalProperties?: boolean | SchemaOrRef;
  nullable?: boolean;
  default?: unknown;
};

export type SchemaOrRef = SchemaObject | ReferenceObject;

export type ParameterObject = {
  name: string;
  in: "query" | "header" | "path" | "cookie";
  description?: string;
  required?: boolean;
  deprecated?: boolean;
  schema?: SchemaOrRef;
};

export type MediaTypeObject = {
  schema?: SchemaOrRef;
};

export type ResponseObject = {
  description?: string;
  content?: Record<string, MediaTypeObject>;
};

export type OperationObject = {
  tags?: string[];
  summary?: string;
  description?: string;
  operationId?: string;
  parameters?: ParameterObject[];
  responses?: Record<string, ResponseObject | ReferenceObject>;
  deprecated?: boolean;
};

export type PathItem = {
  summary?: string;
  description?: string;
  parameters?: ParameterObject[];
  get?: OperationObject;
  put?: OperationObject;
  post?: OperationObject;
  delete?: OperationObject;
  options?: OperationObject;
  head?: OperationObject;
  patch?: OperationObject;
  trace?: OperationObject;
};

export type ComponentsObject = {
  schemas?: Record<string, SchemaOrRef>;
};

export type OpenAPIDocument = {
  openapi: string;
  info: {
    title: string;
    version: string;
    description?: string;
  };
  paths: Record<string, PathItem>;
  components?: ComponentsObject;
};

export type HttpMethod =
  | "get"
  | "put"
  | "post"
  | "delete"
  | "options"
  | "head"
  | "patch"
  | "trace";

export const HTTP_METHODS: HttpMethod[] = [
  "get",
  "put",
  "post",
  "delete",
  "options",
  "head",
  "patch",
  "trace",
];

export function isReferenceObject(value: unknown): value is ReferenceObject {
  return (
    typeof value === "object" &&
    value !== null &&
    "$ref" in value &&
    typeof (value as ReferenceObject).$ref === "string"
  );
}

export function isSchemaObject(value: unknown): value is SchemaObject {
  return typeof value === "object" && value !== null && !isReferenceObject(value);
}
