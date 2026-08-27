// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from 'frontend/lib/api'
import { EndpointDetailPage } from './EndpointDetailPage'
import { apisApi } from 'frontend/lib/entities'
import { endpointServicesApi, endpointsApi } from '../lib/entities'
import { makeApi, makeConsumers, makeEndpoint, makeServiceSummary } from '../testFixtures'

afterEach(() => cleanup())

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

// jsdom has no matchMedia; Gravity UI's Dialog (mounted, if hidden, inside the
// Linked services tab's Link Service dialog) needs it to mount at all.
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
}))

vi.mock('frontend/lib/entities', () => ({
  apisApi: { get: vi.fn(), relations: vi.fn().mockResolvedValue([]) },
  groupsApi: { list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  componentsApi: { list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  kindToPath: { system: '/systems', component: '/components', group: '/teams', api: '/apis' },
}))

vi.mock('../lib/entities', () => ({
  endpointsApi: { get: vi.fn() },
  endpointServicesApi: {
    consumers: vi.fn(),
    // Gravity UI's TabPanel mounts every panel up front (not just the active
    // one), so the Linked services tab's own fetch runs on every render here.
    list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 20, page: { number: 1, objectList: [] } }),
    link: vi.fn(),
    unlink: vi.fn(),
  },
}))

// The graph pulls in `@xyflow/react`, which needs a lot more DOM plumbing than
// this page's own rendering logic is about — the graph's own behavior is
// EndpointConsumersGraph.test.tsx's job.
vi.mock('../components/EndpointConsumersGraph', () => ({
  EndpointConsumersGraph: () => <div>consumers graph</div>,
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: () => ({ session: { isAuthenticated: true, user: null }, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}))

function renderPage() {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={['/apis/api-1/endpoints/endpoint-1']}>
        <Routes>
          <Route path="/apis/:apiId/endpoints/:endpointId" element={<EndpointDetailPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EndpointDetailPage', () => {
  it('renders breadcrumbs from APIs to the API name to the method+path', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockResolvedValue(makeEndpoint())
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('billing-api')).toBeDefined())
    expect(screen.getByText('APIs')).toBeDefined()
    expect(screen.getByText('GET /v1/invoices')).toBeDefined()
  })

  it('shows a deprecated indicator on the header for a deprecated endpoint', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockResolvedValue(makeEndpoint({ deprecated: true }))
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('Deprecated')).toBeDefined())
  })

  it('shows no deprecated indicator for a non-deprecated endpoint', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockResolvedValue(makeEndpoint({ deprecated: false }))
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('consumers graph')).toBeDefined())
    expect(screen.queryByText('Deprecated')).toBeNull()
  })

  it('shows a removed-endpoint warning naming how many services still depend on it', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockResolvedValue(makeEndpoint({ status: 'removed' }))
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(
      makeConsumers([makeServiceSummary(), makeServiceSummary({ id: 'service-2', name: 'other-service' })], { status: 'removed' }),
    )

    renderPage()

    await waitFor(() => expect(screen.getByText('This endpoint was removed from the API')).toBeDefined())
    expect(screen.getByText('2 services still declare a dependency on it.')).toBeDefined()
  })

  it('shows no removed-endpoint warning for an active endpoint', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockResolvedValue(makeEndpoint({ status: 'active' }))
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('consumers graph')).toBeDefined())
    expect(screen.queryByText('This endpoint was removed from the API')).toBeNull()
  })

  it('renders Overview, Request, Response, and Linked services tabs with a counter', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockResolvedValue(makeEndpoint())
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers([makeServiceSummary()]))

    renderPage()

    await waitFor(() => expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined())
    expect(screen.getByRole('tab', { name: 'Request' })).toBeDefined()
    expect(screen.getByRole('tab', { name: 'Response' })).toBeDefined()
    expect(screen.getByRole('tab', { name: /Linked services/ }).textContent).toContain('1')
  })

  it('shows a distinct not-found state for a nonexistent endpoint, with a link back to the API', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockRejectedValue(new ApiError(404, { detail: 'not found' }))
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('Endpoint not found')).toBeDefined())
    expect(screen.getByText('Back to API')).toBeDefined()
  })

  it('shows a generic failure state for a non-404 documentation-load error', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(endpointsApi.get).mockRejectedValue(new Error('server exploded'))
    vi.mocked(endpointServicesApi.consumers).mockResolvedValue(makeConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('server exploded')).toBeDefined())
    expect(screen.queryByText('Endpoint not found')).toBeNull()
  })
})
