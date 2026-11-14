// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { useSession } from 'frontend/lib/SessionContext'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ViewsList } from './ViewsList'

vi.mock('frontend/lib/SessionContext', () => ({ useSession: vi.fn() }))

class ResizeObserverStub {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}
globalThis.ResizeObserver = ResizeObserverStub

// jsdom has no matchMedia; Gravity UI's Dialog and menus need it.
window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false, media: query, onchange: null, addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)

const fetchMock = vi.fn()
const settings = { level: 'systems', selection: 'selected', entities: ['s1'], entityTypes: ['actor'], relationships: 'declared' }
const view = (id: string, name: string, description = '') => ({ id, name, description, settings, missingEntities: [], createdAt: 't', updatedAt: 't' })
const listBody = (items: unknown[], count = items.length, numPages = 1) => ({ count, numPages, perPage: 15, page: { number: 1, objectList: items } })
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function Probe() {
  const location = useLocation()
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>
}

function renderList(url = '/system-map?tab=views') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ThemeProvider theme="light">
        <Routes>
          <Route path="/system-map" element={<><ViewsList /><Probe /></>} />
          <Route path="*" element={<Probe />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

const listCalls = () => fetchMock.mock.calls.filter(([url, init]) => String(url).includes('/views/') && (init?.method ?? 'GET') === 'GET').map(([url]) => String(url))

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  vi.mocked(useSession).mockReturnValue({ session: { isReadOnly: false } } as never)
  fetchMock.mockImplementation(async (_url: string, init?: RequestInit) => (init?.method === 'DELETE' ? new Response(null, { status: 204 }) : json(200, listBody([view('v1', 'Billing', 'Payments flow'), view('v2', 'Booking')]))))
})

afterEach(() => {
  cleanup()
  fetchMock.mockReset()
  vi.unstubAllGlobals()
})

describe('ViewsList', () => {
  it('lists views with name and description and opens one on row click', async () => {
    renderList()
    expect(await screen.findByText('Billing')).toBeDefined()
    expect(screen.getByText('Payments flow')).toBeDefined()
    expect(screen.getByText('—')).toBeDefined()
    fireEvent.click(screen.getByText('Booking'))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/system-map/views/v2'))
  })

  it('searches by name and sorts by name', async () => {
    renderList()
    await screen.findByText('Billing')
    fireEvent.change(screen.getByPlaceholderText('Search…'), { target: { value: 'bil' } })
    await waitFor(() => expect(listCalls().some((url) => url.includes('q=bil'))).toBe(true))
    fireEvent.click(screen.getByText('Name'))
    await waitFor(() => expect(listCalls().some((url) => url.includes('sort=-name'))).toBe(true))
  })

  it('reads the page from the URL and requests it', async () => {
    renderList('/system-map?tab=views&page=3')
    await screen.findByText('Billing')
    expect(listCalls()[0]).toContain('page=3')
  })

  it('offers Create view, and Edit and Delete rows actions', async () => {
    renderList()
    await screen.findByText('Billing')
    fireEvent.click(screen.getByRole('button', { name: 'Create view' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/system-map/views/new'))
  })

  it('deletes only after confirmation', async () => {
    renderList()
    const row = (await screen.findByText('Billing')).closest('tr') as HTMLElement
    fireEvent.click(within(row).getByRole('button'))
    fireEvent.click(await screen.findByText('Delete'))
    expect(await screen.findByText(/Delete "Billing"\?/)).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByText(/Delete "Billing"\?/)).toBeNull())
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)

    fireEvent.click(within(row).getByRole('button'))
    fireEvent.click(await screen.findByText('Delete'))
    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/views/v1/') && init?.method === 'DELETE')).toBe(true))
  })

  it('shows an empty state', async () => {
    fetchMock.mockImplementation(async () => json(200, listBody([])))
    renderList()
    expect(await screen.findByText(/No views yet/)).toBeDefined()
  })

  it('hides Create view and row actions for a read-only session', async () => {
    vi.mocked(useSession).mockReturnValue({ session: { isReadOnly: true } } as never)
    renderList()
    await screen.findByText('Billing')
    expect(screen.queryByRole('button', { name: 'Create view' })).toBeNull()
    const row = screen.getByText('Billing').closest('tr') as HTMLElement
    expect(within(row).queryByRole('button')).toBeNull()
  })
})
