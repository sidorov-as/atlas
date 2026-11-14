/** Triggers a browser download of a captured `data:` URL (from `html-to-image`'s `toSvg`/`toPng`) under `filename`. */
export function downloadDataUrl(dataUrl: string, filename: string): void {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  link.click()
}

const FALLBACK_EXPORT_BACKGROUND = '#ffffff'

/**
 * The fill for a non-transparent image export: the active theme's page background, read from the
 * live `--g-color-base-background` token at export time so it follows the theme (and any brand
 * override) without a lookup table. `undefined` for a transparent export.
 */
export function exportBackgroundColor(element: Element, transparent: boolean): string | undefined {
  if (transparent) return undefined
  const value = window.getComputedStyle(element).getPropertyValue('--g-color-base-background').trim()
  return value || FALLBACK_EXPORT_BACKGROUND
}
