// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SystemDetailPage } from './SystemDetailPage'
import { apisApi, componentsApi, resourcesApi, systemsApi } from 'frontend/lib/entities'
import type { Paginated, SystemEntity } from 'frontend/lib/types'

afterEach(() => cleanup())

// jsdom has no ResizeObserver; Gravity UI's Table (used by ChildTable/RelationsTab) needs one to mount.
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

function emptyPage<T>(): Paginated<T> {
  return { count: 0, numPages: 0, perPage: 20, page: { number: 1, objectList: [] } }
}

vi.mock('frontend/lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/entities')>()
  return {
    ...actual,
    systemsApi: { ...actual.systemsApi, get: vi.fn(), docs: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 20, page: { number: 1, objectList: [] } }), relations: vi.fn().mockResolvedValue([]) },
    componentsApi: { ...actual.componentsApi, list: vi.fn() },
    resourcesApi: { ...actual.resourcesApi, list: vi.fn() },
    apisApi: { ...actual.apisApi, list: vi.fn() },
    architectureRelationshipsApi: { ...actual.architectureRelationshipsApi, list: vi.fn().mockResolvedValue([]) },
    tagsApi: { ...actual.tagsApi, list: vi.fn().mockResolvedValue([]) },
  }
})

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: vi.fn(() => ({
    session: { isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false },
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })),
}))

const BASE_METADATA = {
  name: 'checkout',
  title: 'Checkout',
  description: '',
  documentation: '',
  labels: {},
  tags: [],
  tagColors: {},
  links: [],
}

function makeSystem(): SystemEntity {
  return {
    id: 5,
    apiVersion: 'atlas/v1alpha1',
    kind: 'System',
    metadata: BASE_METADATA,
    spec: { owner: 'group:payments', ownerId: 1 },
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: ['architecture.subject.v1'],
  }
}

function renderSystemDetailPage(initialEntry = '/systems/5') {
  vi.mocked(systemsApi.get).mockResolvedValue(makeSystem())
  vi.mocked(componentsApi.list).mockResolvedValue(emptyPage())
  vi.mocked(resourcesApi.list).mockResolvedValue(emptyPage())
  vi.mocked(apisApi.list).mockResolvedValue(emptyPage())
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/systems/:id" element={<SystemDetailPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('SystemDetailPage', () => {
  it('exposes separately named System Context and System Architecture tabs', async () => {
    renderSystemDetailPage()
    await waitFor(() => expect(screen.getByRole('tab', { name: 'System Context' })).toBeDefined())
    expect(screen.getByRole('tab', { name: 'System Architecture' })).toBeDefined()
  })

  it('requests the context diagram endpoint for the System Context tab', async () => {
    renderSystemDetailPage()
    const image = await screen.findByAltText('context diagram')
    expect(image.getAttribute('src')).toBe('/api/plugins/atlas.c4/diagrams/system/5/?view=context&layout=LAYOUT_TOP_DOWN&show_title=true&show_legend=true&show_selected_label=true&show_person_sprite=true&show_stereotypes=true')
  })

  it('requests the architecture diagram endpoint for the System Architecture tab', async () => {
    renderSystemDetailPage()
    const image = await screen.findByAltText('architecture diagram')
    expect(image.getAttribute('src')).toBe('/api/plugins/atlas.c4/diagrams/system/5/?view=architecture&layout=LAYOUT_TOP_DOWN&show_title=true&show_legend=true&show_selected_label=true&show_person_sprite=true&show_stereotypes=true')
  })

  it('opens the Docs tab from a direct tab query parameter', async () => {
    renderSystemDetailPage('/systems/5?tab=docs')
    await waitFor(() => expect(systemsApi.docs).toHaveBeenCalledWith(5, { q: undefined, page: 1, pageSize: 20 }))
  })
})
