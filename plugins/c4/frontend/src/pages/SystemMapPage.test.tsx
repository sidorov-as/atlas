// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { systemsApi } from 'frontend/lib/entities'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { systemLandscapeUrl } from '../lib/diagramUrls'
import { SystemMapPage } from './SystemMapPage'

afterEach(() => cleanup())

vi.mock('frontend/lib/entities', async (importOriginal) => ({
  ...(await importOriginal<typeof import('frontend/lib/entities')>()),
  systemsApi: { list: vi.fn() },
}))

function renderSystemMapPage() {
  return render(
    <ThemeProvider theme="light">
      <SystemMapPage />
    </ThemeProvider>,
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
})
