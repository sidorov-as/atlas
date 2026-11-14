// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { THEME_STORAGE_KEY, ThemeModeProvider, useTheme } from '../lib/ThemeContext'
import { ThemeSwitcher } from './ThemeSwitcher'

// The navigation package ships CSS imports that Vitest's node loader cannot resolve.
vi.mock('@gravity-ui/navigation', () => ({
  FooterItem: ({ title, onItemClick }: { title: string; onItemClick: () => void }) => (
    <button title={title} onClick={onItemClick} />
  ),
}))

function Mode() {
  return <span data-testid="mode">{useTheme().mode}</span>
}

function renderSwitcher(compact: boolean) {
  render(
    <ThemeModeProvider>
      <ThemeSwitcher compact={compact} />
      <Mode />
    </ThemeModeProvider>,
  )
}

const storage = new Map<string, string>()

beforeEach(() => {
  storage.clear()
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
    },
  })
  window.matchMedia = vi.fn().mockReturnValue({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }) as unknown as typeof window.matchMedia
})

afterEach(cleanup)

it('shows all three modes when expanded and applies a selection', () => {
  renderSwitcher(false)
  const system = screen.getByRole('radio', { name: 'System' }) as HTMLInputElement
  expect(system.checked).toBe(true)
  expect(screen.getByRole('radio', { name: 'Light' })).toBeTruthy()

  fireEvent.click(screen.getByRole('radio', { name: 'Dark' }))

  expect(screen.getByTestId('mode').textContent).toBe('dark')
  expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
})

it('cycles system, light, dark from a single control when compact', () => {
  renderSwitcher(true)
  const modes: string[] = []
  for (let step = 0; step < 4; step += 1) {
    modes.push(screen.getByTestId('mode').textContent ?? '')
    fireEvent.click(screen.getByTitle(/^Theme: /))
  }
  expect(modes).toEqual(['system', 'light', 'dark', 'system'])
})
