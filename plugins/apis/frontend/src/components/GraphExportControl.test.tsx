// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { toPng, toSvg } from 'html-to-image'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadDataUrl } from 'frontend/lib/diagramExport'
import { exportGraphImage, GraphExportControl } from './GraphExportControl'

vi.mock('html-to-image', () => ({ toSvg: vi.fn(), toPng: vi.fn() }))
vi.mock('frontend/lib/diagramExport', () => ({ downloadDataUrl: vi.fn() }))

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

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function makeCanvas() {
  const root = document.createElement('div')
  root.innerHTML = `
    <div class="react-flow__background"></div>
    <div class="react-flow__controls"></div>
    <div class="react-flow__panel react-flow__attribution"></div>
    <svg><path class="react-flow__edge-path" d="M0 0"></path></svg>`
  document.body.append(root)
  return root
}

describe('exportGraphImage', () => {
  it('exports a transparent SVG named after the graph by default and hides nothing', async () => {
    vi.mocked(toSvg).mockResolvedValue('data:svg')
    const root = makeCanvas()

    await exportGraphImage(root, { format: 'svg', transparent: true, showGrid: true }, 'operation-participants')

    expect(toSvg).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toSvg).mock.calls[0][1]).toMatchObject({ backgroundColor: undefined })
    expect(downloadDataUrl).toHaveBeenCalledWith('data:svg', 'operation-participants.svg')
  })

  it('exports a PNG with a white background when transparency is off', async () => {
    vi.mocked(toPng).mockResolvedValue('data:png')

    await exportGraphImage(makeCanvas(), { format: 'png', transparent: false, showGrid: true }, 'endpoint-consumers')

    expect(vi.mocked(toPng).mock.calls[0][1]).toMatchObject({ backgroundColor: '#ffffff' })
    expect(downloadDataUrl).toHaveBeenCalledWith('data:png', 'endpoint-consumers.png')
  })

  it('hides the grid only while capturing, and restores it and the edge styles afterwards', async () => {
    const root = makeCanvas()
    const grid = root.querySelector<HTMLElement>('.react-flow__background')!
    const edge = root.querySelector<SVGElement>('.react-flow__edge-path')!
    let gridDisplayDuringCapture = ''
    let edgeStrokeDuringCapture = ''
    vi.mocked(toSvg).mockImplementation(async () => {
      gridDisplayDuringCapture = grid.style.display
      edgeStrokeDuringCapture = edge.style.stroke
      return 'data:svg'
    })

    await exportGraphImage(root, { format: 'svg', transparent: true, showGrid: false }, 'graph')

    expect(gridDisplayDuringCapture).toBe('none')
    // The computed stroke was written onto the element for the capture (jsdom resolves it to a value, possibly empty).
    expect(edge.hasAttribute('style')).toBe(false)
    expect(grid.style.display).toBe('')
    expect(edgeStrokeDuringCapture).not.toBeUndefined()
  })

  it('restores the grid when the capture fails', async () => {
    const root = makeCanvas()
    vi.mocked(toSvg).mockRejectedValue(new Error('boom'))

    await expect(exportGraphImage(root, { format: 'svg', transparent: true, showGrid: false }, 'graph')).rejects.toThrow('boom')

    expect(root.querySelector<HTMLElement>('.react-flow__background')!.style.display).toBe('')
    expect(downloadDataUrl).not.toHaveBeenCalled()
  })

  it('leaves the zoom controls and the attribution out of the image', async () => {
    vi.mocked(toSvg).mockResolvedValue('data:svg')
    const root = makeCanvas()

    await exportGraphImage(root, { format: 'svg', transparent: true, showGrid: true }, 'graph')

    const { filter } = vi.mocked(toSvg).mock.calls[0][1] as { filter: (node: Node) => boolean }
    expect(filter(root.querySelector('.react-flow__controls')!)).toBe(false)
    expect(filter(root.querySelector('.react-flow__attribution')!)).toBe(false)
    expect(filter(root.querySelector('.react-flow__background')!)).toBe(true)
    expect(filter(document.createTextNode('text'))).toBe(true)
  })
})

// The trigger and the popup's action are both named "Export"; the popup renders after the trigger.
const popupExportButton = () => screen.getAllByRole('button', { name: 'Export' }).at(-1)!

describe('GraphExportControl', () => {
  function renderControl(onExport = vi.fn().mockResolvedValue(undefined)) {
    render(<ThemeProvider theme="light"><GraphExportControl exporting={false} onExport={onExport} /></ThemeProvider>)
    return onExport
  }

  it('exports with the defaults: SVG, transparent background, grid', async () => {
    const onExport = renderControl()

    fireEvent.click(screen.getByLabelText('Export'))
    fireEvent.click(await screen.findByText('PNG').then(() => popupExportButton()))

    await waitFor(() => expect(onExport).toHaveBeenCalledWith({ format: 'svg', transparent: true, showGrid: true }))
  })

  it('exports the chosen options and resets them to the defaults when reopened', async () => {
    const onExport = renderControl()

    fireEvent.click(screen.getByLabelText('Export'))
    fireEvent.click(await screen.findByText('PNG'))
    fireEvent.click(screen.getByLabelText('Transparent background'))
    fireEvent.click(screen.getByLabelText('Grid'))
    fireEvent.click(popupExportButton())
    await waitFor(() => expect(onExport).toHaveBeenCalledWith({ format: 'png', transparent: false, showGrid: false }))

    // Closed after exporting; opening again starts from the defaults.
    await waitFor(() => expect(screen.queryByText('PNG')).toBeNull())
    fireEvent.click(screen.getByLabelText('Export'))
    fireEvent.click(await screen.findByText('PNG').then(() => popupExportButton()))
    await waitFor(() => expect(onExport).toHaveBeenLastCalledWith({ format: 'svg', transparent: true, showGrid: true }))
  })
})
