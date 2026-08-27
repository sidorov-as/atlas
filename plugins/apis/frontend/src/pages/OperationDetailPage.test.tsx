// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from 'frontend/lib/api'
import { OperationDetailPage } from './OperationDetailPage'
import { apisApi } from 'frontend/lib/entities'
import { operationServicesApi, operationsApi } from '../lib/entities'
import { makeApi, makeOperation, makeOperationConsumers, makeOperationService, makeServiceSummary } from '../testFixtures'

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
  operationsApi: { get: vi.fn() },
  operationServicesApi: {
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
// OperationConsumersGraph.test.tsx's job.
vi.mock('../components/OperationConsumersGraph', () => ({
  OperationConsumersGraph: () => <div>consumers graph</div>,
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: () => ({ session: { isAuthenticated: true, user: null }, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}))

function renderPage() {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={['/apis/api-1/operations/operation-1']}>
        <Routes>
          <Route path="/apis/:apiId/operations/:operationId" element={<OperationDetailPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('OperationDetailPage', () => {
  it('renders breadcrumbs from APIs to the API name to the channel address', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation())
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('billing-api')).toBeDefined())
    expect(screen.getByText('APIs')).toBeDefined()
    // Rendered in both the breadcrumb and the header title.
    expect(screen.getAllByText('booking.created').length).toBeGreaterThan(0)
  })

  it('renders the direction badge with "Send" text for a send operation', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation({ direction: 'send' }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    // Rendered in both the header and the Overview tab's Channel details card.
    await waitFor(() => expect(screen.getAllByText('Send').length).toBeGreaterThan(0))
    expect(screen.queryByText('Receive')).toBeNull()
  })

  it('renders the direction badge with "Receive" text for a receive operation, never "Subscribe"', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation({ direction: 'receive' }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getAllByText('Receive').length).toBeGreaterThan(0))
    expect(screen.queryByText('Subscribe')).toBeNull()
    expect(screen.queryByText('Publish')).toBeNull()
  })

  it('shows a removed-operation warning naming how many services still depend on it', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation({ status: 'removed' }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      count: 2,
      numPages: 1,
      perPage: 100,
      page: {
        number: 1,
        objectList: [
          makeOperationService({ id: 'usage-1', service: makeServiceSummary() }),
          makeOperationService({ id: 'usage-2', service: makeServiceSummary({ id: 'service-2', name: 'other-service' }) }),
        ],
      },
    })

    renderPage()

    await waitFor(() => expect(screen.getByText('This operation was removed from the API')).toBeDefined())
    expect(screen.getByText('2 services still declare a dependency on it.')).toBeDefined()
  })

  it('shows no removed-operation warning for an active operation', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation({ status: 'active' }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('consumers graph')).toBeDefined())
    expect(screen.queryByText('This operation was removed from the API')).toBeNull()
  })

  it('shows a deprecated indicator on the header for a deprecated operation', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation({ deprecated: true }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('Deprecated')).toBeDefined())
  })

  it('shows no deprecated indicator for a non-deprecated operation', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation({ deprecated: false }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('consumers graph')).toBeDefined())
    expect(screen.queryByText('Deprecated')).toBeNull()
  })

  it('renders Overview, Message, and Linked services tabs with a counter', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockResolvedValue(makeOperation())
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      count: 1,
      numPages: 1,
      perPage: 100,
      page: { number: 1, objectList: [makeOperationService()] },
    })

    renderPage()

    await waitFor(() => expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined())
    expect(screen.getByRole('tab', { name: 'Message' })).toBeDefined()
    expect(screen.getByRole('tab', { name: /Linked services/ }).textContent).toContain('1')
  })

  it('shows a distinct not-found state for a nonexistent operation, with a link back to the API', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockRejectedValue(new ApiError(404, { detail: 'not found' }))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('Operation not found')).toBeDefined())
    expect(screen.getByText('Back to API')).toBeDefined()
  })

  it('shows a generic failure state for a non-404 documentation-load error', async () => {
    vi.mocked(apisApi.get).mockResolvedValue(makeApi())
    vi.mocked(operationsApi.get).mockRejectedValue(new Error('server exploded'))
    vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers())

    renderPage()

    await waitFor(() => expect(screen.getByText('server exploded')).toBeDefined())
    expect(screen.queryByText('Operation not found')).toBeNull()
  })
})
