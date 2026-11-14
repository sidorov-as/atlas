// Draft-side rules of the view builder: what a draft may contain, how level and
// mode changes reshape it, and the labels derived from it.
import {
  entityTypesForLevel,
  type CustomViewDepth,
  type CustomViewDirection,
  type CustomViewEntityType,
  type CustomViewLevel,
  type CustomViewRelationships,
  type CustomViewSelection,
  type CustomViewSettings,
} from './customView'
import type { PickerEntity } from './customViewApi'

/** The form's working copy. Entities are resolved (named) and depth may be empty while being typed. */
export interface CustomViewDraft {
  level: CustomViewLevel
  selection: CustomViewSelection
  entities: PickerEntity[]
  depth: CustomViewDepth | null
  direction: CustomViewDirection
  entityTypes: CustomViewEntityType[]
  relationships: CustomViewRelationships
}

export const COMPONENT_LEVEL_KINDS = ['component', 'resource', 'api']

export function draftFromSettings(settings: CustomViewSettings, entities: PickerEntity[]): CustomViewDraft {
  return { ...settings, entities }
}

export function draftToSettings(draft: CustomViewDraft): CustomViewSettings {
  return { ...draft, entities: draft.entities.map((entity) => entity.id), depth: draft.depth ?? 1 }
}

/** The entity type an entity counts as for the type checkboxes; Systems have none (always shown). */
export function typeOfEntity(entity: PickerEntity, actorKindIds: string[]): CustomViewEntityType | null {
  if (actorKindIds.includes(entity.kind)) return 'actor'
  return COMPONENT_LEVEL_KINDS.includes(entity.kind) ? (entity.kind as CustomViewEntityType) : null
}

export function isSelectableAtLevel(entity: PickerEntity, level: CustomViewLevel, actorKindIds: string[]): boolean {
  if (actorKindIds.includes(entity.kind)) return true
  return level === 'systems' ? entity.kind === 'system' : COMPONENT_LEVEL_KINDS.includes(entity.kind)
}

/** Switches the level, dropping entities that do not exist at the new level. */
export function changeLevel(draft: CustomViewDraft, level: CustomViewLevel, actorKindIds: string[]): { draft: CustomViewDraft; cleared: boolean } {
  if (level === draft.level) return { draft, cleared: false }
  const entities = draft.entities.filter((entity) => isSelectableAtLevel(entity, level, actorKindIds))
  const actorsOn = draft.entityTypes.includes('actor')
  const entityTypes = entityTypesForLevel(level).filter((type) => type !== 'actor' || actorsOn)
  return { draft: { ...draft, level, entities, entityTypes }, cleared: entities.length < draft.entities.length }
}

/** Switches the mode, keeping the entities; Selected-only needs every chosen type enabled, so those are re-enabled. */
export function changeSelection(draft: CustomViewDraft, selection: CustomViewSelection, actorKindIds: string[]): CustomViewDraft {
  if (selection === draft.selection) return draft
  const entityTypes = new Set(draft.entityTypes)
  if (selection === 'selected') {
    for (const entity of draft.entities) {
      const type = typeOfEntity(entity, actorKindIds)
      if (type) entityTypes.add(type)
    }
  }
  return { ...draft, selection, entityTypes: entityTypesForLevel(draft.level).filter((type) => entityTypes.has(type)) }
}

/** In Selected-only mode a type that still has chosen entities cannot be switched off. */
export function isTypeLocked(draft: CustomViewDraft, type: CustomViewEntityType, actorKindIds: string[]): boolean {
  return draft.selection === 'selected' && draft.entityTypes.includes(type)
    && draft.entities.some((entity) => typeOfEntity(entity, actorKindIds) === type)
}

export function isDraftValid(draft: CustomViewDraft): boolean {
  if (draft.entities.length === 0) return false
  if (draft.selection === 'neighborhood') return draft.depth === 'all' || (typeof draft.depth === 'number' && Number.isInteger(draft.depth) && draft.depth >= 1)
  return true
}

export function viewHeading(entities: PickerEntity[]): string {
  if (entities.length === 0) return 'Custom view'
  if (entities.length === 1) return `${entities[0].name} dependencies`
  return 'Selected architecture'
}
