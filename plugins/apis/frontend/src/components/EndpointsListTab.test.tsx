// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointsListTab } from './EndpointsListTab'
import { endpointsApi } from '../lib/entities'
import { makeEndpoint } from '../testFixtures'

const paginationControl = () => document.querySelector('[data-qa="pagination-page-sizer"]')
const goToPage2 = () => fireEvent.click(document.querySelector('[data-qa="pagination-page-2"]')!)

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

vi.mock('../lib/entities', () => ({
  endpointsApi: { list: vi.fn() },
}))

function makeEndpoints(count: number) {
  return Array.from({ length: count }, (_, index) =>
    makeEndpoint({ id: `endpoint-${index}`, path: `/v1/item-${String(index).padStart(2, '0')}` }),
  )
}

function renderTab() {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EndpointsListTab apiId="api-1" />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EndpointsListTab pagination', () => {
  it('shows the first 15 endpoints and the pagination control for a longer list', async () => {
    vi.mocked(endpointsApi.list).mockResolvedValue(makeEndpoints(20))

    renderTab()

    await waitFor(() => expect(screen.getByText('/v1/item-00')).toBeDefined())
    expect(screen.getByText('/v1/item-14')).toBeDefined()
    expect(screen.queryByText('/v1/item-15')).toBeNull()
    expect(paginationControl()).not.toBeNull()
  })

  it('shows the rest of the list on page 2', async () => {
    vi.mocked(endpointsApi.list).mockResolvedValue(makeEndpoints(20))

    renderTab()
    await waitFor(() => expect(screen.getByText('/v1/item-00')).toBeDefined())
    goToPage2()

    await waitFor(() => expect(screen.getByText('/v1/item-15')).toBeDefined())
    expect(screen.queryByText('/v1/item-00')).toBeNull()
  })

  it('returns to page 1 when a filter changes', async () => {
    vi.mocked(endpointsApi.list).mockResolvedValue(makeEndpoints(20))

    renderTab()
    await waitFor(() => expect(screen.getByText('/v1/item-00')).toBeDefined())
    goToPage2()
    await waitFor(() => expect(screen.getByText('/v1/item-15')).toBeDefined())

    fireEvent.change(screen.getByPlaceholderText('Search path, summary, operation ID…'), { target: { value: 'item' } })

    await waitFor(() => expect(screen.getByText('/v1/item-00')).toBeDefined())
  })

  it('hides the pagination control for an empty list', async () => {
    vi.mocked(endpointsApi.list).mockResolvedValue([])

    renderTab()

    await waitFor(() => expect(screen.getByText('No endpoints')).toBeDefined())
    expect(paginationControl()).toBeNull()
  })
})
