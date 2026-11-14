// The user's theme mode (light / dark / system) and the theme it resolves to.
//
// The mode lives only in this browser's localStorage. `index.html` carries a tiny
// inline script that reads the same key before React mounts to avoid a flash of the
// wrong theme; `ThemeContext.test.tsx` pins the two together.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'atlas.theme.v1'

// Page background per resolved theme, matching Gravity's `--g-color-base-background`. Painted on <html>
// so overscroll and any area below a short <body> never show the other theme; `index.html` repeats
// these values for the pre-React paint.
export const THEME_BACKGROUND: Record<ResolvedTheme, string> = { light: '#ffffff', dark: '#221d22' }

const DARK_QUERY = '(prefers-color-scheme: dark)'

interface ThemeContextValue {
  mode: ThemeMode
  resolved: ResolvedTheme
  setMode: (mode: ThemeMode) => void
}

// Outside a provider (a component rendered on its own, e.g. in a plugin's tests) the app is simply light.
const ThemeContext = createContext<ThemeContextValue>({ mode: 'system', resolved: 'light', setMode: () => {} })

function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

function readStoredMode(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return isThemeMode(stored) ? stored : 'system'
  } catch {
    return 'system'
  }
}

function writeStoredMode(mode: ThemeMode) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode)
  } catch {
    // Storage can be unavailable (private window, blocked site data); the choice then lasts for this page load only.
  }
}

function systemPrefersDark(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(DARK_QUERY).matches
}

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode)
  const [systemDark, setSystemDark] = useState<boolean>(systemPrefersDark)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined
    const query = window.matchMedia(DARK_QUERY)
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    setSystemDark(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const resolved: ResolvedTheme = mode === 'system' ? (systemDark ? 'dark' : 'light') : mode

  // Keep <html> in step with the theme; the bootstrap script in index.html only paints it once, on load.
  useEffect(() => {
    const root = document.documentElement
    root.style.backgroundColor = THEME_BACKGROUND[resolved]
    root.style.colorScheme = resolved
  }, [resolved])

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next)
    writeStoredMode(next)
  }, [])

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, resolved, setMode }),
    [mode, resolved, setMode],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext)
}
