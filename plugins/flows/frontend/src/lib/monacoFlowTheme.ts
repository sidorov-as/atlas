import type { Monaco } from '@monaco-editor/react'

// Monaco can't read `--g-color-*` custom properties directly, so these are
// literal colors resolved from Gravity UI's default light/dark palettes plus
// Atlas's brand overrides in `theme.css`.

export const FLOW_THEME_LIGHT = 'atlas-flow-light'
export const FLOW_THEME_DARK = 'atlas-flow-dark'

const BRAND = '#1c73e3'

export function defineFlowThemes(monaco: Monaco) {
  monaco.editor.defineTheme(FLOW_THEME_LIGHT, {
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

  monaco.editor.defineTheme(FLOW_THEME_DARK, {
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
export function activeFlowTheme(): string {
  const isDark = document.body.classList.contains('g-root_theme_dark')
  return isDark ? FLOW_THEME_DARK : FLOW_THEME_LIGHT
}

export interface StepRange {
  start: number
  end: number
}

/** Scans `text` for `{...}` objects that sit directly at brace-depth 0 (the array's own elements), skipping string contents so braces inside `summary` text don't confuse the count. */
function topLevelObjectRanges(text: string): StepRange[] {
  const ranges: StepRange[] = []
  let depth = 0
  let start = -1
  let inString = false
  let escaped = false
  for (let i = 0; i < text.length; i++) {
    const char = text[i]
    if (inString) {
      if (escaped) escaped = false
      else if (char === '\\') escaped = true
      else if (char === '"') inString = false
      continue
    }
    if (char === '"') {
      inString = true
    } else if (char === '{') {
      if (depth === 0) start = i
      depth += 1
    } else if (char === '}') {
      depth -= 1
      if (depth === 0 && start !== -1) {
        ranges.push({ start, end: i + 1 })
        start = -1
      }
    }
  }
  return ranges
}

/** Reads the `"id"` value declared directly on the object spanning `range` — not one nested inside `next_step`/`next_steps`, which reuse the same key name to reference a target step. */
function ownId(text: string, range: StepRange): string | null {
  let depth = 0
  let inString = false
  let escaped = false
  for (let i = range.start; i < range.end; i++) {
    const char = text[i]
    if (inString) {
      if (escaped) escaped = false
      else if (char === '\\') escaped = true
      else if (char === '"') inString = false
      continue
    }
    if (char === '"') {
      if (depth === 1) {
        const match = /^"id"\s*:\s*"((?:[^"\\]|\\.)*)"/.exec(text.slice(i))
        if (match) return match[1]
      }
      inString = true
    } else if (char === '{') {
      depth += 1
    } else if (char === '}') {
      depth -= 1
    }
  }
  return null
}

/**
 * Text-scans `text` (the `steps` JSON array) for the top-level step object
 * whose own `id` equals `stepId`, returning its enclosing `{...}` block as
 * character offsets (analogous to the reference playground's
 * `findBlockPositionsMonaco`, but offset-based so it doesn't depend on a live
 * Monaco model, and depth-aware so it isn't fooled by `next_step`/`next_steps`
 * transitions that reference a step id under the same `"id"` key).
 */
export function findStepRange(text: string, stepId: string): StepRange | null {
  for (const range of topLevelObjectRanges(text)) {
    if (ownId(text, range) === stepId) return range
  }
  return null
}
