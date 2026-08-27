// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Protected } from './Protected'
import { useSession } from '../lib/SessionContext'
import type { ResolvedNavItem } from '@atlas/plugin-api'
import type { SessionState } from '../lib/auth'

afterEach(() => cleanup())

vi.mock('../lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

// Stubs the real `@gravity-ui/navigation` shell (untested elsewhere in this
// codebase, and heavy to mount in jsdom) so this test isolates `Protected`'s
// own nav-item-filtering logic instead of Gravity's `AsideHeader` internals.
vi.mock('./AppShell', () => ({
  AppShell: ({ navItems, children }: { navItems: readonly ResolvedNavItem[]; children: React.ReactNode }) => (
    <div>
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

function renderProtected(session: SessionState) {
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
        <Route element={<Protected navItems={[SETTINGS_NAV_ITEM]} />}>
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
})
