// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SearchBox } from './SearchBox'
import { SearchUnavailableError, searchApi, type KindCount, type SearchResult } from '../lib/api'

vi.mock('../lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../lib/api')>()
  return { ...original, searchApi: { search: vi.fn(), status: vi.fn() } }
})

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

function result(overrides: Partial<SearchResult> = {}): SearchResult {
  return { id: 'system:1', kind: 'system', kindLabel: 'System', title: 'Billing', link: '/systems/1', snippet: null, ...overrides }
}

function response(results: SearchResult[], facets?: KindCount[]) {
  return { results, total: results.length, page: 1, pageSize: 20, hasMore: false, facets }
}

function LocationProbe() {
  return <div data-testid="location">{useLocation().pathname}</div>
}

function renderBox() {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={['/']}>
        <SearchBox />
        <Routes>
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

async function typeQuery(text: string) {
  fireEvent.click(screen.getByRole('button', { name: /search/i }))
  const input = await screen.findByLabelText('Search query')
  fireEvent.change(input, { target: { value: text } })
  return input
}

beforeEach(() => {
  vi.mocked(searchApi.status).mockResolvedValue({ ok: true, engineHealthy: true, pendingCount: 0, oldestPendingAgeSeconds: null })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('SearchDialog', () => {
  it('opens from the box, queries after the debounce and shows kind label and snippet', async () => {
    vi.mocked(searchApi.search).mockResolvedValue(
      response([result({ snippet: { text: 'handles invoices', matches: [[8, 16]] } })]),
    )
    renderBox()
    await typeQuery('invoices')

    expect(await screen.findByText('Billing')).toBeDefined()
    expect(screen.getByText('System')).toBeDefined()
    expect(screen.getByText('invoices').tagName).toBe('MARK')
    expect(searchApi.search).toHaveBeenCalledTimes(1)
    expect(vi.mocked(searchApi.search).mock.calls[0][0]).toBe('invoices')
  })

  it('shows a tab per kind with its count and narrows the query when one is picked', async () => {
    const facets = [
      { kind: 'system', kindLabel: 'System', count: 3 },
      { kind: 'api', kindLabel: 'API', count: 2 },
    ]
    vi.mocked(searchApi.search).mockResolvedValue(response([result()], facets))
    renderBox()
    await typeQuery('billing')

    expect((await screen.findByRole('tab', { name: /^System/ })).textContent).toContain('3')
    expect(screen.getByRole('tab', { name: /^All/ }).textContent).toContain('5')
    expect(screen.getByRole('tab', { name: /^API/ }).textContent).toContain('2')
    expect(vi.mocked(searchApi.search).mock.calls[0][1]?.kind ?? null).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: /^API/ }))

    await waitFor(() => expect(vi.mocked(searchApi.search).mock.calls.at(-1)?.[1]?.kind).toBe('api'))
    expect(screen.getByRole('tab', { name: /^API/ }).getAttribute('aria-selected')).toBe('true')
  })

  it('keeps a picked kind selectable, with a zero count, when a new query has no match in it', async () => {
    vi.mocked(searchApi.search).mockResolvedValueOnce(
      response([result()], [{ kind: 'system', kindLabel: 'System', count: 1 }, { kind: 'api', kindLabel: 'API', count: 1 }]),
    )
    renderBox()
    await typeQuery('billing')
    const apiTab = await screen.findByRole('tab', { name: /^API/ })
    vi.mocked(searchApi.search).mockResolvedValue(response([], [{ kind: 'system', kindLabel: 'System', count: 4 }]))
    fireEvent.click(apiTab)
    fireEvent.change(await screen.findByLabelText('Search query'), { target: { value: 'ledger' } })

    await waitFor(() => expect(screen.getByRole('tab', { name: /^API/ }).textContent).toContain('0'))
  })

  it('opens from the keyboard shortcut and stops listening after unmount', async () => {
    const { unmount } = renderBox()
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(await screen.findByLabelText('Search query')).toBeDefined()

    unmount()
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(screen.queryByLabelText('Search query')).toBeNull()
  })

  it('shows an empty state when nothing matches', async () => {
    vi.mocked(searchApi.search).mockResolvedValue(response([]))
    renderBox()
    await typeQuery('zzz')
    expect(await screen.findByText('No results found.')).toBeDefined()
  })

  it('shows an unavailable message instead of "no results" when the service is down', async () => {
    vi.mocked(searchApi.search).mockRejectedValue(new SearchUnavailableError())
    renderBox()
    await typeQuery('anything')
    expect(await screen.findByText(/currently unavailable/i)).toBeDefined()
    expect(screen.queryByText('No results found.')).toBeNull()
  })

  it('shows a stale-index notice when the backlog is old', async () => {
    vi.mocked(searchApi.status).mockResolvedValue({ ok: true, engineHealthy: true, pendingCount: 3, oldestPendingAgeSeconds: 900 })
    renderBox()
    fireEvent.click(screen.getByRole('button', { name: /search/i }))
    expect(await screen.findByText(/index is behind/i)).toBeDefined()
  })

  it('navigates results with arrows, opens with Enter and navigates to the link', async () => {
    vi.mocked(searchApi.search).mockResolvedValue(
      response([result(), result({ id: 'api:2', kind: 'api', kindLabel: 'API', title: 'Payments API', link: '/apis/2' })]),
    )
    renderBox()
    const input = await typeQuery('pay')
    await screen.findByText('Payments API')

    fireEvent.keyDown(input, { key: 'ArrowDown' })
    expect(screen.getAllByRole('option')[1].getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/apis/2'))
    await waitFor(() => expect(screen.queryByLabelText('Search query')).toBeNull())
  })

  it('closes on Escape', async () => {
    renderBox()
    const input = await typeQuery('x')
    fireEvent.keyDown(input, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByLabelText('Search query')).toBeNull())
  })

  it('marks the word after an emoji at the UTF-16 offsets the API returns', async () => {
    vi.mocked(searchApi.search).mockResolvedValue(
      response([result({ snippet: { text: '\u{1F600} payment gateway', matches: [[3, 10]] } })]),
    )
    renderBox()
    await typeQuery('paymnt')

    expect((await screen.findByText('payment')).tagName).toBe('MARK')
  })

  it('renders markup in titles and snippets as literal text', async () => {
    vi.mocked(searchApi.search).mockResolvedValue(
      response([
        result({
          title: '<img src=x onerror=alert(1)>',
          snippet: { text: '<script>alert(1)</script> hit', matches: [[0, 8]] },
        }),
      ]),
    )
    const { baseElement } = renderBox()
    await typeQuery('hit')

    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeDefined()
    expect(baseElement.querySelector('img')).toBeNull()
    expect(baseElement.querySelector('script')).toBeNull()
  })
})
