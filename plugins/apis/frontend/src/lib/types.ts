// Endpoint read shapes — mirrors `atlas_plugin_apis/api/schemas.py`'s
// Endpoint/ServiceEndpointUsage models. `Endpoint` is plugin-owned child data, not a
// `CatalogEntity`, so it doesn't extend `frontend/lib/types`' entity union.

export type EndpointMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS'
export type EndpointStatus = 'active' | 'removed'
export type EndpointParameterLocation = 'path' | 'query' | 'header'

/** Mirrors `EndpointSchemaOut` — a provisional JSON-Schema-like descriptor, not a JSON Schema implementation. */
export interface EndpointSchema {
  type: 'object' | 'array' | 'string' | 'integer' | 'number' | 'boolean' | null
  /** `EndpointSchemaOut.ref` is aliased to `$ref` on the wire. */
  '$ref': string | null
  format: string
  enum: (string | number | boolean)[] | null
  nullable: boolean
  description: string
  properties: Record<string, EndpointSchema>
  required: string[]
  items: EndpointSchema | null
}

export interface EndpointParameter {
  name: string
  location: EndpointParameterLocation
  required: boolean
  description: string
  schema: EndpointSchema | null
}

export interface EndpointBody {
  contentType: string
  schema: EndpointSchema | null
  example: unknown
}

export interface EndpointRequest {
  parameters: EndpointParameter[]
  body: EndpointBody | null
}

export interface EndpointResponseHeader {
  description: string
  schema: EndpointSchema | null
}

export interface EndpointResponse {
  statusCode: string
  description: string
  contentType: string
  schema: EndpointSchema | null
  example: unknown
  headers: Record<string, EndpointResponseHeader>
}

export interface EndpointSecurity {
  type: string
  scheme: string | null
}

export interface Endpoint {
  id: string
  apiId: string
  method: EndpointMethod
  path: string
  operationId: string
  summary: string
  description: string
  deprecated: boolean
  tags: string[]
  request: EndpointRequest
  responses: EndpointResponse[]
  externalDocs: ExternalDocs | null
  security: EndpointSecurity[]
  status: EndpointStatus
  createdAt: string
  updatedAt: string
}

export interface EndpointListFilters {
  method?: EndpointMethod
  tag?: string
  search?: string
  deprecated?: boolean
  status?: EndpointStatus
}

// --- Service <-> Endpoint dependency --------------
// Types for the Linked Services tab.

export interface ServiceSummary {
  id: string
  ref: string
  name: string
  title: string
  /** The Service's owning team; null when it has no owner. */
  team: string | null
  teamId: string | null
  teamName: string | null
  /** The Service's system; null when it has none. */
  system: string | null
  systemId: string | null
  systemName: string | null
}

export interface EndpointService {
  id: string
  service: ServiceSummary
  linkedAt: string
}

// --- Link/unlink and the compact consumers graph ----

export interface EndpointServiceLink {
  id: string
  service: ServiceSummary
  linkedAt: string
  apiRelationCreated: boolean
}

export interface EndpointConsumerSummary {
  id: string
  method: EndpointMethod
  path: string
  status: EndpointStatus
}

/** What the full-screen graphs can group Services by. */
export type ConsumerGroupBy = 'team' | 'system'

/** One team or system holding at least two matching Services (`count` is exact, independent of the page). */
export interface ConsumerGroup {
  id: string
  name: string
  count: number
}

/** Query for the `.../consumers` routes — one page of linked Services, optionally narrowed by `search`. With `groupBy` the response also lists groups and holds only the ungrouped Services; add `groupId` (and `role` for Operations) to page through one group's members. */
export interface ConsumersParams {
  page?: number
  pageSize?: number
  search?: string
  groupBy?: ConsumerGroupBy
  groupId?: string
  role?: OperationRole
}

/** `GET /api/endpoints/{endpointId}/consumers` — one page (default 50) of linked Services. `count` is the total matching `search`, so the graph and the removed-endpoint banner use it instead of `services.length`. */
export interface EndpointConsumers {
  endpoint: EndpointConsumerSummary
  services: ServiceSummary[]
  count: number
  /** Present only when the request had `groupBy` and no `groupId`. */
  groups?: ConsumerGroup[]
  /** Size of the `services` remainder, for paging it; present only together with `groups`. `count` includes the grouped Services. */
  servicesCount?: number
}

// --- Operation -
// `Operation` read shapes — mirrors `atlas_plugin_apis/api/schemas.py`'s
// Operation/ServiceOperationUsage models. Like `Endpoint`, `Operation` is
// plugin-owned child data, not a `CatalogEntity`.

export type OperationDirection = 'send' | 'receive'
export type OperationStatus = 'active' | 'removed'
export type OperationRole = 'publisher' | 'subscriber'

/** `{description?, url}` — mirrors `ExternalDocsOut`. */
export interface ExternalDocs {
  description: string
  url: string
}

/** One message shape carried by an Operation's channel — reuses `EndpointSchema` for its payload schema. */
export interface OperationMessage {
  name: string
  title: string
  summary: string
  contentType: string
  schema: EndpointSchema | null
  example: unknown
  headers: EndpointSchema | null
}

/** The Operation's API document-owner Service, with its role implied purely from `direction` — never a stored `ServiceOperationUsage` row. `null` when the API has no `apiProvidedBy` relation. */
export interface OperationProvider {
  service: ServiceSummary
  role: OperationRole
}

export interface Operation {
  id: string
  apiId: string
  channelAddress: string
  channelProtocol: string
  direction: OperationDirection
  operationKey: string
  operationId: string
  summary: string
  description: string
  tags: string[]
  messages: OperationMessage[]
  externalDocs: ExternalDocs | null
  delivery: OperationDelivery
  status: OperationStatus
  deprecated: boolean
  provider: OperationProvider | null
  createdAt: string
  updatedAt: string
}

/** How an AMQP event is delivered; documentation only, never identity. */
export interface OperationDelivery {
  exchange?: string | null
  queue?: string | null
  vhost?: string | null
}

export interface OperationListFilters {
  direction?: OperationDirection
  tag?: string
  search?: string
  status?: OperationStatus
}

// --- Service <-> Operation dependency -------------

export interface OperationService {
  id: string
  service: ServiceSummary
  role: OperationRole
  linkedAt: string
}

export type OperationServiceLink = OperationService

export interface OperationConsumerSummary {
  id: string
  channelAddress: string
  channelProtocol: string
  direction: OperationDirection
  status: OperationStatus
}

/** One publisher/subscriber node in the channel-scoped compact graph — either a document-owner's implied role or an explicit `ServiceOperationUsage` link. */
export interface OperationConsumerParticipant {
  service: ServiceSummary
  role: OperationRole
}

/** `GET /api/operations/{operationId}/consumers` — aggregated by `channel_address`, not scoped to the single Operation row. One page (default 50), publishers first; the counts are totals matching `search`, independent of the page. */
export interface OperationConsumers {
  operation: OperationConsumerSummary
  participants: OperationConsumerParticipant[]
  count: number
  publisherCount: number
  subscriberCount: number
  /** Present only when the request had `groupBy` and no `groupId`; a team can be in both lists with different counts. */
  publisherGroups?: ConsumerGroup[]
  subscriberGroups?: ConsumerGroup[]
  /** Size of the `participants` remainder, for paging it; present only together with the group lists. `count` includes the grouped participants. */
  participantsCount?: number
}
