// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { systemEntityDetailTabs } from './system'
import { componentsApi, systemsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import type { CatalogEntityUnion, SystemEntity } from 'frontend/lib/types'

afterEach(() => cleanup())
beforeEach(() => {
  vi.clearAllMocks()
  mockSession(false)
})

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = ResizeObserverStub
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
  })),
})
const writeText = vi.fn().mockResolvedValue(undefined)
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })

vi.mock('frontend/lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('frontend/lib/entities')>()
  return {
    ...actual,
    componentsApi: { ...actual.componentsApi, list: vi.fn() },
    systemsApi: { ...actual.systemsApi, docs: vi.fn(), update: vi.fn() },
    tagsApi: { ...actual.tagsApi, list: vi.fn().mockResolvedValue([]) },
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

const SystemComponentsTab = systemEntityDetailTabs.find((tab) => tab.value === 'components')!.component
const SystemDocsTab = systemEntityDetailTabs.find((tab) => tab.value === 'docs')!.component

function makeSystem(overrides: Partial<SystemEntity> = {}): SystemEntity {
  return {
    id: 'system-1',
    apiVersion: 'atlas/v1alpha1',
    kind: 'System',
    metadata: {
      name: 'checkout', title: 'Checkout', description: '', documentation: '',
      labels: {}, tags: [], tagColors: {}, links: [],
    },
    spec: { owner: 'group:platform', ownerId: 'group-1' },
    status: 'active',
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: [],
    ...overrides,
  }
}

const EMPTY_PAGE = { count: 0, numPages: 1, perPage: 15, page: { number: 1, objectList: [] } }

function renderTab(system: SystemEntity) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <SystemComponentsTab entity={system as CatalogEntityUnion} />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

function docsTabTree(system: SystemEntity, initialEntry = '/') {
  return (
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={[initialEntry]}>
        <SystemDocsTab entity={system as CatalogEntityUnion} />
      </MemoryRouter>
    </ThemeProvider>
  )
}

function renderDocsTab(system: SystemEntity, initialEntry = '/') {
  return render(docsTabTree(system, initialEntry))
}

describe('SystemComponentsTab', () => {
  it('shows no parent-removed banner and excludes removed Components by default for an active System', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab(makeSystem({ status: 'active' }))

    await waitFor(() => expect(componentsApi.list).toHaveBeenCalled())
    expect(componentsApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ status: undefined }))
    expect(screen.queryByText(/is removed/)).toBeNull()
  })

  it('shows a parent-removed banner for a removed System, naming Components', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab(makeSystem({ status: 'removed' }))

    await waitFor(() => expect(componentsApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This System is removed/)).toBeDefined()
    expect(screen.getByText(/Components below/)).toBeDefined()
  })

  it('reveals removed Components via the Show removed toggle', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab(makeSystem({ status: 'active' }))
    await waitFor(() => expect(componentsApi.list).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('checkbox', { name: 'Show removed' }))

    await waitFor(() =>
      expect(componentsApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'all' })),
    )
  })
})

describe('SystemDocsTab', () => {
  const docsPage = {
    count: 2,
    numPages: 1,
    perPage: 20,
    page: {
      number: 1,
      objectList: [
        { title: 'Runbook', description: 'Production recovery', url: 'https://example.test/runbook', type: 'runbook' },
        { title: 'Dashboard', description: 'Metrics', url: 'https://example.test/dashboard', type: 'dashboard' },
      ],
    },
  }

  it('loads the URL-backed search state and renders document links', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue(docsPage)
    renderDocsTab(makeSystem(), '/?q=recovery&page=2')

    await waitFor(() => expect(systemsApi.docs).toHaveBeenCalledWith('system-1', { q: 'recovery', page: 2, pageSize: 20 }))
    expect(screen.getByText('Runbook')).toBeDefined()
    expect(screen.getByText('runbook')).toBeDefined()
    expect(screen.getByText('Production recovery')).toBeDefined()
    expect(screen.getByLabelText('Open Runbook').getAttribute('target')).toBe('_blank')
    expect(screen.getByLabelText('Open Runbook').getAttribute('rel')).toBe('noreferrer')
  })

  it('adds a link by PATCHing the complete ordered list', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue({ ...docsPage, count: 0, page: { number: 1, objectList: [] } })
    vi.mocked(systemsApi.update).mockResolvedValue(makeSystem())
    renderDocsTab(makeSystem({ metadata: { ...makeSystem().metadata, links: [docsPage.page.objectList[0]] } }))

    await screen.findByRole('button', { name: 'Add' })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    fireEvent.change(screen.getByPlaceholderText('https://…'), { target: { value: 'https://example.test/dashboard' } })
    fireEvent.change(screen.getByPlaceholderText('Title'), { target: { value: 'Dashboard' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[1])

    await waitFor(() => expect(systemsApi.update).toHaveBeenCalledWith('system-1', {
      metadata: {
        links: [
          docsPage.page.objectList[0],
          { title: 'Dashboard', description: '', url: 'https://example.test/dashboard', type: '' },
        ],
      },
    }))
  })

  it('requires a title before saving a link', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue({ ...docsPage, count: 0, page: { number: 1, objectList: [] } })
    renderDocsTab(makeSystem())

    fireEvent.click(await screen.findByRole('button', { name: 'Add' }))
    fireEvent.change(screen.getByPlaceholderText('https://…'), { target: { value: 'https://example.test/untitled' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[1])

    expect(await screen.findByText('Title is required')).toBeDefined()
    expect(systemsApi.update).not.toHaveBeenCalled()
  })

  it('asks for confirmation before deleting a link', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue(docsPage)
    vi.mocked(systemsApi.update).mockResolvedValue(makeSystem())
    renderDocsTab(makeSystem({ metadata: { ...makeSystem().metadata, links: docsPage.page.objectList } }))

    await screen.findByText('Runbook')
    const firstActionsButton = document.querySelector<HTMLButtonElement>('.g-table__actions-button')
    expect(firstActionsButton).not.toBeNull()
    fireEvent.click(firstActionsButton!)
    fireEvent.click(await screen.findByText('Remove'))

    expect(await screen.findByText('Delete "Runbook"? This action cannot be undone.')).toBeDefined()
    expect(systemsApi.update).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(systemsApi.update).toHaveBeenCalledWith('system-1', {
      metadata: { links: [docsPage.page.objectList[1]] },
    }))
  })

  it('hides mutation controls for YAML-managed Systems', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue(docsPage)
    renderDocsTab(makeSystem({ ingestedFrom: 'org/catalog' }))

    await screen.findByText('Runbook')
    expect(screen.queryByRole('button', { name: 'Add' })).toBeNull()
    expect(document.querySelector('.g-table__actions')).toBeNull()
  })

  it('preserves document access but hides authoring controls for a read-only session', async () => {
    mockSession(true)
    vi.mocked(systemsApi.docs).mockResolvedValue(docsPage)
    renderDocsTab(makeSystem())

    await screen.findByText('Runbook')
    expect(screen.getByPlaceholderText('Search documentation')).toBeDefined()
    expect(screen.getByLabelText('Open Runbook')).toBeDefined()
    fireEvent.click(screen.getByLabelText('Copy Runbook'))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('https://example.test/runbook'))
    expect(screen.queryByRole('button', { name: 'Add' })).toBeNull()
    expect(document.querySelector('.g-table__actions')).toBeNull()
    expect(screen.queryByText('Add link')).toBeNull()
  })

  it('closes an open authoring dialog when the session becomes read-only', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue(docsPage)
    const system = makeSystem()
    const { rerender } = renderDocsTab(system)

    fireEvent.click(await screen.findByRole('button', { name: 'Add' }))
    expect(screen.getByText('Add link')).toBeDefined()

    mockSession(true)
    rerender(docsTabTree(system))

    expect(screen.queryByText('Add link')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Add' })).toBeNull()
    expect(systemsApi.update).not.toHaveBeenCalled()
  })

  it('copies a link URL and reports success', async () => {
    writeText.mockClear()
    vi.mocked(systemsApi.docs).mockResolvedValue(docsPage)
    renderDocsTab(makeSystem())

    fireEvent.click(await screen.findByLabelText('Copy Runbook'))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('https://example.test/runbook'))
    expect(screen.getByText('Link copied')).toBeDefined()
  })
})
