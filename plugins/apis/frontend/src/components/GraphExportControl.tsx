// Image export of the full-screen dependency graphs: an "Export" button with a
// popup (SVG or PNG, transparent background, grid), the same options and
// defaults as the Flow and ER diagram exports. Kept private to this plugin
// rather than shared with those (minimal sharing, as they do between themselves).
import { useState } from 'react'
import { toPng, toSvg } from 'html-to-image'
import { Button, Checkbox, Icon, Popup, SegmentedRadioGroup, Tooltip } from '@gravity-ui/uikit'
import { ArrowUpRightFromSquare } from '@gravity-ui/icons'
import { downloadDataUrl } from 'frontend/lib/diagramExport'

export interface GraphExportOptions {
  format: 'svg' | 'png'
  transparent: boolean
  showGrid: boolean
}

// `html-to-image` inlines each HTML element's computed style but deep-clones
// anything inside an `<svg>` as is, and React Flow's edge strokes come only from
// class rules and custom properties that do not resolve in the clone. Put each
// edge's and marker's computed stroke on its own `style` for the capture, then
// restore (the same approach as the Flow and ER exports).
function inlineEdgeStyles(root: HTMLElement): () => void {
  const strokeElements = root.querySelectorAll<SVGElement>(
    '.react-flow__edge-path, .react-flow__marker path, .react-flow__marker polyline',
  )
  const restores = Array.from(strokeElements).map((element) => {
    const previousStyle = element.getAttribute('style')
    const computed = window.getComputedStyle(element)
    element.style.stroke = computed.stroke
    element.style.strokeWidth = computed.strokeWidth
    element.style.fill = computed.fill
    return () => {
      if (previousStyle === null) element.removeAttribute('style')
      else element.setAttribute('style', previousStyle)
    }
  })
  return () => restores.forEach((restore) => restore())
}

// The zoom controls and the attribution are canvas chrome, not part of the graph.
const CANVAS_CHROME = '.react-flow__controls, .react-flow__panel'

/** Captures `element` (the canvas as it is currently framed) and downloads it as `<filename>.<format>`. */
export async function exportGraphImage(element: HTMLElement, { format, transparent, showGrid }: GraphExportOptions, filename: string): Promise<void> {
  const restoreEdgeStyles = inlineEdgeStyles(element)
  const gridElement = element.querySelector<HTMLElement>('.react-flow__background')
  if (gridElement && !showGrid) gridElement.style.display = 'none'
  try {
    const options = {
      backgroundColor: transparent ? undefined : '#ffffff',
      filter: (node: Node) => !(node instanceof Element && node.matches(CANVAS_CHROME)),
    }
    const dataUrl = format === 'svg' ? await toSvg(element, options) : await toPng(element, options)
    downloadDataUrl(dataUrl, `${filename}.${format}`)
  } finally {
    if (gridElement && !showGrid) gridElement.style.display = ''
    restoreEdgeStyles()
  }
}

/** Export trigger button + options popup; the options reset to their defaults each time it opens and are never persisted. */
export function GraphExportControl({ exporting, onExport }: { exporting: boolean, onExport: (options: GraphExportOptions) => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [anchorElement, setAnchorElement] = useState<HTMLButtonElement | null>(null)
  const [format, setFormat] = useState<'svg' | 'png'>('svg')
  const [transparent, setTransparent] = useState(true)
  const [showGrid, setShowGrid] = useState(true)

  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen) {
      setFormat('svg')
      setTransparent(true)
      setShowGrid(true)
    }
    setOpen(nextOpen)
  }

  async function handleExportClick() {
    await onExport({ format, transparent, showGrid })
    setOpen(false)
  }

  return (
    <>
      <Tooltip content="Export" placement="bottom">
        <Button ref={setAnchorElement} view="raised" aria-label="Export" onClick={() => handleOpenChange(!open)}>
          <Icon data={ArrowUpRightFromSquare} />
        </Button>
      </Tooltip>
      <Popup anchorElement={anchorElement} open={open} placement="bottom-end" onOpenChange={handleOpenChange}>
        <div style={{ width: 220, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <SegmentedRadioGroup value={format} onUpdate={(value) => setFormat(value as 'svg' | 'png')} width="max">
            <SegmentedRadioGroup.Option value="svg">SVG</SegmentedRadioGroup.Option>
            <SegmentedRadioGroup.Option value="png">PNG</SegmentedRadioGroup.Option>
          </SegmentedRadioGroup>
          <Checkbox checked={transparent} onUpdate={setTransparent}>Transparent background</Checkbox>
          <Checkbox checked={showGrid} onUpdate={setShowGrid}>Grid</Checkbox>
          <Button view="action" width="max" loading={exporting} onClick={() => void handleExportClick()}>Export</Button>
        </div>
      </Popup>
    </>
  )
}
