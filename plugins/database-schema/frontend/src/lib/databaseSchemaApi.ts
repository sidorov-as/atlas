// Typed client for the facet-owned CRUD endpoint
// (`/api/plugins/atlas.database-schema/resources/{entityId}/schema` — a
// plugin-owned endpoint, not part of `frontend/lib/entities`'s core Entity
// Service wrappers, since the facet's data and lifecycle are independent of
// Resource's own kind).
import { ApiError, apiJson } from 'frontend/lib/api'

export type DatabaseSchemaDialect = 'postgresql' | 'mysql' | 'mssql'
export type ParseStatus = 'ok' | 'failed'

// Mirrors `parser.py`'s tbls-compatible output shape
// (`parsed_schema` targets the tbls-*json* shape) — the documented
// JSON-input subset, not tbls' runtime-computed Go structs. PK/FK-ness lives
// in `constraints[]`/`relations[]`, not on the column itself.
//
// Unlike the facet's own top-level fields, these keys stay snake_case on the
// wire: `DatabaseSchemaOut.parsed_schema` is typed as a plain `dict` in the
// backend schema (api/schemas.py), so `CamelModel` only camel-cases the
// facet's own fields (`sourceSql`, `parseStatus`, ...) — it can't see inside
// an opaque dict to camel-case `parser.py`'s tbls-shaped keys.
export interface ParsedSchemaColumn {
  name: string
  type: string
  nullable: boolean
  default: string | null
}

export interface ParsedSchemaIndex {
  name: string
  def: string
  table: string
  columns: string[]
}

export type ParsedSchemaConstraintType = 'PRIMARY KEY' | 'FOREIGN KEY' | 'UNIQUE' | 'CHECK'

export interface ParsedSchemaConstraint {
  name: string
  type: ParsedSchemaConstraintType
  def: string
  table: string
  columns: string[]
  referenced_table: string | null
  referenced_columns: string[] | null
}

export interface ParsedSchemaTable {
  name: string
  type: string
  columns: ParsedSchemaColumn[]
  indexes: ParsedSchemaIndex[]
  constraints: ParsedSchemaConstraint[]
}

export type ParsedSchemaCardinality = 'many_to_one' | 'one_to_one'

export interface ParsedSchemaRelation {
  table: string
  columns: string[]
  parent_table: string
  parent_columns: string[]
  cardinality: ParsedSchemaCardinality
}

export interface ParsedSchemaEnum {
  name: string
  values: string[]
}

export interface ParsedSchema {
  tables: ParsedSchemaTable[]
  relations?: ParsedSchemaRelation[]
  enums?: ParsedSchemaEnum[]
}

/** Old-shape `parsed_schema` rows (pre-sqlglot) never had a top-level
 * `relations` key; the new parser always emits one (possibly empty). A
 * facet last saved before the tbls-shape change stays old-shape until its next
 * Schema-tab save (no backfill). */
export function isUpgradedSchema(schema: ParsedSchema): boolean {
  return Array.isArray(schema.relations)
}

export interface DatabaseSchemaFacet {
  entityId: string
  dialect: DatabaseSchemaDialect
  sourceSql: string
  parsedSchema: ParsedSchema
  parseStatus: ParseStatus
}

function url(entityId: number | string): string {
  return `/api/plugins/atlas.database-schema/resources/${entityId}/schema/`
}

export const databaseSchemaApi = {
  get: (entityId: number | string) => apiJson<DatabaseSchemaFacet>(url(entityId)),
  create: (entityId: number | string, sourceSql: string, dialect: DatabaseSchemaDialect) =>
    apiJson<DatabaseSchemaFacet>(url(entityId), { method: 'POST', body: JSON.stringify({ sourceSql, dialect }) }),
  update: (entityId: number | string, sourceSql: string, dialect: DatabaseSchemaDialect) =>
    apiJson<DatabaseSchemaFacet>(url(entityId), { method: 'PATCH', body: JSON.stringify({ sourceSql, dialect }) }),
}

/** No facet has been attached to this entity yet — a normal, expected state (not an error). */
export function isNoFacetFound(err: unknown): boolean {
  return err instanceof ApiError && err.status === 404
}
