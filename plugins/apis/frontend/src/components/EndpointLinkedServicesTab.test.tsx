// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointLinkedServicesTab } from './EndpointLinkedServicesTab'
import { groupsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import { endpointServicesApi } from '../lib/entities'
import { makeApi, makeEndpoint, makeServiceSummary } from '../testFixtures'
import type { EndpointService } from '../lib/types'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

const EMPTY_PAGE = { count: 0, numPages: 1, perPage: 20, page: { number: 1, objectList: [] as EndpointService[] } }

vi.mock('frontend/lib/entities', () => ({
  groupsApi: { list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  componentsApi: { list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  kindToPath: { system: '/systems', component: '/components', group: '/teams', api: '/apis' },
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

vi.mock('../lib/entities', () => ({
  endpointServicesApi: {
    list: vi.fn(),
    link: vi.fn(),
    unlink: vi.fn(),
  },
}))

function makeUsage(overrides: Partial<EndpointService> = {}): EndpointService {
  return { id: 'usage-1', service: makeServiceSummary(), linkedAt: '2026-01-01T00:00:00Z', ...overrides }
}

function mockSession(session: { isAuthenticated: boolean; isReadOnly?: boolean } | null) {
  vi.mocked(useSession).mockReturnValue({ session: session as never, isLoading: false, login: vi.fn(), logout: vi.fn() })
}

function renderTab(endpointOverrides: Parameters<typeof makeEndpoint>[0] = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EndpointLinkedServicesTab
          endpoint={makeEndpoint(endpointOverrides)}
          api={makeApi()}
          linkedServices={[]}
          onServicesChanged={vi.fn()}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EndpointLinkedServicesTab', () => {
  it('shows a removed-endpoint warning and no Link action for a removed endpoint', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'removed' })

    await waitFor(() => expect(endpointServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This endpoint was removed from the API/)).toBeDefined()
    expect(screen.queryByText('Link service')).toBeNull()
  })

  it('shows a deprecated-endpoint warning distinct from the removed-endpoint warning', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'active', deprecated: true })

    await waitFor(() => expect(endpointServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This endpoint is deprecated/)).toBeDefined()
    expect(screen.queryByText(/This endpoint was removed from the API/)).toBeNull()
  })

  it('shows both warnings when an endpoint is both deprecated and removed', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'removed', deprecated: true })

    await waitFor(() => expect(endpointServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This endpoint was removed from the API/)).toBeDefined()
    expect(screen.getByText(/This endpoint is deprecated/)).toBeDefined()
  })

  it('shows a Link service action for an active endpoint when authenticated', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'active' })

    await waitFor(() => expect(endpointServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText('Link service')).toBeDefined()
  })

  it('hides Link/Unlink actions entirely when unauthenticated (no permission)', async () => {
    mockSession(null)
    vi.mocked(endpointServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeUsage()] },
    })
    renderTab({ status: 'active' })

    await waitFor(() => expect(screen.getByText('billing-service')).toBeDefined())
    expect(screen.queryByText('Link service')).toBeNull()
    expect(screen.queryByText('Unlink')).toBeNull()
  })

  it('hides Link/Unlink actions for a read-only session', async () => {
    mockSession({ isAuthenticated: true, isReadOnly: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeUsage()] },
    })
    renderTab({ status: 'active' })

    await waitFor(() => expect(screen.getByText('billing-service')).toBeDefined())
    expect(screen.queryByText('Link service')).toBeNull()
    expect(screen.queryByText('Unlink')).toBeNull()
  })

  it('shows a per-row Unlink action when authenticated', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeUsage()] },
    })
    renderTab()

    await waitFor(() => expect(screen.getByText('Unlink')).toBeDefined())
  })

  it('searching calls the list API with the search term and resets to page 1', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(endpointServicesApi.list).toHaveBeenCalled())

    fireEvent.change(screen.getByPlaceholderText('Search services…'), { target: { value: 'billing' } })

    await waitFor(() =>
      expect(endpointServicesApi.list).toHaveBeenLastCalledWith(
        'endpoint-1',
        expect.objectContaining({ search: 'billing', page: 1 }),
      ),
    )
  })

  it('toggling sort order calls the list API with order=desc', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(endpointServicesApi.list).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: 'Sort ascending' }))

    await waitFor(() =>
      expect(endpointServicesApi.list).toHaveBeenLastCalledWith(
        'endpoint-1',
        expect.objectContaining({ order: 'desc' }),
      ),
    )
  })

  it('unlinking a service opens a styled confirm dialog and calls the unlink API on confirm', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeUsage()] },
    })
    vi.mocked(endpointServicesApi.unlink).mockResolvedValue(undefined)
    renderTab()

    await waitFor(() => expect(screen.getByText('Unlink')).toBeDefined())
    fireEvent.click(screen.getByText('Unlink'))

    await waitFor(() => expect(screen.getByText(/consumesAPI relation is not affected/i)).toBeDefined())
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => expect(endpointServicesApi.unlink).toHaveBeenCalledWith('endpoint-1', 'service-1'))
  })

  it('does not unlink when the confirmation dialog is cancelled', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeUsage()] },
    })
    renderTab()

    await waitFor(() => expect(screen.getByText('Unlink')).toBeDefined())
    fireEvent.click(screen.getByText('Unlink'))

    await waitFor(() => expect(screen.getByText(/consumesAPI relation is not affected/i)).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.queryByText(/consumesAPI relation is not affected/i)).toBeNull())
    expect(endpointServicesApi.unlink).not.toHaveBeenCalled()
  })

  it('loads team options from groupsApi for the team filter', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(endpointServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(groupsApi.list).toHaveBeenCalled())
  })
})
