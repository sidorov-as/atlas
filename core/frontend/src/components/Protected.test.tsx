// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Protected } from './Protected'
import { useSession } from '../lib/SessionContext'
import type { GlobalSearchContribution, ResolvedNavItem } from '@atlas/plugin-api'
import type { SessionState } from '../lib/auth'

afterEach(() => cleanup())

vi.mock('../lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

// Stubs the real `@gravity-ui/navigation` shell (untested elsewhere in this
// codebase, and heavy to mount in jsdom) so this test isolates `Protected`'s
// own nav-item-filtering logic instead of Gravity's `AsideHeader` internals.
vi.mock('./AppShell', () => ({
  AppShell: ({
    navItems,
    globalSearch,
    children,
  }: {
    navItems: readonly ResolvedNavItem[]
    globalSearch?: GlobalSearchContribution
    children: React.ReactNode
  }) => (
    <div>
      {globalSearch && <globalSearch.component />}
      <nav>{navItems.map((item) => <span key={item.id}>{item.title}</span>)}</nav>
      {children}
    </div>
  ),
}))

const SETTINGS_NAV_ITEM: ResolvedNavItem = {
  type: 'navItem',
  id: 'atlas.core.nav.settings',
  title: 'Settings',
  route: { __routeRef: true, id: 'atlas.core.settings' },
  resolvedPath: '/settings',
}

function renderProtected(session: SessionState, globalSearch?: GlobalSearchContribution) {
  vi.mocked(useSession).mockReturnValue({
    session,
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route element={<Protected navItems={[SETTINGS_NAV_ITEM]} globalSearch={globalSearch} />}>
          <Route path="/" element={<div>page content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('Protected', () => {
  it('shows the Settings nav item for an admin', () => {
    renderProtected({ isAuthenticated: true, user: null, isAdmin: true, isReadOnly: false })
    expect(screen.getByText('Settings')).toBeDefined()
  })

  it('hides the Settings nav item for a non-admin', () => {
    renderProtected({ isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false })
    expect(screen.queryByText('Settings')).toBeNull()
  })

  it('renders the search contribution when present and nothing extra when absent', () => {
    const session = { isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false }
    const { unmount } = renderProtected(session, {
      type: 'globalSearch',
      id: 'atlas.fixture.search',
      component: () => <div>search box</div>,
    })
    expect(screen.getByText('search box')).toBeDefined()
    unmount()

    renderProtected(session)
    expect(screen.queryByText('search box')).toBeNull()
    expect(screen.getByText('page content')).toBeDefined()
  })
})
