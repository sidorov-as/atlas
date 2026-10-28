// Data layer for the view builder: actor kinds, entity search for the picker,
// and id resolution for entities named in a link.
import { apiJson, ApiError } from 'frontend/lib/api'
import {
  apisApi,
  componentsApi,
  groupsApi,
  resourcesApi,
  systemsApi,
  usersApi,
} from 'frontend/lib/entities'
import { refName, type Paginated } from 'frontend/lib/types'
import {
  settingsFromBody,
  settingsToBody,
  type CustomViewEntityType,
  type CustomViewLevel,
  type CustomViewSettings,
  type CustomViewSettingsBody,
} from './customView'

export interface ActorKind {
  kind: string
  label: string
}

export function fetchActorKinds(): Promise<ActorKind[]> {
  return apiJson<{ items: ActorKind[] }>('/api/plugins/atlas.c4/custom-view/actor-kinds/').then((body) => body.items)
}

/** A structured error from the custom view endpoint (`{ detail: [{ msg, type, ... }] }`). */
export class CustomViewFetchError extends Error {
  status: number
  code: string
  entity?: string
  limit?: number
  count?: number

  constructor(status: number, code: string, message: string, extra: { entity?: string; limit?: number; count?: number } = {}) {
    super(message)
    this.status = status
    this.code = code
    Object.assign(this, extra)
  }

  static async fromResponse(response: Response): Promise<CustomViewFetchError> {
    try {
      const body = (await response.json()) as { detail?: Array<{ msg?: string; type?: string; entity?: string; limit?: number; count?: number }> }
      const detail = body.detail?.[0]
      if (detail) {
        return new CustomViewFetchError(response.status, detail.type ?? 'error', detail.msg ?? 'The view could not be built', {
          entity: detail.entity,
          limit: detail.limit,
          count: detail.count,
        })
      }
    } catch {
      // Non-JSON error body (for example a proxy page); fall through to the generic error.
    }
    return new CustomViewFetchError(response.status, response.status >= 500 ? 'render_failed' : 'error', 'The view could not be built')
  }
}

/** What the picker and the selected-entity rows need to show about one entity. */
export interface PickerEntity {
  id: string
  /** Lowercase kind id: `system`, `component`, `resource`, `api`, `group`, `user`. */
  kind: string
  name: string
  /** The owning System's name, when the entity has one. */
  system: string | null
  /** Type within the kind (service, database, openapi, ...), for icons. */
  type: string | null
}

const PAGE_SIZE = 8

type AnyEntity = {
  id: string
  kind: string
  metadata: { name: string; title?: string }
  spec?: Record<string, unknown>
}

function toPickerEntity(entity: AnyEntity): PickerEntity {
  const spec = entity.spec ?? {}
  const profile = spec.profile as { displayName?: string } | undefined
  return {
    id: entity.id,
    kind: entity.kind.toLowerCase(),
    name: entity.metadata.title || profile?.displayName || entity.metadata.name,
    system: typeof spec.system === 'string' && spec.system ? refName(spec.system) : null,
    type: typeof spec.type === 'string' ? spec.type : null,
  }
}

type Source = {
  list: (q: string) => Promise<AnyEntity[]>
  get: (id: string) => Promise<AnyEntity>
}

function pageSource(api: {
  list: (filters: { q?: string; pageSize?: number }) => Promise<{ page: { objectList: unknown[] } }>
  get: (id: string) => Promise<unknown>
}): Source {
  return {
    list: async (q) => (await api.list({ q, pageSize: PAGE_SIZE })).page.objectList as AnyEntity[],
    get: async (id) => (await api.get(id)) as AnyEntity,
  }
}

const SOURCES: Record<string, Source> = {
  system: pageSource(systemsApi),
  component: pageSource(componentsApi),
  resource: pageSource(resourcesApi),
  api: pageSource(apisApi),
  group: pageSource(groupsApi),
  user: {
    list: async (q) => ((await usersApi.list({ q })) as unknown as AnyEntity[]).slice(0, PAGE_SIZE),
    get: async (id) => (await usersApi.get(id)) as unknown as AnyEntity,
  },
}

const TYPE_KINDS: Record<Exclude<CustomViewEntityType, 'actor'>, string> = {
  component: 'component',
  resource: 'resource',
  api: 'api',
}

/** Kinds the picker can search: the level's own kinds plus the actor kinds with a known list endpoint. */
export function pickerKinds(level: CustomViewLevel, enabledTypes: CustomViewEntityType[], actorKinds: ActorKind[]): string[] {
  const own = level === 'systems' ? ['system'] : enabledTypes.filter((type): type is Exclude<CustomViewEntityType, 'actor'> => type !== 'actor').map((type) => TYPE_KINDS[type])
  const actors = enabledTypes.includes('actor') ? actorKinds.map((entry) => entry.kind).filter((kind) => kind in SOURCES) : []
  return [...own, ...actors]
}

/** Name search over the per-kind list endpoints, merged and de-duplicated; independent of the search plugin. */
export async function searchPickerEntities(query: string, kinds: string[], excludeIds: string[]): Promise<PickerEntity[]> {
  const lists = await Promise.all(kinds.map((kind) => SOURCES[kind]?.list(query) ?? Promise.resolve([])))
  const seen = new Set(excludeIds)
  const merged: PickerEntity[] = []
  for (const entity of lists.flat().map(toPickerEntity)) {
    if (seen.has(entity.id)) continue
    seen.add(entity.id)
    merged.push(entity)
  }
  return merged.sort((a, b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id))
}

/**
 * Resolves entity ids (from a link or a preset) to display data by trying the level's kinds in turn.
 * Ids that no kind returns come back in `missing`, so they can be reported instead of dropped.
 */
export async function resolvePickerEntities(
  ids: string[],
  level: CustomViewLevel,
  actorKinds: ActorKind[],
): Promise<{ found: PickerEntity[]; missing: string[] }> {
  const kinds = [...(level === 'systems' ? ['system'] : ['component', 'resource', 'api']), ...actorKinds.map((entry) => entry.kind).filter((kind) => kind in SOURCES)]
  const results = await Promise.all(
    ids.map(async (id) => {
      const attempts = await Promise.all(
        kinds.map((kind) =>
          SOURCES[kind].get(id).then(
            (entity) => toPickerEntity(entity),
            (error: unknown) => {
              if (error instanceof ApiError && error.status === 404) return null
              throw error
            },
          ),
        ),
      )
      return attempts.find((entity) => entity !== null) ?? null
    }),
  )
  return {
    found: results.filter((entity): entity is PickerEntity => entity !== null),
    missing: ids.filter((_, index) => results[index] === null),
  }
}



/** A saved view as the editor and detail page use it. */
export interface SavedView {
  id: string
  name: string
  description: string
  settings: CustomViewSettings
  /** Entity ids in the settings that no longer resolve. */
  missingEntities: string[]
  createdAt: string
  updatedAt: string
}

export interface ViewInput {
  name: string
  description: string
  settings: CustomViewSettings
}

interface SavedViewBody extends Omit<SavedView, 'settings'> {
  settings: CustomViewSettingsBody
}

export interface ViewListFilters {
  q?: string
  page?: number
  pageSize?: number
  sort?: 'name' | '-name'
}

const VIEWS_URL = '/api/plugins/atlas.c4/views/'

const fromBody = (body: SavedViewBody): SavedView => ({ ...body, settings: settingsFromBody(body.settings) })
const toBody = (input: ViewInput) => JSON.stringify({ name: input.name, description: input.description, settings: settingsToBody(input.settings) })

export const viewsApi = {
  async list(filters: ViewListFilters = {}): Promise<Paginated<SavedView>> {
    const query = new URLSearchParams()
    if (filters.q) query.set('q', filters.q)
    if (filters.page) query.set('page', String(filters.page))
    if (filters.pageSize) query.set('page_size', String(filters.pageSize))
    if (filters.sort) query.set('sort', filters.sort)
    const suffix = query.toString()
    const body = await apiJson<Paginated<SavedViewBody>>(`${VIEWS_URL}${suffix ? `?${suffix}` : ''}`)
    return { ...body, page: { ...body.page, objectList: body.page.objectList.map(fromBody) } }
  },
  async get(id: string): Promise<SavedView> {
    return fromBody(await apiJson<SavedViewBody>(`${VIEWS_URL}${id}/`))
  },
  async create(input: ViewInput): Promise<SavedView> {
    return fromBody(await apiJson<SavedViewBody>(VIEWS_URL, { method: 'POST', body: toBody(input) }))
  },
  async update(id: string, input: ViewInput): Promise<SavedView> {
    return fromBody(await apiJson<SavedViewBody>(`${VIEWS_URL}${id}/`, { method: 'PUT', body: toBody(input) }))
  },
  remove: (id: string) => apiJson<void>(`${VIEWS_URL}${id}/`, { method: 'DELETE' }),
}

/** The message of a field-level error (such as a duplicate name) in a dmr error body, if any. */
export function fieldError(error: unknown, field: string): string | null {
  if (!(error instanceof ApiError)) return null
  const detail = (error.body as { detail?: Array<{ msg?: string; loc?: Array<string | number> }> } | null)?.detail
  return detail?.find((item) => item.loc?.[item.loc.length - 1] === field)?.msg ?? null
}
