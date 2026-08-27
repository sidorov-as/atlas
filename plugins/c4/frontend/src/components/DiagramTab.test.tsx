// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DiagramTab, DiagramViewer } from './DiagramTab'

class ResizeObserverStub {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

globalThis.ResizeObserver = ResizeObserverStub

const storage = new Map<string, string>()

beforeEach(() => {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      clear: () => storage.clear(),
    },
  })
})

afterEach(() => {
  cleanup()
  window.localStorage.clear()
})

describe('DiagramViewer', () => {
  it('shows viewport controls and SVG/PNG download actions after loading', () => {
    render(<ThemeProvider theme="light"><DiagramTab kind="system" id={42} view="context" /></ThemeProvider>)
    fireEvent.load(screen.getByAltText('context diagram'))
    expect(screen.getByRole('button', { name: 'Zoom in' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Zoom out' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Fit to viewport' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Download SVG' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Download PNG' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Diagram settings' })).toBeDefined()
  })

  it('persists settings and applies them to rendered and downloaded URLs', () => {
    render(<ThemeProvider theme="light"><DiagramTab kind="component" id={42} view="component" /></ThemeProvider>)
    const image = screen.getByAltText('component diagram') as HTMLImageElement
    fireEvent.load(image)
    fireEvent.click(screen.getByRole('button', { name: 'Diagram settings' }))
    fireEvent.click(screen.getByRole('radio', { name: 'Left-right' }))

    expect(image.src).toContain('layout=LAYOUT_LEFT_RIGHT')
    expect(image.src).toContain('show_legend=true')
    expect(window.localStorage.getItem('atlas.c4-diagram-preferences.v1')).toContain('LAYOUT_LEFT_RIGHT')
  })

  it('falls back to defaults when saved preferences are invalid', () => {
    window.localStorage.setItem('atlas.c4-diagram-preferences.v1', JSON.stringify({ context: { layout: 'diagonal' } }))
    render(<ThemeProvider theme="light"><DiagramTab kind="system" id={42} view="context" /></ThemeProvider>)

    const image = screen.getByAltText('context diagram') as HTMLImageElement
    expect(image.src).toContain('layout=LAYOUT_TOP_DOWN')
    expect(image.src).toContain('show_legend=true')
  })

  it('replaces a failed image with a rendering error state', () => {
    render(<ThemeProvider theme="light"><DiagramViewer src="/broken.svg" alt="broken diagram" /></ThemeProvider>)
    fireEvent.error(screen.getByAltText('broken diagram'))
    expect(screen.getByText(/could not be rendered/i)).toBeDefined()
    expect(screen.queryByAltText('broken diagram')).toBeNull()
  })
})
