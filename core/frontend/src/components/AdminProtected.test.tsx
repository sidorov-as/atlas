// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminProtected } from './AdminProtected'
import { useSession } from '../lib/SessionContext'
import type { SessionState } from '../lib/auth'

afterEach(() => cleanup())

vi.mock('../lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

function renderAdminProtected(session: SessionState) {
  vi.mocked(useSession).mockReturnValue({
    session,
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })
  return render(
    <MemoryRouter initialEntries={['/settings']}>
      <Routes>
        <Route path="/" element={<div>home page</div>} />
        <Route element={<AdminProtected />}>
          <Route path="/settings" element={<div>settings content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminProtected', () => {
  it('renders the nested route for an admin', () => {
    renderAdminProtected({ isAuthenticated: true, user: null, isAdmin: true, isReadOnly: false })
    expect(screen.getByText('settings content')).toBeDefined()
  })

  it('redirects a non-admin away from the route without showing its content', () => {
    renderAdminProtected({ isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false })
    expect(screen.queryByText('settings content')).toBeNull()
    expect(screen.getByText('home page')).toBeDefined()
  })
})
