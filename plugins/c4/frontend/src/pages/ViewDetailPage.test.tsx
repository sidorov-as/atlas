// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { useSession } from 'frontend/lib/SessionContext'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ViewDetailPage } from './ViewDetailPage'

vi.mock('frontend/lib/SessionContext', () => ({ useSession: vi.fn() }))

class ResizeObserverStub {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}
globalThis.ResizeObserver = ResizeObserverStub

// jsdom has no matchMedia; Gravity UI's Dialog needs it.
window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false, media: query, onchange: null, addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)

const ID = '44444444-4444-4444-8444-444444444444'
const GONE = '33333333-3333-4333-8333-333333333333'
const fetchMock = vi.fn()
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const svg = () => new Response(new Blob(['<svg />']), { status: 200 })
const settings = { level: 'systems', selection: 'selected', entities: ['s1'], entityTypes: ['actor'], relationships: 'declared' }
const view = (extra: object = {}) => ({ id: ID, name: 'Billing', description: 'Payments flow', settings, missingEntities: [], createdAt: 't', updatedAt: 't', ...extra })

function Probe() {
  const location = useLocation()
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>
}

function serve(options: { view?: object | null; diagram?: () => Response } = {}) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const target = String(url)
    if (target.includes('/diagram/')) return (options.diagram ?? svg)()
    if (init?.method === 'DELETE') return new Response(null, { status: 204 })
    if (target.endsWith(`/views/${ID}/`)) return options.view === null ? json(404, { detail: [{ msg: 'View not found' }] }) : json(200, options.view ?? view())
    return json(404, {})
  })
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={[`/system-map/views/${ID}`]}>
      <ThemeProvider theme="light">
        <Routes>
          <Route path="/system-map/views/:id" element={<ViewDetailPage />} />
          <Route path="*" element={<Probe />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  URL.createObjectURL = vi.fn(() => 'blob:1')
  URL.revokeObjectURL = vi.fn()
  vi.mocked(useSession).mockReturnValue({ session: { isReadOnly: false } } as never)
})

afterEach(() => {
  cleanup()
  fetchMock.mockReset()
  vi.unstubAllGlobals()
})

describe('ViewDetailPage', () => {
  it('shows the view and its diagram, fetched by id', async () => {
    serve()
    renderDetail()
    expect(await screen.findByRole('heading', { name: 'Billing' })).toBeDefined()
    expect(screen.getByText('Payments flow')).toBeDefined()
    await screen.findByAltText('View diagram')
    const call = fetchMock.mock.calls.find(([url]) => String(url).includes('/diagram/'))
    expect(String(call?.[0])).toContain(`/views/${ID}/diagram/`)
    expect(String(call?.[0])).toContain('theme=light')
  })

  it('offers SVG and PNG export once the diagram is shown', async () => {
    serve()
    renderDetail()
    fireEvent.load(await screen.findByAltText('View diagram'))
    expect(screen.getByRole('button', { name: 'Download SVG' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Download PNG' })).toBeDefined()
  })

  it('opens the editor from Edit', async () => {
    serve()
    renderDetail()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe(`/system-map/views/${ID}/edit`))
  })

  it('deletes after confirmation and returns to the list', async () => {
    serve()
    renderDetail()
    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(await screen.findByText(/Delete "Billing"\?/)).toBeDefined()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    fireEvent.click(screen.getAllByRole('button', { name: 'Delete' }).at(-1) as HTMLElement)
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/system-map?tab=views'))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true)
  })

  it('hides Edit and Delete for a read-only session', async () => {
    vi.mocked(useSession).mockReturnValue({ session: { isReadOnly: true } } as never)
    serve()
    renderDetail()
    await screen.findByRole('heading', { name: 'Billing' })
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })

  it('shows a not-found state for an unknown view', async () => {
    serve({ view: null })
    renderDetail()
    expect(await screen.findByText('View not found')).toBeDefined()
    expect(screen.queryByAltText('View diagram')).toBeNull()
  })

  it('warns about missing entities and does not request the diagram', async () => {
    serve({ view: view({ missingEntities: [GONE] }) })
    renderDetail()
    expect(await screen.findByText('Some entities in this view no longer exist')).toBeDefined()
    expect(screen.getByText(new RegExp(GONE))).toBeDefined()
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/diagram/'))).toBe(false)
  })

  it('explains a node-limit failure and offers Retry for render failures', async () => {
    serve({ diagram: () => json(422, { detail: [{ msg: 'too many', type: 'node_limit_exceeded', limit: 50, count: 72 }] }) })
    renderDetail()
    expect(await screen.findByText(/72 nodes but the limit is 50/)).toBeDefined()
    cleanup()
    serve({ diagram: () => json(500, { detail: [{ msg: 'x', type: 'value_error' }] }) })
    renderDetail()
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeDefined()
  })
})
