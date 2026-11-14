import { describe, expect, it } from 'vitest'
import { diagramUrl, systemLandscapeUrl } from './diagramUrls'

describe('diagram URLs carry the resolved theme', () => {
  it('adds the theme to entity diagram URLs, downloads included', () => {
    expect(diagramUrl('system', 'abc', 'context', { theme: 'dark' })).toBe(
      '/api/plugins/atlas.c4/diagrams/system/abc/?view=context&theme=dark',
    )
    expect(diagramUrl('system', 'abc', 'context', { format: 'png', download: true, theme: 'dark' })).toBe(
      '/api/plugins/atlas.c4/diagrams/system/abc/?view=context&format=png&download=1&theme=dark',
    )
  })

  it('adds the theme to landscape URLs, downloads included', () => {
    expect(systemLandscapeUrl({ theme: 'dark' })).toBe('/api/plugins/atlas.c4/diagrams/landscape/?theme=dark')
    expect(systemLandscapeUrl({ download: true, theme: 'light' })).toBe(
      '/api/plugins/atlas.c4/diagrams/landscape/?download=1&theme=light',
    )
  })

  it('omits the theme when none is given', () => {
    expect(diagramUrl('system', 'abc', 'context')).not.toContain('theme')
  })
})
