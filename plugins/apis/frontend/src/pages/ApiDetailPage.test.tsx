// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiDetailPage } from './ApiDetailPage'
import { apisApi } from 'frontend/lib/entities'
import type { ApiEntity } from 'frontend/lib/types'

// Vitest doesn't auto-run Testing Library's cleanup between tests the way Jest does.
afterEach(() => cleanup())

// jsdom has no ResizeObserver; Gravity UI's Table (used by RelationsTab) needs one to mount.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

// jsdom has no matchMedia; Gravity UI's Modal (used by ConfirmDialog) needs it to mount.
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

// Spreads the real module's exports (rather than replacing it outright) so an
// unrelated export this test doesn't care about (e.g. `HomePage.tsx`'s
// count-row apis, reached transitively through `frontend/plugins/composition`)
// never breaks this suite just by existing.
vi.mock('frontend/lib/entities', async (importOriginal) => ({
  ...(await importOriginal<typeof import('frontend/lib/entities')>()),
  architectureRelationshipsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  apisApi: {
    get: vi.fn(),
    relations: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: () => ({
    session: { isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false },
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  }),
}))

// The doc viewer's own render/fallback behavior is exercised by ApiSpecPanel's
// own logic (js-yaml parsing, Redoc/AsyncAPI mounting); here we only need to
// verify ApiDetailPage wires the right tabs and actions for a given API.
vi.mock('../components/ApiSpecPanel', () => ({
  ApiDocumentationView: () => <div>documentation view</div>,
  DownloadSpecButton: ({ api }: { api: ApiEntity }) => (api.spec.specContent ? <button>Download spec</button> : null),
  StaleSpecLabel: () => <span>Stale spec</span>,
  EndpointSyncFailedLabel: () => <span>Endpoint sync failed</span>,
  OperationSyncFailedLabel: () => <span>Operation sync failed</span>,
}))

// The openapi Operations tab's own list/filter/fetch behavior is exercised by
// EndpointsListTab's own tests; here we only need to verify ApiDetailPage
// wires the sync-failed indicator alongside it.
vi.mock('../components/EndpointsListTab', () => ({
  EndpointsListTab: () => <div>endpoints list</div>,
}))

// Same rationale as EndpointsListTab above, for the Operations tab.
vi.mock('../components/OperationsListTab', () => ({
  OperationsListTab: () => <div>operations list</div>,
}))

vi.mock('frontend/components/DocumentationPreview', () => ({
  DocumentationPreview: ({ value }: { value: string }) => <div>{value}</div>,
}))

const BASE_METADATA = {
  name: 'user-api',
  title: '',
  description: '',
  documentation: '',
  labels: {},
  tags: [],
  tagColors: {},
  links: [],
}

function makeApi(overrides: Partial<ApiEntity['spec']> = {}, documentation = ''): ApiEntity {
  return {
    id: 1,
    apiVersion: 'atlas/v1alpha1',
    kind: 'API',
    metadata: { ...BASE_METADATA, documentation },
    spec: {
      type: 'openapi',
      owner: 'group:platform',
      ownerId: 1,
      system: 'system:user-management',
      systemId: 1,
      specSource: 'inline',
      specUrl: '',
      specContent: '',
      specResolvedAt: null,
      specResolveFailed: false,
      endpointsSyncedAt: null,
      endpointsSyncFailed: false,
      operationsSyncedAt: null,
      operationsSyncFailed: false,
      resolvedBaseUrl: '',
      resolvedProtocol: '',
      ...overrides,
    },
    status: 'active',
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: [],
  }
}

function renderApiDetailPage(api: ApiEntity) {
  vi.mocked(apisApi.get).mockResolvedValue(api)
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={['/apis/1']}>
        <Routes>
          <Route path="/apis/:id" element={<ApiDetailPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('ApiDetailPage', () => {
  it('renders full documentation in Overview rather than the short description', async () => {
    renderApiDetailPage(makeApi({}, '## API guide\n\nUse a token.'))
    await waitFor(() => expect(screen.getByText(/API guide/)).toBeDefined())
    expect(screen.getByText(/Use a token/)).toBeDefined()
  })

  it('shows a Specification tab for openapi', async () => {
    renderApiDetailPage(makeApi({ type: 'openapi', specContent: 'openapi: 3.0.0' }))
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Specification' })).toBeDefined())
  })

  it('shows a Specification tab for asyncapi', async () => {
    renderApiDetailPage(makeApi({ type: 'asyncapi', specContent: 'asyncapi: 3.0.0' }))
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Specification' })).toBeDefined())
  })

  it('shows a download-only Specification tab for grpc and graphql', async () => {
    renderApiDetailPage(makeApi({ type: 'grpc', specContent: 'service Foo {}' }))
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined())
    expect(screen.getByRole('tab', { name: 'Specification' }).textContent).toBe('Specification')
  })

  it('shows the download action in the Specification tab for every type when spec content is present', async () => {
    renderApiDetailPage(makeApi({ type: 'graphql', specContent: 'type Query {}' }))
    const specification = await screen.findByRole('tab', { name: 'Specification' })
    specification.click()
    await waitFor(() => expect(screen.getByText('Download spec')).toBeDefined())
    expect(screen.getByText(/No embedded viewer is available for GRAPHQL/i)).toBeDefined()
  })

  it('shows no download action when spec content is empty', async () => {
    renderApiDetailPage(makeApi({ type: 'grpc', specContent: '' }))
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined())
    expect(screen.queryByText('Download spec')).toBeNull()
  })

  it('shows the stale-fetch label when spec_resolve_failed is true', async () => {
    renderApiDetailPage(makeApi({ specContent: 'openapi: 3.0.0', specResolveFailed: true }))
    ;(await screen.findByRole('tab', { name: 'Specification' })).click()
    await waitFor(() => expect(screen.getAllByText('Stale spec').length).toBeGreaterThan(0))
  })

  it('shows no stale-fetch label when spec_resolve_failed is false', async () => {
    renderApiDetailPage(makeApi({ specContent: 'openapi: 3.0.0', specResolveFailed: false }))
    ;(await screen.findByRole('tab', { name: 'Specification' })).click()
    await waitFor(() => expect(screen.getByText('Download spec')).toBeDefined())
    expect(screen.queryByText('Stale spec')).toBeNull()
  })

  it('shows the endpoint-sync-failed label on the Operations tab when endpoints_sync_failed is true', async () => {
    renderApiDetailPage(makeApi({ endpointsSyncFailed: true }))
    ;(await screen.findByRole('tab', { name: 'Operations' })).click()
    await waitFor(() => expect(screen.getByText('Endpoint sync failed')).toBeDefined())
  })

  it('shows no endpoint-sync-failed label when endpoints_sync_failed is false', async () => {
    renderApiDetailPage(makeApi({ endpointsSyncFailed: false }))
    ;(await screen.findByRole('tab', { name: 'Operations' })).click()
    await waitFor(() => expect(screen.getByText('endpoints list')).toBeDefined())
    expect(screen.queryByText('Endpoint sync failed')).toBeNull()
  })

  it('shows the operation-sync-failed label on the Operations tab when operations_sync_failed is true', async () => {
    renderApiDetailPage(makeApi({ type: 'asyncapi', operationsSyncFailed: true }))
    ;(await screen.findByRole('tab', { name: 'Operations' })).click()
    await waitFor(() => expect(screen.getByText('Operation sync failed')).toBeDefined())
  })

  it('shows no operation-sync-failed label when operations_sync_failed is false', async () => {
    renderApiDetailPage(makeApi({ type: 'asyncapi', operationsSyncFailed: false }))
    ;(await screen.findByRole('tab', { name: 'Operations' })).click()
    await waitFor(() => expect(screen.getByText('operations list')).toBeDefined())
    expect(screen.queryByText('Operation sync failed')).toBeNull()
  })
})
