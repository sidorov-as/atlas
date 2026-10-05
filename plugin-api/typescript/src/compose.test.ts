import { describe, expect, it } from 'vitest'
import { entityDetailTab, globalSearch, homeWidget, navItem, route, routeRef } from './builders'
import { CORE_PLUGIN_ID, CompositionError, composeFrontendPlugins } from './compose'
import type { FrontendPlugin } from './types'

function Noop() {
  return null
}

describe('composeFrontendPlugins', () => {
  it('resolves routes, nav items, and entity-detail tabs from a valid set of plugins', () => {
    const plugin: FrontendPlugin = {
      id: 'atlas.fixture',
      contributions: [
        route({ id: 'atlas.fixture.list', path: '/fixtures', component: Noop }),
        navItem({ id: 'atlas.fixture.nav', title: 'Fixtures', route: routeRef('atlas.fixture.list') }),
        entityDetailTab({
          id: 'atlas.fixture.overview',
          value: 'overview',
          label: 'Overview',
          when: () => true,
          component: Noop,
        }),
        homeWidget({ id: 'atlas.fixture.widget', component: Noop }),
      ],
    }

    const result = composeFrontendPlugins([plugin])

    expect(result.routes).toHaveLength(1)
    expect(result.navItems).toEqual([{ ...plugin.contributions[1], resolvedPath: '/fixtures' }])
    expect(result.entityDetailTabs).toHaveLength(1)
    expect(result.homeWidgets).toHaveLength(1)
  })

  it('fails composition on a duplicate contribution id', () => {
    const pluginA: FrontendPlugin = {
      id: 'atlas.fixture-a',
      contributions: [route({ id: 'atlas.shared.id', path: '/a', component: Noop })],
    }
    const pluginB: FrontendPlugin = {
      id: 'atlas.fixture-b',
      contributions: [route({ id: 'atlas.shared.id', path: '/b', component: Noop })],
    }

    expect(() => composeFrontendPlugins([pluginA, pluginB])).toThrow(CompositionError)
    try {
      composeFrontendPlugins([pluginA, pluginB])
      expect.unreachable()
    } catch (error) {
      expect(error).toBeInstanceOf(CompositionError)
      expect((error as CompositionError).message).toContain('atlas.shared.id')
      expect((error as CompositionError).message).toContain('atlas.fixture-a')
      expect((error as CompositionError).message).toContain('atlas.fixture-b')
    }
  })

  it('fails composition on conflicting route paths', () => {
    const plugin: FrontendPlugin = {
      id: 'atlas.fixture',
      contributions: [
        route({ id: 'atlas.fixture.one', path: '/conflict', component: Noop }),
        route({ id: 'atlas.fixture.two', path: '/conflict', component: Noop }),
      ],
    }

    try {
      composeFrontendPlugins([plugin])
      expect.unreachable()
    } catch (error) {
      expect(error).toBeInstanceOf(CompositionError)
      expect((error as CompositionError).message).toContain('/conflict')
      expect((error as CompositionError).message).toContain('atlas.fixture.one')
      expect((error as CompositionError).message).toContain('atlas.fixture.two')
    }
  })

  it('fails composition on an unresolved routeRef', () => {
    const plugin: FrontendPlugin = {
      id: 'atlas.fixture',
      contributions: [navItem({ id: 'atlas.fixture.nav', title: 'Fixture', route: routeRef('atlas.does-not-exist') })],
    }

    try {
      composeFrontendPlugins([plugin])
      expect.unreachable()
    } catch (error) {
      expect(error).toBeInstanceOf(CompositionError)
      expect((error as CompositionError).message).toContain('atlas.does-not-exist')
      expect((error as CompositionError).message).toContain('atlas.fixture.nav')
    }
  })

  it('fails composition when a non-core plugin uses a core-reserved path', () => {
    const plugin: FrontendPlugin = {
      id: 'atlas.fixture',
      contributions: [route({ id: 'atlas.fixture.settings', path: '/settings', component: Noop })],
    }

    try {
      composeFrontendPlugins([plugin])
      expect.unreachable()
    } catch (error) {
      expect(error).toBeInstanceOf(CompositionError)
      expect((error as CompositionError).message).toContain('/settings')
      expect((error as CompositionError).message).toContain('atlas.fixture.settings')
    }
  })

  it('allows core itself to use a core-reserved path', () => {
    const corePlugin: FrontendPlugin = {
      id: CORE_PLUGIN_ID,
      contributions: [route({ id: 'atlas.core.settings', path: '/settings', component: Noop })],
    }

    expect(() => composeFrontendPlugins([corePlugin])).not.toThrow()
  })

  it('collects every conflict in a single error rather than stopping at the first', () => {
    const plugin: FrontendPlugin = {
      id: 'atlas.fixture',
      contributions: [
        route({ id: 'atlas.dup', path: '/dup-a', component: Noop }),
        route({ id: 'atlas.dup', path: '/dup-b', component: Noop }),
        navItem({ id: 'atlas.fixture.nav', title: 'Fixture', route: routeRef('atlas.missing') }),
      ],
    }

    try {
      composeFrontendPlugins([plugin])
      expect.unreachable()
    } catch (error) {
      const message = (error as CompositionError).message
      expect(message).toContain('atlas.dup')
      expect(message).toContain('atlas.missing')
    }
  })

  it('exposes the single globalSearch contribution, or undefined when absent', () => {
    const search = globalSearch({ id: 'atlas.fixture.search', component: Noop })
    const withSearch: FrontendPlugin = { id: 'atlas.fixture-search', contributions: [search] }
    const without: FrontendPlugin = { id: 'atlas.fixture', contributions: [homeWidget({ id: 'atlas.fixture.widget', component: Noop })] }

    expect(composeFrontendPlugins([without, withSearch]).globalSearch).toBe(search)
    expect(composeFrontendPlugins([without]).globalSearch).toBeUndefined()
  })

  it('fails composition naming both plugins when two supply globalSearch', () => {
    const pluginA: FrontendPlugin = {
      id: 'atlas.search-a',
      contributions: [globalSearch({ id: 'atlas.search-a.box', component: Noop })],
    }
    const pluginB: FrontendPlugin = {
      id: 'atlas.search-b',
      contributions: [globalSearch({ id: 'atlas.search-b.box', component: Noop })],
    }

    try {
      composeFrontendPlugins([pluginA, pluginB])
      expect.unreachable()
    } catch (error) {
      expect(error).toBeInstanceOf(CompositionError)
      const message = (error as CompositionError).message
      expect(message).toContain('globalSearch')
      expect(message).toContain('atlas.search-a')
      expect(message).toContain('atlas.search-b')
    }
  })
})
