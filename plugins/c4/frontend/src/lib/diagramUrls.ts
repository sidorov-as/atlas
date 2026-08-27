// Diagram URL builders — moved out of `frontend/lib/entities` (diagram
// endpoints live under `/api/plugins/atlas.c4/...`).

export type DiagramView = 'context' | 'architecture' | 'container' | 'component'
export type DiagramFormat = 'svg' | 'png'
export type DiagramRenderingOptions = {
  layout: 'LAYOUT_TOP_DOWN' | 'LAYOUT_LEFT_RIGHT' | 'LAYOUT_LANDSCAPE'
  showTitle: boolean
  showLegend: boolean
  showSelectedLabel: boolean
  showPersonSprite: boolean
  showStereotypes: boolean
}

export type DiagramUrlOptions = { format?: DiagramFormat; download?: boolean; rendering?: DiagramRenderingOptions }

function addRenderingOptions(query: URLSearchParams, rendering?: DiagramRenderingOptions) {
  if (!rendering) return
  query.set('layout', rendering.layout)
  query.set('show_title', String(rendering.showTitle))
  query.set('show_legend', String(rendering.showLegend))
  query.set('show_selected_label', String(rendering.showSelectedLabel))
  query.set('show_person_sprite', String(rendering.showPersonSprite))
  query.set('show_stereotypes', String(rendering.showStereotypes))
}

/** Same-origin `<img src>` URL — the session cookie rides along automatically. */
export function diagramUrl(kind: string, id: string, view: DiagramView, options: DiagramUrlOptions = {}): string {
  const query = new URLSearchParams({ view })
  if (options.format && options.format !== 'svg') query.set('format', options.format)
  if (options.download) query.set('download', '1')
  addRenderingOptions(query, options.rendering)
  return `/api/plugins/atlas.c4/diagrams/${kind}/${id}/?${query}`
}

/** Same-origin URL for the catalog-wide diagram, which has no entity target. */
export function systemLandscapeUrl(options: DiagramUrlOptions = {}): string {
  const query = new URLSearchParams()
  if (options.format && options.format !== 'svg') query.set('format', options.format)
  if (options.download) query.set('download', '1')
  addRenderingOptions(query, options.rendering)
  const suffix = query.toString()
  return `/api/plugins/atlas.c4/diagrams/landscape/${suffix ? `?${suffix}` : ''}`
}
