// Mirrors the camelCase envelope produced by backend/apps/catalog/api/schemas.py.

export interface FlowStepTransition {
  id: string
  label?: string
}

/** Gravity UI `Label` theme tokens a plain Step node's color may take. */
export type FlowStepLabelTheme = 'success' | 'danger' | 'warning' | 'info' | 'utility' | 'normal'

/** A step's `query_ref` — a point-in-time snapshot referencing an `atlas_plugin_apis` Endpoint. `method`/`path` are captured when the reference is chosen, never re-fetched. `summary` is likewise a pick-time snapshot of the Endpoint's own summary, optional — empty string allowed — since the Endpoint's own `summary` is itself optional; feeds the Call node's card subtitle. */
export interface FlowStepQueryRef {
  api: string
  endpoint: string
  method: string
  path: string
  summary?: string
}

/** A step's `event_ref` — mirrors `FlowStepQueryRef`, referencing an Operation instead. */
export interface FlowStepEventRef {
  api: string
  operation: string
  direction: string
  channel: string
  summary?: string
}

/** Live status of a step's `query_ref`/`event_ref`, resolved at read time — never stored on the step itself and never a replacement for its snapshot. `deprecated` is present only for a `query_ref`-backed step (an `ApiOperation` has no such field). */
export interface FlowStepRefStatus {
  /** Absent for a `flow_ref` step — a Flow has no `status`/`deprecated` lifecycle of its own; entry presence alone (see `name` below) is its "does it still resolve" signal. */
  status?: 'active' | 'removed'
  deprecated?: boolean
  /** Live values that disagree with the step's own `query_ref`/`event_ref` snapshot — each key present only when it actually drifted (presence itself is the drift signal). `direction`/`channel_address` are `event_ref`-only (an Endpoint's `method`/`path` is its own upsert identity and cannot drift by construction). `summary` applies to both `query_ref` and `event_ref` steps, independent of the other fields — an Endpoint's/Operation's `summary` is an ordinary mutable field with no such identity guarantee. */
  live?: { direction?: string; channel_address?: string; summary?: string }
  /** An `entity_ref` step's referenced entity's current `title`/`description` — the only source an entity-backed node's rendered title/subtitle draws from. Never present for a `query_ref`/`event_ref` step. */
  title?: string
  description?: string
  /** A `flow_ref` step's referenced Flow's current `name` — the only source a Flow node's rendered title draws from. Shares `description` above with the `entity_ref` case; a Flow has no `status`/`deprecated` of its own, so absence of this entry entirely (not a `status` value) is the "target no longer exists" signal. */
  name?: string
}

/** The Flow JSON step grammar — kept here (not `@atlas/plugin-flows`) since `FlowEntity` below needs it and core may reference `FlowEntity` independent of whether `atlas.flows` is selected. `@atlas/plugin-flows`'s own `lib/flowLayout.ts` re-exports this type for its internal call sites. */
export interface FlowStep {
  id: string
  title?: string
  summary?: string
  entity_ref?: string | null
  next_step?: FlowStepTransition | null
  next_steps?: FlowStepTransition[]
  /** Manually placed canvas position; absent steps fall back to ELK autolayout. */
  position?: { x: number; y: number }
  /** @deprecated Replaced by `color`; still accepted on read so an unmigrated flow keeps rendering, never written by the editor. */
  label_theme?: FlowStepLabelTheme
  /** Plain Step node color — a key into `flowNodePalette.ts`'s `FLOW_NODE_SWATCHES`; ignored when `entity_ref` or `external_label` is set. */
  color?: FlowStepLabelTheme
  /** Plain Step node icon — a `@gravity-ui/icons` component name; falls back to Step's default icon when unset. */
  icon?: string
  /** Plain Step node chip label — free text, author-chosen; falls back to "Step" when blank/unset. */
  type_label?: string
  /** Out-of-catalog reference label; mutually exclusive with `entity_ref`, `query_ref`, and `event_ref`. */
  external_label?: string
  /** Endpoint reference (Query step); mutually exclusive with `entity_ref`, `external_label`, and `event_ref`. */
  query_ref?: FlowStepQueryRef | null
  /** Operation reference (Event step); mutually exclusive with `entity_ref`, `external_label`, and `query_ref`. */
  event_ref?: FlowStepEventRef | null
  /** Flow reference (Flow step) — another Flow's id; mutually exclusive with every other ref field. Ref-backed like `entity_ref`/`query_ref`/`event_ref`: a step carrying this never also carries `title`/`summary`. */
  flow_ref?: number | null
  /** External URL (Link step); mutually exclusive with every ref field above. Freeform like `external_label`/plain Step: `title`/`summary` are the author's own, optional text — falls back to `link_url` itself when `title` is unset, never to the step's own opaque id. */
  link_url?: string | null
}

/** Mirrors `ConflictRecord.REASON_CHOICES` — why a rival YAML/manual claim was rejected in favor of the entity currently holding the ref. */
export type ConflictReason = 'manual_entity' | 'other_repository' | 'removed_entity'

export interface LinkOut {
  url: string
  title: string
  description: string
  type: string
}

export interface Metadata {
  name: string
  title: string
  description: string
  documentation: string
  labels: Record<string, string>
  tags: string[]
  tagColors: Record<string, string>
  links: LinkOut[]
}

/** Fixed tag color presets; mirrors `apps/catalog/models/tag.py`'s `TAG_PALETTE`. */
export const TAG_PALETTE = ['gray', 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink'] as const

export type TagColorKey = (typeof TAG_PALETTE)[number]

/** Mirrors `apps/catalog/models/tag.py`'s `DEFAULT_TAG_COLOR` — used when a tag is missing from `tagColors` or holds an unrecognized/legacy value. */
export const DEFAULT_TAG_COLOR: TagColorKey = 'gray'

/** Maps a stored tag color value to a known palette key, falling back to the default for anything unrecognized (e.g. a pre-migration hex value). */
export function tagColorKey(color: string | undefined): TagColorKey {
  return (TAG_PALETTE as readonly string[]).includes(color ?? '') ? (color as TagColorKey) : DEFAULT_TAG_COLOR
}

export interface Tag {
  id: number
  name: string
  color: string
}

/** Homepage's admin-editable "About this catalog" content. */
export interface CatalogHomeSettings {
  aboutMarkdown: string
}

/** Mirrors the paginated envelope returned by catalog list endpoints. */
export interface Paginated<T> {
  count: number
  numPages: number
  perPage: number
  page: { number: number; objectList: T[] }
}

/** One `EntityAuditRecord`, as shown on the entity detail page's History section. */
export interface HistoryRecord {
  action: 'create' | 'update' | 'delete' | 'remove' | 'revive' | 'purge'
  actor: string | null
  timestamp: string
}

export interface Relation {
  predicate: string
  target: string
  targetKind: string
  targetId: string
  // Target's current lifecycle status (surface a
  // removed or deprecated target's status).
  status: 'active' | 'removed'
  deprecated: boolean
}

/** A directed, declared runtime interaction, distinct from derived catalog relations. */
export interface ArchitectureRelationship {
  id: number
  source: string
  sourceKind: string
  sourceId: string
  sourceStatus: 'active' | 'removed'
  sourceDeprecated: boolean
  target: string
  targetKind: string
  targetId: string
  targetStatus: 'active' | 'removed'
  targetDeprecated: boolean
  label: string
  technology: string
  interactionKind: 'synchronous' | 'asynchronous' | 'data-access' | 'manual'
  tags: string[]
  origin: 'manual' | 'yaml'
}

export type ComponentType = 'service' | 'website' | 'library' | 'worker'
export type ComponentLifecycle = 'experimental' | 'production' | 'deprecated'
export type ResourceType = 'database' | 'cache' | 'bucket' | 'queue' | 'cluster'
export type ApiType = 'openapi' | 'grpc' | 'asyncapi' | 'graphql'
export type GroupType = 'team' | 'business-unit' | 'product-area' | 'root'

/** `CatalogEntity.status` — System/Component/Resource/API only; Group/Actor never leave `active`. */
export type EntityStatus = 'active' | 'removed'

export interface SystemSpec {
  owner: string
  ownerId: string
}

export interface SystemEntity {
  id: string
  apiVersion: string
  kind: 'System'
  metadata: Metadata
  spec: SystemSpec
  status: EntityStatus
  ingestedFrom: string | null
  blockedBy: string | null
  blockedByReason: ConflictReason | null
  capabilities: string[]
}

export interface ComponentSpec {
  type: ComponentType
  lifecycle: ComponentLifecycle
  owner: string
  ownerId: string
  system: string
  systemId: string | null
  providesApis: string[]
  consumesApis: string[]
  dependsOn: string[]
}

export interface ComponentEntity {
  id: string
  apiVersion: string
  kind: 'Component'
  metadata: Metadata
  spec: ComponentSpec
  status: EntityStatus
  ingestedFrom: string | null
  blockedBy: string | null
  blockedByReason: ConflictReason | null
  capabilities: string[]
}

export interface ResourceSpec {
  type: ResourceType
  owner: string
  ownerId: string
  system: string | null
  systemId: string | null
}

export interface ResourceEntity {
  id: string
  apiVersion: string
  kind: 'Resource'
  metadata: Metadata
  spec: ResourceSpec
  status: EntityStatus
  ingestedFrom: string | null
  blockedBy: string | null
  blockedByReason: ConflictReason | null
  capabilities: string[]
}

export type ApiSpecSource = 'none' | 'inline' | 'url'

export interface ApiSpec {
  type: ApiType
  owner: string
  ownerId: string
  system: string
  systemId: string | null
  specSource: ApiSpecSource
  specUrl: string
  specContent: string
  specResolvedAt: string | null
  specResolveFailed: boolean
  endpointsSyncedAt: string | null
  endpointsSyncFailed: boolean
  operationsSyncedAt: string | null
  operationsSyncFailed: boolean
  resolvedBaseUrl: string
  resolvedProtocol: string
}

export interface ApiEntity {
  id: string
  apiVersion: string
  kind: 'API'
  metadata: Metadata
  spec: ApiSpec
  status: EntityStatus
  ingestedFrom: string | null
  blockedBy: string | null
  blockedByReason: ConflictReason | null
  capabilities: string[]
}

/** Not a `CatalogEntity` — no `kind`/`metadata` envelope, no ingestion. */
export interface FlowEntity {
  id: number
  system: string
  name: string
  description: string
  documentation: string
  steps: FlowStep[]
  /** Whether every step's `position` is continuously ELK-recomputed (`true`) or fully manual (`false`) — a persisted, Flow-level binary mode replacing the old per-step "`position` wins if present" merge. */
  autolayoutEnabled: boolean
  /** ELK layout axis, shared by every viewer — no longer a per-viewer `localStorage` preference. */
  layoutDirection: 'LAYOUT_LEFT_RIGHT' | 'LAYOUT_TOP_DOWN'
  /** Persisted, per-Flow layout algorithm choice, shared by every viewer. */
  layoutEngine: 'dagre' | 'elk'
  /** Step id -> live status, for steps with a `query_ref`/`event_ref` whose reference still resolves; a step id absent from this map has no live status (no such ref, an unresolvable reference, or the APIs plugin not installed). */
  refStatus?: Record<string, FlowStepRefStatus>
}

export interface GroupSpec {
  type: GroupType
  members: string[]
  membershipGrants?: EffectiveMembership[]
}

export interface MembershipGrantSummary {
  id: number
  sourceKind: 'manual' | 'provider'
  providerId: string | null
  sourceId: string | null
  subject: string | null
  externalKey: string | null
  legacyUnclassified: boolean
  createdAt: string
  lastConfirmedAt: string
  expiresAt: string | null
  applicable: boolean
}

export interface EffectiveMembership {
  entity: string
  effective: boolean
  grants: MembershipGrantSummary[]
}

export interface GroupEntity {
  id: string
  apiVersion: string
  kind: 'Group'
  metadata: Metadata
  spec: GroupSpec
  capabilities: string[]
}

export interface UserSpec {
  memberOf: string[]
  membershipGrants?: EffectiveMembership[]
  profile: { displayName: string; email: string }
}

export interface UserEntity {
  id: string
  apiVersion: string
  kind: 'User'
  metadata: Metadata
  spec: UserSpec
  capabilities: string[]
}

/** Every Entity Kind whose canonical detail page renders through `EntityDetailShell`. */
export type CatalogEntityUnion = SystemEntity | ComponentEntity | ResourceEntity | ApiEntity | GroupEntity

/** Refs are `kind:name`; this strips the kind prefix for display. */
export function refName(ref: string | null | undefined): string {
  if (!ref) return ''
  const separator = ref.indexOf(':')
  return separator === -1 ? ref : ref.slice(separator + 1)
}
