// Custom view settings model: what a view stores, its JSON wire format, and the
// routes and diagram endpoint URLs around it. Settings are never serialized
// into page URLs; layout and display options come from viewer preferences.
import { addRenderingOptions, type DiagramFormat, type DiagramRenderingOptions, type DiagramTheme } from './diagramUrls'

export type CustomViewLevel = 'systems' | 'components'
export type CustomViewSelection = 'selected' | 'neighborhood'
export type CustomViewDirection = 'both' | 'outgoing' | 'incoming'
export type CustomViewRelationships = 'declared' | 'declared_and_derived'
export type CustomViewEntityType = 'component' | 'resource' | 'api' | 'actor'
export type CustomViewDepth = number | 'all'

export interface CustomViewSettings {
  level: CustomViewLevel
  selection: CustomViewSelection
  /** Entity ids: the full node set in `selected` mode, the roots in `neighborhood` mode. */
  entities: string[]
  depth: CustomViewDepth
  direction: CustomViewDirection
  entityTypes: CustomViewEntityType[]
  relationships: CustomViewRelationships
}

/** The JSON shape of view settings in request bodies and saved views. */
export interface CustomViewSettingsBody {
  level: CustomViewLevel
  selection: CustomViewSelection
  entities: string[]
  depth?: CustomViewDepth | null
  direction?: CustomViewDirection | null
  entityTypes?: CustomViewEntityType[] | null
  relationships: CustomViewRelationships
}

export const SYSTEM_MAP_PATH = '/system-map'
export const VIEWS_TAB = 'views'
export const NEW_VIEW_PATH = `${SYSTEM_MAP_PATH}/views/new`
export const VIEWS_LIST_PATH = `${SYSTEM_MAP_PATH}?tab=${VIEWS_TAB}`

export const viewPath = (id: string) => `${SYSTEM_MAP_PATH}/views/${id}`
export const viewEditPath = (id: string) => `${viewPath(id)}/edit`
/** "Open in view builder": the editor resolves the root, derives the level, and applies defaults. */
export const newViewFromRootPath = (rootId: string) => `${NEW_VIEW_PATH}?root=${encodeURIComponent(rootId)}`

const ENTITY_TYPE_ORDER: CustomViewEntityType[] = ['component', 'resource', 'api', 'actor']

/** The optional entity types a level offers; Systems themselves are always shown. */
export function entityTypesForLevel(level: CustomViewLevel): CustomViewEntityType[] {
  return level === 'systems' ? ['actor'] : [...ENTITY_TYPE_ORDER]
}

export function defaultCustomViewSettings(): CustomViewSettings {
  return {
    level: 'systems',
    selection: 'selected',
    entities: [],
    depth: 1,
    direction: 'both',
    entityTypes: entityTypesForLevel('systems'),
    relationships: 'declared',
  }
}

/** The "Open in view builder" defaults: the entity as a depth-1 Neighborhood root, both directions, declared only, all types. */
export function neighborhoodPreset(level: CustomViewLevel, entityId: string): CustomViewSettings {
  return {
    ...defaultCustomViewSettings(),
    level,
    selection: 'neighborhood',
    entities: [entityId],
    entityTypes: entityTypesForLevel(level),
  }
}

/** Request/stored JSON for settings. Depth and direction only apply to Neighborhood mode. */
export function settingsToBody(settings: CustomViewSettings): CustomViewSettingsBody {
  const allowed = new Set(entityTypesForLevel(settings.level))
  const types = new Set(settings.entityTypes)
  const body: CustomViewSettingsBody = {
    level: settings.level,
    selection: settings.selection,
    entities: settings.entities,
    entityTypes: ENTITY_TYPE_ORDER.filter((type) => allowed.has(type) && types.has(type)),
    relationships: settings.relationships,
  }
  if (settings.selection === 'neighborhood') {
    body.depth = settings.depth
    body.direction = settings.direction
  }
  return body
}

/** Settings from a saved view's JSON; omitted optional fields take the builder's defaults. */
export function settingsFromBody(body: CustomViewSettingsBody): CustomViewSettings {
  return {
    level: body.level,
    selection: body.selection,
    entities: body.entities,
    depth: body.depth ?? 1,
    direction: body.direction ?? 'both',
    entityTypes: body.entityTypes ?? entityTypesForLevel(body.level),
    relationships: body.relationships,
  }
}

export function sameCustomViewSettings(a: CustomViewSettings, b: CustomViewSettings): boolean {
  return JSON.stringify(settingsToBody(a)) === JSON.stringify(settingsToBody(b))
}

export type CustomViewUrlOptions = {
  format?: DiagramFormat
  download?: boolean
  rendering?: DiagramRenderingOptions
  theme?: DiagramTheme
}

function diagramQuery(options: CustomViewUrlOptions): string {
  const query = new URLSearchParams()
  if (options.format && options.format !== 'svg') query.set('format', options.format)
  if (options.download) query.set('download', '1')
  addRenderingOptions(query, options.rendering, options.theme)
  const suffix = query.toString()
  return suffix ? `?${suffix}` : ''
}

/** Draft preview endpoint; the settings travel as a POST body, only rendering options in the URL. */
export function customViewPreviewUrl(options: CustomViewUrlOptions = {}): string {
  return `/api/plugins/atlas.c4/diagrams/custom/${diagramQuery(options)}`
}

/** Plain link to a saved view's diagram (SVG, PNG, or download). */
export function viewDiagramUrl(viewId: string, options: CustomViewUrlOptions = {}): string {
  return `/api/plugins/atlas.c4/views/${viewId}/diagram/${diagramQuery(options)}`
}
