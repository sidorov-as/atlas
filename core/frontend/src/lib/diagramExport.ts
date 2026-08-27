/** Triggers a browser download of a captured `data:` URL (from `html-to-image`'s `toSvg`/`toPng`) under `filename`. */
export function downloadDataUrl(dataUrl: string, filename: string): void {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  link.click()
}
