import { describe, expect, it } from 'vitest'
import {
  customViewPreviewUrl,
  defaultCustomViewSettings,
  neighborhoodPreset,
  newViewFromRootPath,
  sameCustomViewSettings,
  settingsFromBody,
  settingsToBody,
  viewDiagramUrl,
  type CustomViewSettings,
} from './customView'

const ID = '11111111-1111-4111-8111-111111111111'
const rendering = { layout: 'LAYOUT_LEFT_RIGHT', showTitle: false, showLegend: true, showSelectedLabel: true, showPersonSprite: false, showStereotypes: true } as const

describe('settings body', () => {
  it('sends depth and direction only for Neighborhood mode', () => {
    const selected: CustomViewSettings = { ...defaultCustomViewSettings(), entities: [ID] }
    expect(settingsToBody(selected)).not.toHaveProperty('depth')
    expect(settingsToBody(selected)).not.toHaveProperty('direction')
    const neighborhood = neighborhoodPreset('components', ID)
    expect(settingsToBody(neighborhood)).toMatchObject({ selection: 'neighborhood', depth: 1, direction: 'both' })
  })

  it('keeps an empty entity type list as "none enabled"', () => {
    expect(settingsToBody({ ...defaultCustomViewSettings(), entities: [ID], entityTypes: [] }).entityTypes).toEqual([])
  })

  it('drops types the level does not offer and orders the rest', () => {
    const body = settingsToBody({ ...neighborhoodPreset('components', ID), entityTypes: ['actor', 'api', 'component'] })
    expect(body.entityTypes).toEqual(['component', 'api', 'actor'])
    expect(settingsToBody({ ...defaultCustomViewSettings(), entityTypes: ['resource', 'actor'] }).entityTypes).toEqual(['actor'])
  })

  it('round-trips through the stored shape and fills omitted fields with defaults', () => {
    const settings = { ...neighborhoodPreset('components', ID), depth: 'all' as const, direction: 'incoming' as const }
    expect(settingsFromBody(settingsToBody(settings))).toEqual(settings)
    expect(settingsFromBody({ level: 'systems', selection: 'selected', entities: [ID], depth: null, direction: null, entityTypes: null, relationships: 'declared' }))
      .toEqual({ ...defaultCustomViewSettings(), entities: [ID] })
  })

  it('compares settings by what the view stores', () => {
    const a = { ...defaultCustomViewSettings(), entities: [ID], depth: 3 as const }
    expect(sameCustomViewSettings(a, { ...a, depth: 9 })).toBe(true) // depth is ignored in Selected mode
    expect(sameCustomViewSettings(a, { ...a, relationships: 'declared_and_derived' })).toBe(false)
  })
})

describe('URLs', () => {
  it('keeps settings out of the preview URL', () => {
    expect(customViewPreviewUrl()).toBe('/api/plugins/atlas.c4/diagrams/custom/')
    const url = customViewPreviewUrl({ rendering })
    expect(url).toContain('layout=LAYOUT_LEFT_RIGHT')
    expect(url).toContain('show_title=false')
    expect(url).not.toMatch(/level|entity|selection/)
  })

  it('builds saved view diagram links with format, download, and rendering', () => {
    expect(viewDiagramUrl(ID)).toBe(`/api/plugins/atlas.c4/views/${ID}/diagram/`)
    expect(viewDiagramUrl(ID, { format: 'png', download: true })).toBe(`/api/plugins/atlas.c4/views/${ID}/diagram/?format=png&download=1`)
    expect(viewDiagramUrl(ID, { rendering })).toContain('show_person_sprite=false')
    expect(viewDiagramUrl(ID, { format: 'png', download: true, theme: 'dark' })).toBe(
      `/api/plugins/atlas.c4/views/${ID}/diagram/?format=png&download=1&theme=dark`,
    )
    expect(customViewPreviewUrl({ theme: 'dark' })).toBe('/api/plugins/atlas.c4/diagrams/custom/?theme=dark')
  })

  it('links "Open in view builder" by root id only', () => {
    expect(newViewFromRootPath(ID)).toBe(`/system-map/views/new?root=${ID}`)
  })
})
