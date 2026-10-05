// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationLinkedServicesTab } from './OperationLinkedServicesTab'
import { groupsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import { operationServicesApi } from '../lib/entities'
import { makeOperation, makeOperationService } from '../testFixtures'
import type { OperationService } from '../lib/types'

const paginationControl = () => document.querySelector('[data-qa="pagination-page-sizer"]')

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

const EMPTY_PAGE = { count: 0, numPages: 1, perPage: 20, page: { number: 1, objectList: [] as OperationService[] } }

vi.mock('frontend/lib/entities', () => ({
  groupsApi: { list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  componentsApi: { list: vi.fn().mockResolvedValue({ count: 0, numPages: 1, perPage: 100, page: { number: 1, objectList: [] } }) },
  kindToPath: { system: '/systems', component: '/components', group: '/teams', api: '/apis' },
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

vi.mock('../lib/entities', () => ({
  operationServicesApi: {
    list: vi.fn(),
    link: vi.fn(),
    unlink: vi.fn(),
  },
}))

function mockSession(session: { isAuthenticated: boolean; isReadOnly?: boolean } | null) {
  vi.mocked(useSession).mockReturnValue({ session: session as never, isLoading: false, login: vi.fn(), logout: vi.fn() })
}

function renderTab(operationOverrides: Parameters<typeof makeOperation>[0] = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <OperationLinkedServicesTab
          operation={makeOperation(operationOverrides)}
          onServicesChanged={vi.fn()}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('OperationLinkedServicesTab', () => {
  it('shows a removed-operation warning and no Link action for a removed operation', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'removed' })

    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This operation was removed from the API/)).toBeDefined()
    expect(screen.queryByText('Link service')).toBeNull()
  })

  it('shows a deprecated-operation warning distinct from the removed-operation warning', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'active', deprecated: true })

    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This operation is deprecated/)).toBeDefined()
    expect(screen.queryByText(/This operation was removed from the API/)).toBeNull()
  })

  it('shows both warnings when an operation is both deprecated and removed', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'removed', deprecated: true })

    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText(/This operation was removed from the API/)).toBeDefined()
    expect(screen.getByText(/This operation is deprecated/)).toBeDefined()
  })

  it('shows a Link service action for an active operation when authenticated', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab({ status: 'active' })

    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())
    expect(screen.getByText('Link service')).toBeDefined()
  })

  it('hides Link/Unlink actions entirely when unauthenticated (no permission)', async () => {
    mockSession(null)
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeOperationService()] },
    })
    renderTab({ status: 'active' })

    await waitFor(() => expect(screen.getByText('billing-service')).toBeDefined())
    expect(screen.queryByText('Link service')).toBeNull()
    expect(screen.queryByText('Unlink')).toBeNull()
  })

  it('hides Link/Unlink actions for a read-only session', async () => {
    mockSession({ isAuthenticated: true, isReadOnly: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeOperationService()] },
    })
    renderTab({ status: 'active' })

    await waitFor(() => expect(screen.getByText('billing-service')).toBeDefined())
    expect(screen.queryByText('Link service')).toBeNull()
    expect(screen.queryByText('Unlink')).toBeNull()
  })

  it('shows a per-row Unlink action and a role badge when authenticated', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeOperationService({ role: 'publisher' })] },
    })
    renderTab()

    await waitFor(() => expect(screen.getByText('Unlink')).toBeDefined())
    expect(screen.getByText('Publisher')).toBeDefined()
  })

  it('searching calls the list API with the search term and resets to page 1', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())

    fireEvent.change(screen.getByPlaceholderText('Search services…'), { target: { value: 'billing' } })

    await waitFor(() =>
      expect(operationServicesApi.list).toHaveBeenLastCalledWith(
        'operation-1',
        expect.objectContaining({ search: 'billing', page: 1 }),
      ),
    )
  })

  it('filtering by role calls the list API with role=publisher and resets to page 1', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())

    // "Role" also labels the table's Role column, so scope to the filter
    // Select's placeholder, which renders first in document order.
    fireEvent.click(screen.getAllByText('Role')[0])
    fireEvent.click(await screen.findByText('Publisher'))

    await waitFor(() =>
      expect(operationServicesApi.list).toHaveBeenLastCalledWith(
        'operation-1',
        expect.objectContaining({ role: 'publisher', page: 1 }),
      ),
    )
  })

  it('toggling sort order calls the list API with order=desc', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: 'Sort ascending' }))

    await waitFor(() =>
      expect(operationServicesApi.list).toHaveBeenLastCalledWith(
        'operation-1',
        expect.objectContaining({ order: 'desc' }),
      ),
    )
  })

  it('unlinking a service opens a styled confirm dialog and calls the unlink API with the row\'s role on confirm', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeOperationService({ role: 'publisher' })] },
    })
    vi.mocked(operationServicesApi.unlink).mockResolvedValue(undefined)
    renderTab()

    await waitFor(() => expect(screen.getByText('Unlink')).toBeDefined())
    fireEvent.click(screen.getByText('Unlink'))

    await waitFor(() => expect(screen.getByText(/from this operation/i)).toBeDefined())
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => expect(operationServicesApi.unlink).toHaveBeenCalledWith('operation-1', 'service-1', 'publisher'))
  })

  it('does not unlink when the confirmation dialog is cancelled', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      ...EMPTY_PAGE,
      count: 1,
      page: { number: 1, objectList: [makeOperationService()] },
    })
    renderTab()

    await waitFor(() => expect(screen.getByText('Unlink')).toBeDefined())
    fireEvent.click(screen.getByText('Unlink'))

    await waitFor(() => expect(screen.getByText(/from this operation/i)).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.queryByText(/from this operation/i)).toBeNull())
    expect(operationServicesApi.unlink).not.toHaveBeenCalled()
  })

  it('loads team options from groupsApi for the team filter', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)
    renderTab()
    await waitFor(() => expect(groupsApi.list).toHaveBeenCalled())
  })

  it('shows the pagination control for a short list and sends the default page size', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue({
      count: 18, numPages: 2, perPage: 15, page: { number: 1, objectList: [makeOperationService()] },
    })

    renderTab()

    await waitFor(() => expect(paginationControl()).not.toBeNull())
    expect(operationServicesApi.list).toHaveBeenLastCalledWith('operation-1', expect.objectContaining({ pageSize: 15 }))
  })

  it('reads page and page_size from the URL', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)

    render(
      <ThemeProvider theme="light">
        <MemoryRouter initialEntries={['/?page=2&page_size=30']}>
          <OperationLinkedServicesTab operation={makeOperation()} onServicesChanged={vi.fn()} />
        </MemoryRouter>
      </ThemeProvider>,
    )

    await waitFor(() =>
      expect(operationServicesApi.list).toHaveBeenLastCalledWith('operation-1', expect.objectContaining({ page: 2, pageSize: 30 })),
    )
  })

  it('hides the pagination control when the list is empty', async () => {
    mockSession({ isAuthenticated: true })
    vi.mocked(operationServicesApi.list).mockResolvedValue(EMPTY_PAGE)

    renderTab()

    await waitFor(() => expect(operationServicesApi.list).toHaveBeenCalled())
    expect(paginationControl()).toBeNull()
  })
})
