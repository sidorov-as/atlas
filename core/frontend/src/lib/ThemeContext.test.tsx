// @vitest-environment jsdom
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { THEME_STORAGE_KEY, ThemeModeProvider, useTheme } from './ThemeContext'

type ChangeListener = (event: MediaQueryListEvent) => void

let systemDark = false
let listeners: ChangeListener[] = []

// jsdom's localStorage is unavailable under this config, so tests install a plain stub.
const storage = new Map<string, string>()
const storageStub = {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => void storage.set(key, value),
  clear: () => storage.clear(),
}

function installStorage(stub: Pick<Storage, 'getItem' | 'setItem' | 'clear'> = storageStub) {
  Object.defineProperty(window, 'localStorage', { configurable: true, value: stub })
}

function installMatchMedia() {
  listeners = []
  window.matchMedia = vi.fn().mockImplementation(() => ({
    get matches() {
      return systemDark
    },
    addEventListener: (_type: string, listener: ChangeListener) => listeners.push(listener),
    removeEventListener: (_type: string, listener: ChangeListener) => {
      listeners = listeners.filter((item) => item !== listener)
    },
  })) as unknown as typeof window.matchMedia
}

function setSystemDark(value: boolean) {
  systemDark = value
  act(() => listeners.forEach((listener) => listener({ matches: value } as MediaQueryListEvent)))
}

function Probe() {
  const { mode, resolved, setMode } = useTheme()
  return (
    <div>
      <span data-testid="state">{`${mode}/${resolved}`}</span>
      <button onClick={() => setMode('dark')}>dark</button>
    </div>
  )
}

function renderProbe() {
  render(
    <ThemeModeProvider>
      <Probe />
    </ThemeModeProvider>,
  )
  return () => screen.getByTestId('state').textContent
}

beforeEach(() => {
  systemDark = false
  document.documentElement.removeAttribute('style')
  installStorage()
  window.localStorage.clear()
  installMatchMedia()
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('ThemeModeProvider', () => {
  it('defaults to system and resolves it from the operating system', () => {
    systemDark = true
    expect(renderProbe()()).toBe('system/dark')
  })

  it('uses a stored mode over the operating system', () => {
    systemDark = true
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light')
    expect(renderProbe()()).toBe('light/light')
  })

  it('falls back to system for an unrecognized stored value', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'sepia')
    expect(renderProbe()()).toBe('system/light')
  })

  it('falls back to system and stays usable when storage throws', () => {
    const blocked = () => {
      throw new Error('blocked')
    }
    installStorage({ getItem: blocked, setItem: blocked, clear: blocked })
    const state = renderProbe()
    expect(state()).toBe('system/light')
    act(() => screen.getByText('dark').click())
    expect(state()).toBe('dark/dark')
  })

  it('follows operating system changes in system mode', () => {
    const state = renderProbe()
    expect(state()).toBe('system/light')
    setSystemDark(true)
    expect(state()).toBe('system/dark')
  })

  it('ignores operating system changes in an explicit mode', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light')
    const state = renderProbe()
    setSystemDark(true)
    expect(state()).toBe('light/light')
  })

  it('keeps the <html> background and color scheme in step with the resolved theme', () => {
    renderProbe()
    expect(document.documentElement.style.backgroundColor).toBe('rgb(255, 255, 255)')
    act(() => screen.getByText('dark').click())
    expect(document.documentElement.style.backgroundColor).toBe('rgb(34, 29, 34)')
    expect(document.documentElement.style.colorScheme).toBe('dark')
    setSystemDark(false)
    expect(document.documentElement.style.backgroundColor).toBe('rgb(34, 29, 34)')
  })

  it('persists the chosen mode', () => {
    renderProbe()
    act(() => screen.getByText('dark').click())
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  })

  it('reads as light system mode outside a provider', () => {
    render(<Probe />)
    expect(screen.getByTestId('state').textContent).toBe('system/light')
  })
})

describe('no-flash bootstrap script', () => {
  const html = readFileSync(join(import.meta.dirname, '..', '..', 'index.html'), 'utf8')

  it('reads the same storage key as the context', () => {
    expect(html).toContain(`getItem('${THEME_STORAGE_KEY}')`)
  })

  it.each([
    ['dark', false, '#221d22'],
    ['light', true, '#ffffff'],
    [null, true, '#221d22'],
    ['sepia', false, '#ffffff'],
  ])('paints stored %s (system dark: %s) as %s', (stored, prefersDark, background) => {
    const script = /<script>([\s\S]*?)<\/script>/.exec(html)![1]
    if (stored) window.localStorage.setItem(THEME_STORAGE_KEY, stored)
    systemDark = prefersDark
    document.documentElement.removeAttribute('style')
    new Function(script)()
    expect(document.documentElement.style.backgroundColor).toBe(
      background === '#221d22' ? 'rgb(34, 29, 34)' : 'rgb(255, 255, 255)',
    )
  })
})
