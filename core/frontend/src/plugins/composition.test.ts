// Boundary coverage for c4-plugin spec's "Distribution without atlas.c4 composes
// successfully" scenario — composes a synthetic distribution
// that omits `c4Plugin` and checks no C4 tab or home widget contribution appears, while
// Standard Catalog's own contributions are unaffected.
//
// Filters the real `installedFrontendPlugins` list rather than importing the plugin
// packages directly here: several plugin pages import `composedContributions` back from
// this same module (e.g. `ApiDetailPage.tsx`), so importing a plugin package before this
// module has established the real composition creates a circular-import ordering hazard.
import { describe, expect, it } from 'vitest'
import { composeFrontendPlugins } from '@atlas/plugin-api'
import { installedFrontendPlugins } from './composition'

describe('composing a distribution without atlas.c4', () => {
  const withoutC4 = installedFrontendPlugins.filter((plugin) => plugin.id !== 'atlas.c4')

  it('composes successfully with no C4 tab or home widget contribution', () => {
    const result = composeFrontendPlugins(withoutC4)

    expect(result.entityDetailTabs.some((tab) => tab.id.startsWith('atlas.c4.'))).toBe(false)
    expect(result.homeWidgets.some((widget) => widget.id.startsWith('atlas.c4.'))).toBe(false)
  })

  it('leaves Standard Catalog contributions unaffected', () => {
    const withC4 = composeFrontendPlugins(installedFrontendPlugins)
    const result = composeFrontendPlugins(withoutC4)

    const standardCatalogTabIds = (contributions: typeof withC4.entityDetailTabs) =>
      contributions.filter((tab) => tab.id.startsWith('atlas.standard-catalog.')).map((tab) => tab.id)

    expect(standardCatalogTabIds(result.entityDetailTabs)).toEqual(standardCatalogTabIds(withC4.entityDetailTabs))
  })
})
