import { describe, expect, it } from 'vitest'
import { logoForTheme, type AtlasConfig } from './atlas.config'

const base: AtlasConfig = { title: 'T', tagline: '', logo: '/light.svg', icon: '/favicon.ico' }

describe('logoForTheme', () => {
  it('uses the light logo in the light theme', () => {
    expect(logoForTheme({ ...base, logoDark: '/dark.svg' }, 'light')).toBe('/light.svg')
  })

  it('uses the dark logo in the dark theme when configured', () => {
    expect(logoForTheme({ ...base, logoDark: '/dark.svg' }, 'dark')).toBe('/dark.svg')
  })

  it('falls back to the light logo in the dark theme when no dark logo is configured', () => {
    expect(logoForTheme(base, 'dark')).toBe('/light.svg')
  })
})
