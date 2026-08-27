// Typed wrappers around the entity CRUD API.
import { apiJson } from './api'
import type {
  ApiEntity,
  ArchitectureRelationship,
  CatalogHomeSettings,
  ComponentEntity,
  FlowEntity,
  FlowStep,
  GroupEntity,
  HistoryRecord,
  Relation,
  ResourceEntity,
  Paginated,
  SystemEntity,
  Tag,
  UserEntity,
  LinkOut,
} from './types'

/** Lowercase model kind -> its list-page path prefix. No `user` entry — there's no detail route. */
export const kindToPath: Record<string, string> = {
  system: '/systems',
  component: '/components',
  resource: '/resources',
  api: '/apis',
  group: '/teams',
}

export interface ListFilters {
  owner?: string
  system?: string
  lifecycle?: string
  type?: string
  q?: string
  tags?: string[]
  /** `entity-catalog` spec's "List filtering and search": omitted/`active` excludes `removed` entities; `all` is the "show removed" opt-in. */
  status?: 'active' | 'all'
  page?: number
  pageSize?: number
  sort?: 'name' | '-name'
}

function toQuery(filters: ListFilters = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item))
    else if (value) params.set(key === 'pageSize' ? 'page_size' : key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export interface MetadataInput {
  name: string
  title?: string
  description?: string
  documentation?: string
  tags?: string[]
  links?: LinkOut[]
}

export interface SystemInput {
  metadata: MetadataInput
  spec: { owner: string }
}

export interface SystemUpdate {
  metadata?: Partial<MetadataInput>
  spec?: Partial<SystemInput['spec']>
}

export interface ComponentInput {
  metadata: MetadataInput
  spec: {
    type: string
    lifecycle: string
    owner: string
    system: string
    providesApis?: string[]
    consumesApis?: string[]
    dependsOn?: string[]
  }
}

export interface ResourceInput {
  metadata: MetadataInput
  spec: { type: string; owner: string; system?: string | null }
}

export interface ApiInput {
  metadata: MetadataInput
  spec: { type: string; owner: string; system: string; specSource?: string; specUrl?: string; specContent?: string }
}

function envelope(kind: string, input: { metadata: MetadataInput; spec: unknown }) {
  return { apiVersion: 'atlas/v1alpha1', kind, ...input }
}

export const systemsApi = {
  list: (filters?: ListFilters) => apiJson<Paginated<SystemEntity>>(`/api/systems/${toQuery(filters)}`),
  get: (id: string) => apiJson<SystemEntity>(`/api/systems/${id}/`),
  create: (input: SystemInput) =>
    apiJson<SystemEntity>('/api/systems/', {
      method: 'POST',
      body: JSON.stringify(envelope('System', input)),
    }),
  update: (id: string, input: SystemUpdate) =>
    apiJson<SystemEntity>(`/api/systems/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  relations: (id: string) => apiJson<Relation[]>(`/api/systems/${id}/relations/`),
  history: (id: string) => apiJson<HistoryRecord[]>(`/api/systems/${id}/history/`),
  docs: (id: string, filters?: Pick<ListFilters, 'q' | 'page' | 'pageSize'>) =>
    apiJson<Paginated<LinkOut>>(`/api/systems/${id}/docs/${toQuery(filters)}`),
  remove: (id: string) => apiJson<SystemEntity>(`/api/systems/${id}/remove/`, { method: 'POST' }),
  revive: (id: string) => apiJson<SystemEntity>(`/api/systems/${id}/revive/`, { method: 'POST' }),
  purge: (id: string) => apiJson<void>(`/api/systems/${id}/purge/`, { method: 'POST' }),
}

export const componentsApi = {
  list: (filters?: ListFilters) => apiJson<Paginated<ComponentEntity>>(`/api/components/${toQuery(filters)}`),
  get: (id: string) => apiJson<ComponentEntity>(`/api/components/${id}/`),
  create: (input: ComponentInput) =>
    apiJson<ComponentEntity>('/api/components/', {
      method: 'POST',
      body: JSON.stringify(envelope('Component', input)),
    }),
  update: (id: string, input: Partial<ComponentInput>) =>
    apiJson<ComponentEntity>(`/api/components/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  relations: (id: string) => apiJson<Relation[]>(`/api/components/${id}/relations/`),
  history: (id: string) => apiJson<HistoryRecord[]>(`/api/components/${id}/history/`),
  remove: (id: string) => apiJson<ComponentEntity>(`/api/components/${id}/remove/`, { method: 'POST' }),
  revive: (id: string) => apiJson<ComponentEntity>(`/api/components/${id}/revive/`, { method: 'POST' }),
  purge: (id: string) => apiJson<void>(`/api/components/${id}/purge/`, { method: 'POST' }),
}

export const resourcesApi = {
  list: (filters?: ListFilters) => apiJson<Paginated<ResourceEntity>>(`/api/resources/${toQuery(filters)}`),
  get: (id: string) => apiJson<ResourceEntity>(`/api/resources/${id}/`),
  create: (input: ResourceInput) =>
    apiJson<ResourceEntity>('/api/resources/', {
      method: 'POST',
      body: JSON.stringify(envelope('Resource', input)),
    }),
  update: (id: string, input: Partial<ResourceInput>) =>
    apiJson<ResourceEntity>(`/api/resources/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  relations: (id: string) => apiJson<Relation[]>(`/api/resources/${id}/relations/`),
  history: (id: string) => apiJson<HistoryRecord[]>(`/api/resources/${id}/history/`),
  remove: (id: string) => apiJson<ResourceEntity>(`/api/resources/${id}/remove/`, { method: 'POST' }),
  revive: (id: string) => apiJson<ResourceEntity>(`/api/resources/${id}/revive/`, { method: 'POST' }),
  purge: (id: string) => apiJson<void>(`/api/resources/${id}/purge/`, { method: 'POST' }),
}

export const apisApi = {
  list: (filters?: ListFilters) => apiJson<Paginated<ApiEntity>>(`/api/apis/${toQuery(filters)}`),
  get: (id: string) => apiJson<ApiEntity>(`/api/apis/${id}/`),
  create: (input: ApiInput) =>
    apiJson<ApiEntity>('/api/apis/', { method: 'POST', body: JSON.stringify(envelope('API', input)) }),
  update: (id: string, input: Partial<ApiInput>) =>
    apiJson<ApiEntity>(`/api/apis/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  relations: (id: string) => apiJson<Relation[]>(`/api/apis/${id}/relations/`),
  history: (id: string) => apiJson<HistoryRecord[]>(`/api/apis/${id}/history/`),
  remove: (id: string) => apiJson<ApiEntity>(`/api/apis/${id}/remove/`, { method: 'POST' }),
  revive: (id: string) => apiJson<ApiEntity>(`/api/apis/${id}/revive/`, { method: 'POST' }),
  purge: (id: string) => apiJson<void>(`/api/apis/${id}/purge/`, { method: 'POST' }),
}

export const architectureRelationshipsApi = {
  list: (source: string) =>
    apiJson<ArchitectureRelationship[]>(`/api/architecture-relationships/?${new URLSearchParams({ source })}`),
  create: (input: ArchitectureRelationshipInput) =>
    apiJson<ArchitectureRelationship>('/api/architecture-relationships/', { method: 'POST', body: JSON.stringify(input) }),
  update: (id: number, input: Partial<ArchitectureRelationshipInput>) =>
    apiJson<ArchitectureRelationship>(`/api/architecture-relationships/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  remove: (id: number) => apiJson<void>(`/api/architecture-relationships/${id}/`, { method: 'DELETE' }),
}

export interface ArchitectureRelationshipInput {
  source: string
  target: string
  label: string
  technology: string
  interactionKind: 'synchronous' | 'asynchronous' | 'data-access' | 'manual'
  tags: string[]
}

export interface FlowListFilters {
  system?: string
  team?: string
  q?: string
  page?: number
  pageSize?: number
  sort?: 'name' | '-name'
}

function toFlowQuery(filters: FlowListFilters = {}): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key === 'pageSize' ? 'page_size' : key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export interface FlowInput {
  system: string
  name: string
  description?: string
  steps?: FlowStep[]
  autolayoutEnabled?: boolean
  layoutDirection?: 'LAYOUT_LEFT_RIGHT' | 'LAYOUT_TOP_DOWN'
  layoutEngine?: 'dagre' | 'elk'
}

export const flowsApi = {
  list: (filters?: FlowListFilters) => apiJson<Paginated<FlowEntity>>(`/api/flows/${toFlowQuery(filters)}`),
  get: (id: number) => apiJson<FlowEntity>(`/api/flows/${id}/`),
  create: (input: FlowInput) =>
    apiJson<FlowEntity>('/api/flows/', { method: 'POST', body: JSON.stringify(input) }),
  update: (id: number, input: Partial<FlowInput>) =>
    apiJson<FlowEntity>(`/api/flows/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  remove: (id: number) => apiJson<void>(`/api/flows/${id}/`, { method: 'DELETE' }),
}

export const groupsApi = {
  list: (filters?: ListFilters) => apiJson<Paginated<GroupEntity>>(`/api/groups/${toQuery(filters)}`),
  get: (id: string) => apiJson<GroupEntity>(`/api/groups/${id}/`),
}

export const usersApi = {
  list: (filters?: ListFilters) => apiJson<UserEntity[]>(`/api/users/${toQuery(filters)}`),
  get: (id: string) => apiJson<UserEntity>(`/api/users/${id}/`),
}

export const tagsApi = {
  list: () => apiJson<Tag[]>('/api/tags/'),
  updateColor: (id: number, color: string) =>
    apiJson<Tag>(`/api/tags/${id}/`, { method: 'PATCH', body: JSON.stringify({ color }) }),
}

export const catalogHomeSettingsApi = {
  get: () => apiJson<CatalogHomeSettings>('/api/catalog-home-settings/'),
  update: (aboutMarkdown: string) =>
    apiJson<CatalogHomeSettings>('/api/catalog-home-settings/', { method: 'PATCH', body: JSON.stringify({ aboutMarkdown }) }),
}
