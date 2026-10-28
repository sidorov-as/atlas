// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { systemsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { systemLandscapeUrl } from '../lib/diagramUrls'
import { SystemMapPage } from './SystemMapPage'

afterEach(() => cleanup())

// jsdom has no matchMedia or ResizeObserver; Gravity UI's table menus need them.
window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false, media: query, onchange: null, addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)
globalThis.ResizeObserver = globalThis.ResizeObserver || (class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver)

vi.mock('frontend/lib/SessionContext', () => ({ useSession: vi.fn() }))

vi.mock('frontend/lib/entities', async (importOriginal) => ({
  ...(await importOriginal<typeof import('frontend/lib/entities')>()),
  systemsApi: { list: vi.fn() },
}))

function renderSystemMapPage(url = '/system-map') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ThemeProvider theme="light">
        <SystemMapPage />
      </ThemeProvider>
    </MemoryRouter>,
  )
}

describe('SystemMapPage', () => {
  it('renders the shared landscape viewer with loading, error, and download URLs', async () => {
    vi.mocked(systemsApi.list).mockResolvedValue({
      count: 3, numPages: 1, perPage: 1, page: { number: 1, objectList: [] },
    })

    renderSystemMapPage()

    const image = await screen.findByAltText('System Landscape diagram')
    expect(image.getAttribute('src')).toContain(
      '/api/plugins/atlas.c4/diagrams/landscape/?layout=LAYOUT_TOP_DOWN',
    )
    fireEvent.load(image)
    expect(screen.getByRole('button', { name: 'Download SVG' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Download PNG' })).toBeDefined()
    fireEvent.error(image)
    expect(screen.getByText(/could not be rendered/i)).toBeDefined()
    expect(systemLandscapeUrl({ download: true })).toBe(
      '/api/plugins/atlas.c4/diagrams/landscape/?download=1',
    )
    expect(systemLandscapeUrl({ format: 'png', download: true })).toBe(
      '/api/plugins/atlas.c4/diagrams/landscape/?format=png&download=1',
    )
  })

  it('shows an empty state instead of the diagram when the catalog has zero Systems', async () => {
    vi.mocked(systemsApi.list).mockResolvedValue({
      count: 0, numPages: 1, perPage: 1, page: { number: 1, objectList: [] },
    })

    renderSystemMapPage()

    await waitFor(() =>
      expect(screen.getByText('System Map appears once your catalog has systems.')).toBeDefined(),
    )
    expect(screen.queryByAltText('System Landscape diagram')).toBeNull()
  })

  it('has Landscape and Views tabs, and shows the Views list on the views tab', async () => {
    vi.mocked(systemsApi.list).mockResolvedValue({
      count: 3, numPages: 1, perPage: 1, page: { number: 1, objectList: [] },
    })
    vi.mocked(useSession).mockReturnValue({ session: { isReadOnly: false } } as never)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ count: 0, numPages: 1, perPage: 15, page: { number: 1, objectList: [] } }), { status: 200 })))

    renderSystemMapPage('/system-map?tab=views')

    expect(screen.getByRole('tab', { name: 'Landscape' })).toBeDefined()
    expect(screen.getByRole('tab', { name: 'Views' })).toBeDefined()
    expect(await screen.findByRole('button', { name: 'Create view' })).toBeDefined()
    expect(screen.queryByAltText('System Landscape diagram')).toBeNull()
    vi.unstubAllGlobals()
  })
})
