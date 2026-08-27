// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FlowsListPage } from './FlowsListPage'
import { useSession } from 'frontend/lib/SessionContext'

afterEach(() => cleanup())

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverStub

window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)

vi.mock('frontend/lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('frontend/lib/entities')>()
  return {
    ...actual,
    flowsApi: {
      ...actual.flowsApi,
      list: vi.fn().mockResolvedValue({
        count: 1,
        numPages: 1,
        perPage: 20,
        page: { number: 1, objectList: [{ id: 1, system: 'system:payments', name: 'checkout', description: '', steps: [] }] },
      }),
    },
    groupsApi: { ...actual.groupsApi, list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
    systemsApi: { ...actual.systemsApi, list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  }
})

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

function mockSession(isReadOnly: boolean) {
  vi.mocked(useSession).mockReturnValue({
    session: { isAuthenticated: true, user: null, isAdmin: false, isReadOnly },
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })
}

function renderPage() {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <FlowsListPage />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('FlowsListPage', () => {
  beforeEach(() => mockSession(false))

  it('shows the Add Flow action and row actions for a normal session', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('checkout')).toBeDefined())
    expect(screen.getByRole('button', { name: 'Add Flow' })).toBeDefined()
    expect(screen.getByRole('button', { name: /actions/i })).toBeDefined()
  })

  it('hides the Add Flow action and row actions for a read-only session (flow-management spec)', async () => {
    mockSession(true)
    renderPage()
    await waitFor(() => expect(screen.getByText('checkout')).toBeDefined())
    expect(screen.queryByRole('button', { name: 'Add Flow' })).toBeNull()
    expect(screen.queryByRole('button', { name: /actions/i })).toBeNull()
  })
})
