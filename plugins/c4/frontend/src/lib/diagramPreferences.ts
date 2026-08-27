import { useState } from 'react'

export type DiagramPreferenceView = 'context' | 'architecture' | 'container' | 'component' | 'landscape'
export type DiagramLayout = 'LAYOUT_TOP_DOWN' | 'LAYOUT_LEFT_RIGHT' | 'LAYOUT_LANDSCAPE'

export interface DiagramRenderingPreferences {
  layout: DiagramLayout
  showTitle: boolean
  showLegend: boolean
  showSelectedLabel: boolean
  showPersonSprite: boolean
  showStereotypes: boolean
}

const STORAGE_KEY = 'atlas.c4-diagram-preferences.v1'

export const DEFAULT_DIAGRAM_PREFERENCES: DiagramRenderingPreferences = {
  layout: 'LAYOUT_TOP_DOWN',
  showTitle: true,
  showLegend: true,
  showSelectedLabel: true,
  showPersonSprite: true,
  showStereotypes: true,
}

function isPreferences(value: unknown): value is DiagramRenderingPreferences {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return ['LAYOUT_TOP_DOWN', 'LAYOUT_LEFT_RIGHT', 'LAYOUT_LANDSCAPE'].includes(candidate.layout as string)
    && ['showTitle', 'showLegend', 'showSelectedLabel', 'showPersonSprite', 'showStereotypes'].every((key) => typeof candidate[key] === 'boolean')
}

export function loadDiagramPreferences(view: DiagramPreferenceView): DiagramRenderingPreferences {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (!stored) return DEFAULT_DIAGRAM_PREFERENCES
    const values = JSON.parse(stored) as Partial<Record<DiagramPreferenceView, unknown>>
    return isPreferences(values[view]) ? values[view] : DEFAULT_DIAGRAM_PREFERENCES
  } catch {
    return DEFAULT_DIAGRAM_PREFERENCES
  }
}

export function saveDiagramPreferences(view: DiagramPreferenceView, preferences: DiagramRenderingPreferences) {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    const values = stored ? JSON.parse(stored) : {}
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...values, [view]: preferences }))
  } catch {
    // Preferences enhance the viewer; unavailable storage must never block rendering.
  }
}

export function useDiagramPreferences(view: DiagramPreferenceView) {
  const [preferences, setPreferences] = useState(() => loadDiagramPreferences(view))

  function updatePreferences(next: DiagramRenderingPreferences) {
    setPreferences(next)
    saveDiagramPreferences(view, next)
  }

  return [preferences, updatePreferences] as const
}
