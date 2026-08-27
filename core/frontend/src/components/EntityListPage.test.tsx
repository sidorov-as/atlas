// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { EntityListPage } from './EntityListPage'
import { groupsApi, tagsApi } from '../lib/entities'
import { useSession } from '../lib/SessionContext'
import type { SessionState } from '../lib/auth'

afterEach(() => cleanup())

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = ResizeObserverStub

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

vi.mock('../lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/entities')>()
  return {
    ...actual,
    groupsApi: { ...actual.groupsApi, list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 20, page: { number: 1, objectList: [] } }) },
    tagsApi: { ...actual.tagsApi, list: vi.fn().mockResolvedValue([]) },
  }
})

vi.mock('../lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

function mockSession(session: SessionState) {
  vi.mocked(useSession).mockReturnValue({
    session,
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })
}

const NOT_READ_ONLY: SessionState = { isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false }

const entity = {
  id: 'system-1',
  ingestedFrom: null,
  metadata: { name: 'payments', title: 'Payments', description: '', documentation: '', labels: {}, tags: [], tagColors: {}, links: [] },
  spec: { owner: 'group:platform' },
}

function renderPage(overrides: { fetchList?: Parameters<typeof EntityListPage>[0]['fetchList'] } = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EntityListPage
          title="Systems"
          description="All systems"
          addLabel="Add System"
          onAdd={() => {}}
          fetchList={overrides.fetchList
            ?? (async () => ({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [entity] } }))}
          columns={[{ id: 'name', name: 'Name', template: (item) => item.metadata.title }]}
          rowTo={(item) => `/systems/${item.id}`}
          railFields={() => []}
          remove={async () => {}}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EntityListPage', () => {
  beforeEach(() => mockSession(NOT_READ_ONLY))

  it('renders page chrome before the table-and-preview flex row', async () => {
    const { container } = renderPage()

    await waitFor(() => expect(screen.getByText('Payments')).toBeDefined())
    expect(groupsApi.list).toHaveBeenCalled()
    expect(tagsApi.list).toHaveBeenCalled()

    const root = container.firstElementChild
    const contentRow = root?.lastElementChild as HTMLElement
    expect(root?.firstElementChild?.textContent).toContain('Systems')
    expect(root?.children[2]?.textContent).toContain('Add System')
    expect(contentRow.style.display).toBe('flex')
    expect(contentRow.querySelector('table')?.textContent).toContain('Payments')
  })

  it('excludes removed entities by default and reveals them via the Show removed toggle', async () => {
    const fetchList = vi.fn().mockResolvedValue({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [entity] } })
    renderPage({ fetchList })

    await waitFor(() => expect(fetchList).toHaveBeenCalled())
    expect(fetchList).toHaveBeenLastCalledWith(expect.objectContaining({ status: undefined }))

    fireEvent.click(screen.getByRole('checkbox', { name: 'Show removed' }))

    await waitFor(() =>
      expect(fetchList).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'all' })),
    )
  })

  it('shows a Removed badge for a removed row once the toggle is on, not before', async () => {
    const removedEntity = { ...entity, id: 'system-2', status: 'removed' as const, metadata: { ...entity.metadata, name: 'legacy', title: 'Legacy' } }
    const fetchList = vi.fn().mockResolvedValue({
      count: 2, numPages: 1, perPage: 20, page: { number: 1, objectList: [entity, removedEntity] },
    })
    renderPage({ fetchList })

    await waitFor(() => expect(screen.getByText('Legacy')).toBeDefined())
    expect(screen.queryByText('Removed')).toBeNull()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Show removed' }))

    await waitFor(() => expect(screen.getByText('Removed')).toBeDefined())
  })

  it('row-action Remove opens a revivable-phrased confirm dialog, not a delete one, and calls the soft-remove callback on confirm', async () => {
    const remove = vi.fn().mockResolvedValue(undefined)
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <EntityListPage
            title="Systems"
            description="All systems"
            addLabel="Add System"
            onAdd={() => {}}
            fetchList={async () => ({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [entity] } })}
            columns={[{ id: 'name', name: 'Name', template: (item) => item.metadata.title }]}
            rowTo={(item) => `/systems/${item.id}`}
            railFields={() => []}
            remove={remove}
          />
        </MemoryRouter>
      </ThemeProvider>,
    )
    await waitFor(() => expect(screen.getByText('Payments')).toBeDefined())

    fireEvent.click(screen.getByRole('button', { name: /actions/i }))
    fireEvent.click(await screen.findByText('Remove'))

    await waitFor(() => expect(screen.getByText(/revived later/i)).toBeDefined())
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => expect(remove).toHaveBeenCalledWith('system-1'))
  })

  it('row-action Remove does not call the soft-remove callback when the confirm dialog is cancelled', async () => {
    const remove = vi.fn().mockResolvedValue(undefined)
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <EntityListPage
            title="Systems"
            description="All systems"
            addLabel="Add System"
            onAdd={() => {}}
            fetchList={async () => ({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [entity] } })}
            columns={[{ id: 'name', name: 'Name', template: (item) => item.metadata.title }]}
            rowTo={(item) => `/systems/${item.id}`}
            railFields={() => []}
            remove={remove}
          />
        </MemoryRouter>
      </ThemeProvider>,
    )
    await waitFor(() => expect(screen.getByText('Payments')).toBeDefined())

    fireEvent.click(screen.getByRole('button', { name: /actions/i }))
    fireEvent.click(await screen.findByText('Remove'))

    await waitFor(() => expect(screen.getByText(/revived later/i)).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.queryByText(/revived later/i)).toBeNull())
    expect(remove).not.toHaveBeenCalled()
  })

  it('hides row actions for an already-removed entity', async () => {
    const removedEntity = { ...entity, status: 'removed' as const }
    renderPage({
      fetchList: async () => ({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [removedEntity] } }),
    })
    await waitFor(() => expect(screen.getByText('Payments')).toBeDefined())

    expect(screen.queryByRole('button', { name: /actions/i })).toBeNull()
  })

  it('hides the Add action and row actions for a read-only session (catalog-web-ui spec)', async () => {
    mockSession({ isAuthenticated: true, user: null, isAdmin: false, isReadOnly: true })
    renderPage()
    await waitFor(() => expect(screen.getByText('Payments')).toBeDefined())

    expect(screen.queryByRole('button', { name: 'Add System' })).toBeNull()
    expect(screen.queryByRole('button', { name: /actions/i })).toBeNull()
  })
})
