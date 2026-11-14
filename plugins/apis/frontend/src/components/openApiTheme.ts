import type { RedocRawOptions } from 'redoc'
import type { ResolvedTheme } from 'frontend/lib/ThemeContext'

type RedocTheme = NonNullable<RedocRawOptions['theme']>

// Redoc derives shades from these with a color library, so they must be literal colors rather than
// `var(--g-color-*)`. Values follow Gravity UI's dark palette plus Atlas's brand overrides (`theme.css`).
const DARK_REDOC_THEME: RedocTheme = {
  colors: {
    primary: { main: '#5b9eea' },
    text: { primary: '#dedddd', secondary: '#b9b6b9' },
    border: { dark: '#4a444a', light: '#3a343a' },
    responses: {
      success: { color: '#6dc27d', backgroundColor: 'rgba(109, 194, 125, 0.12)' },
      error: { color: '#ee8a8a', backgroundColor: 'rgba(238, 138, 138, 0.12)' },
      redirect: { color: '#e5c07b', backgroundColor: 'rgba(229, 192, 123, 0.12)' },
      info: { color: '#7fb4f0', backgroundColor: 'rgba(127, 180, 240, 0.12)' },
    },
  },
  sidebar: { backgroundColor: '#2b252b', textColor: '#dedddd' },
  rightPanel: { backgroundColor: '#191519', textColor: '#dedddd' },
  codeBlock: { backgroundColor: '#191519' },
  schema: { nestedBackground: '#2b252b', typeNameColor: '#b9b6b9', typeTitleColor: '#b9b6b9' },
  typography: {
    code: { color: '#f0a35e', backgroundColor: 'rgba(255, 255, 255, 0.08)' },
    links: { color: '#5b9eea', visited: '#5b9eea', hover: '#7fb4f0' },
  },
  fab: { backgroundColor: '#2b252b', color: '#dedddd' },
}

/** Redoc options for the active theme; light keeps Redoc's own defaults. */
export function redocOptions(theme: ResolvedTheme): RedocRawOptions {
  return theme === 'dark' ? { theme: DARK_REDOC_THEME } : {}
}
