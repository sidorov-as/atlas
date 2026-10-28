import { describe, expect, it } from 'vitest'
import { defaultCustomViewSettings } from './customView'
import type { PickerEntity } from './customViewApi'
import {
  changeLevel,
  changeSelection,
  draftFromSettings,
  draftToSettings,
  isDraftValid,
  isTypeLocked,
  viewHeading,
} from './customViewDraft'

const entity = (id: string, kind: string, name = id): PickerEntity => ({ id, kind, name, system: null, type: null })
const ACTORS = ['group', 'user']

describe('changeLevel', () => {
  it('drops entities that do not exist at the new level and reports it', () => {
    const draft = { ...draftFromSettings({ ...defaultCustomViewSettings(), level: 'components', entityTypes: ['component', 'resource', 'api', 'actor'] }, [entity('c', 'component'), entity('u', 'user')]) }
    const { draft: next, cleared } = changeLevel(draft, 'systems', ACTORS)
    expect(next.entities.map((e) => e.id)).toEqual(['u'])
    expect(next.entityTypes).toEqual(['actor'])
    expect(cleared).toBe(true)
  })

  it('does not report clearing when nothing was dropped and keeps the actor toggle', () => {
    const draft = draftFromSettings({ ...defaultCustomViewSettings(), entityTypes: [] }, [entity('s', 'system')])
    const { draft: next, cleared } = changeLevel(draft, 'components', ACTORS)
    expect(cleared).toBe(true)
    expect(next.entityTypes).toEqual(['component', 'resource', 'api'])
    expect(changeLevel(draftFromSettings(defaultCustomViewSettings(), []), 'components', ACTORS).cleared).toBe(false)
  })
})

describe('mode and type rules', () => {
  const base = draftFromSettings(
    { ...defaultCustomViewSettings(), level: 'components', selection: 'neighborhood', entityTypes: ['component'] },
    [entity('a', 'api'), entity('c', 'component')],
  )

  it('keeps the entities across mode switches and re-enables the types of chosen entities in Selected mode', () => {
    const selected = changeSelection(base, 'selected', ACTORS)
    expect(selected.entities).toHaveLength(2)
    expect(selected.entityTypes).toEqual(['component', 'api'])
    expect(changeSelection(selected, 'neighborhood', ACTORS).entities).toHaveLength(2)
  })

  it('blocks disabling a type that has chosen entities only in Selected mode', () => {
    const selected = changeSelection(base, 'selected', ACTORS)
    expect(isTypeLocked(selected, 'api', ACTORS)).toBe(true)
    expect(isTypeLocked(selected, 'resource', ACTORS)).toBe(false)
    expect(isTypeLocked({ ...selected, selection: 'neighborhood' }, 'api', ACTORS)).toBe(false)
  })
})

describe('validity and heading', () => {
  it('requires an entity and, in Neighborhood mode, a positive depth or Unlimited', () => {
    const empty = draftFromSettings(defaultCustomViewSettings(), [])
    expect(isDraftValid(empty)).toBe(false)
    const one = { ...empty, entities: [entity('s', 'system')] }
    expect(isDraftValid(one)).toBe(true)
    expect(isDraftValid({ ...one, selection: 'neighborhood', depth: null })).toBe(false)
    expect(isDraftValid({ ...one, selection: 'neighborhood', depth: 0 })).toBe(false)
    expect(isDraftValid({ ...one, selection: 'neighborhood', depth: 'all' })).toBe(true)
  })

  it('serializes the draft to settings with entity ids', () => {
    const draft = draftFromSettings(defaultCustomViewSettings(), [entity('s', 'system')])
    expect(draftToSettings(draft).entities).toEqual(['s'])
  })

  it('computes the heading', () => {
    expect(viewHeading([])).toBe('Custom view')
    expect(viewHeading([entity('a', 'api', 'Booking API')])).toBe('Booking API dependencies')
    expect(viewHeading([entity('a', 'api'), entity('b', 'api')])).toBe('Selected architecture')
  })
})
