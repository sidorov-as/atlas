import type { Monaco } from '@monaco-editor/react'

// Monaco can't read `--g-color-*` custom properties directly, so these are
// literal colors resolved from Gravity UI's default light/dark palettes plus
// Atlas's brand overrides in `theme.css` — ported from
// `plugins/flows/frontend/src/lib/monacoFlowTheme.ts`,
// same colors, generalized beyond Flow's JSON-only usage.

export const CODE_EDITOR_THEME_LIGHT = 'atlas-code-editor-light'
export const CODE_EDITOR_THEME_DARK = 'atlas-code-editor-dark'

const BRAND = '#1c73e3'

export function defineCodeEditorThemes(monaco: Monaco) {
  monaco.editor.defineTheme(CODE_EDITOR_THEME_LIGHT, {
    base: 'vs',
    inherit: true,
    rules: [{ token: 'string.key.json', foreground: '1c73e3' }],
    colors: {
      'editor.foreground': '#262626',
      'editor.background': '#ffffff',
      'editor.lineHighlightBackground': '#f5f5f5',
      'editorLineNumber.foreground': '#b3b3b3',
      'editorLineNumber.activeForeground': '#262626',
      'editor.selectionBackground': `${BRAND}26`,
      'editor.inactiveSelectionBackground': `${BRAND}14`,
      'editorCursor.foreground': BRAND,
    },
  })

  monaco.editor.defineTheme(CODE_EDITOR_THEME_DARK, {
    base: 'vs-dark',
    inherit: true,
    rules: [{ token: 'string.key.json', foreground: '5b9eea' }],
    colors: {
      'editor.foreground': '#dedddd',
      'editor.background': '#221d22',
      'editor.lineHighlightBackground': '#2b252b',
      'editorLineNumber.foreground': '#605d60',
      'editorLineNumber.activeForeground': '#dedddd',
      'editor.selectionBackground': `${BRAND}55`,
      'editor.inactiveSelectionBackground': `${BRAND}29`,
      'editorCursor.foreground': BRAND,
    },
  })
}

/** Picks the Monaco theme matching the app's current Gravity UI theme class. */
export function activeCodeEditorTheme(): string {
  const isDark = document.body.classList.contains('g-root_theme_dark')
  return isDark ? CODE_EDITOR_THEME_DARK : CODE_EDITOR_THEME_LIGHT
}
