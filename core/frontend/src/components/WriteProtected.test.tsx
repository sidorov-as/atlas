// @vitest-environment jsdom
import { act, cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { WriteProtected } from './WriteProtected'
import { useSession } from '../lib/SessionContext'
import type { SessionState } from '../lib/auth'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

vi.mock('../lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

const WRITABLE_SESSION: SessionState = {
  isAuthenticated: true,
  user: null,
  isAdmin: false,
  isReadOnly: false,
}

function deferred() {
  let resolve!: () => void
  const promise = new Promise<void>((resolvePromise) => {
    resolve = resolvePromise
  })
  return { promise, resolve }
}

function mockSession(overrides: Partial<ReturnType<typeof useSession>> = {}) {
  const value = {
    session: WRITABLE_SESSION,
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
  vi.mocked(useSession).mockReturnValue(value)
  return value
}

function renderWriteRoute() {
  return render(
    <MemoryRouter initialEntries={['/things/new']}>
      <Routes>
        <Route path="/" element={<div>safe page</div>} />
        <Route element={<WriteProtected />}>
          <Route path="/things/new" element={<div>mutation form</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('WriteProtected', () => {
  it('refreshes access state on route entry and never flashes the form while unresolved', async () => {
    const pending = deferred()
    const session = mockSession({ refresh: vi.fn(() => pending.promise) })

    renderWriteRoute()

    expect(session.refresh).toHaveBeenCalledOnce()
    expect(screen.queryByText('mutation form')).toBeNull()

    await act(async () => pending.resolve())

    expect(screen.getByText('mutation form')).toBeDefined()
  })

  it('keeps the form hidden when the access refresh failed', async () => {
    mockSession({ error: true })

    renderWriteRoute()

    await act(async () => {})
    expect(screen.queryByText('mutation form')).toBeNull()
    expect(screen.queryByText('safe page')).toBeNull()
  })

  it('redirects a read-only session to a safe route after refreshing', async () => {
    mockSession({ session: { ...WRITABLE_SESSION, isReadOnly: true } })

    renderWriteRoute()

    expect(await screen.findByText('safe page')).toBeDefined()
    expect(screen.queryByText('mutation form')).toBeNull()
  })

  it('renders the mutation route for a refreshed writable session', async () => {
    mockSession()

    renderWriteRoute()

    expect(await screen.findByText('mutation form')).toBeDefined()
  })

  it('closes an already-open form when refreshed state becomes read-only', async () => {
    const context = mockSession()
    const rendered = renderWriteRoute()
    expect(await screen.findByText('mutation form')).toBeDefined()

    vi.mocked(useSession).mockReturnValue({
      ...context,
      session: { ...WRITABLE_SESSION, isReadOnly: true },
    })
    rendered.rerender(
      <MemoryRouter initialEntries={['/things/new']}>
        <Routes>
          <Route path="/" element={<div>safe page</div>} />
          <Route element={<WriteProtected />}>
            <Route path="/things/new" element={<div>mutation form</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('safe page')).toBeDefined()
    expect(screen.queryByText('mutation form')).toBeNull()
  })
})
