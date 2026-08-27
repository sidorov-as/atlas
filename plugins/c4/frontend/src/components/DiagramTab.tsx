import { useCallback, useEffect, useRef, useState } from 'react'
import { Gear, MagnifierMinus, MagnifierPlus, SquareDashed } from '@gravity-ui/icons'
import { Button, Checkbox, Icon, Loader, Popup, SegmentedRadioGroup, Text, Tooltip } from '@gravity-ui/uikit'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'
import { diagramUrl, type DiagramView } from '../lib/diagramUrls'
import {
  type DiagramLayout,
  type DiagramRenderingPreferences,
  useDiagramPreferences,
} from '../lib/diagramPreferences'

const ZOOM_STEP = 0.15
const MIN_SCALE = 0.2
const MAX_SCALE = 3

export interface DiagramViewerProps {
  src: string
  alt: string
  downloadUrls?: { svg: string; png: string }
  preferences?: DiagramRenderingPreferences
  onPreferencesChange?: (preferences: DiagramRenderingPreferences) => void
  height?: number | string
}

function DiagramSettings({ preferences, onChange }: { preferences: DiagramRenderingPreferences; onChange: (preferences: DiagramRenderingPreferences) => void }) {
  const [open, setOpen] = useState(false)
  const [anchorElement, setAnchorElement] = useState<HTMLButtonElement | null>(null)
  const set = (next: Partial<DiagramRenderingPreferences>) => onChange({ ...preferences, ...next })

  return (
    <>
      <Tooltip content="Diagram settings" placement="top">
        <Button ref={setAnchorElement} view="raised" aria-label="Diagram settings" onClick={() => setOpen((value) => !value)}>
          <Icon data={Gear} />
        </Button>
      </Tooltip>
      <Popup anchorElement={anchorElement} open={open} placement="top-start" onOpenChange={setOpen}>
        <div style={{ width: 280, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Text variant="subheader-2">Diagram settings</Text>
          <div>
            <Text color="secondary" style={{ display: 'block', marginBottom: 6 }}>Layout</Text>
            <SegmentedRadioGroup
              name="diagram-layout"
              size="s"
              width="max"
              value={preferences.layout}
              onUpdate={(layout) => set({ layout: layout as DiagramLayout })}
              options={[
                { value: 'LAYOUT_TOP_DOWN', content: 'Top-down' },
                { value: 'LAYOUT_LEFT_RIGHT', content: 'Left-right' },
                { value: 'LAYOUT_LANDSCAPE', content: 'Landscape' },
              ]}
            />
          </div>
          <Checkbox checked={preferences.showTitle} onUpdate={(showTitle) => set({ showTitle })}>Show title</Checkbox>
          <Checkbox checked={preferences.showLegend} onUpdate={(showLegend) => set({ showLegend })}>Show legend</Checkbox>
          <Checkbox checked={preferences.showSelectedLabel} onUpdate={(showSelectedLabel) => set({ showSelectedLabel })}>Show selected label</Checkbox>
          <Checkbox checked={preferences.showPersonSprite} onUpdate={(showPersonSprite) => set({ showPersonSprite })}>Show person sprite</Checkbox>
          <Checkbox checked={preferences.showStereotypes} onUpdate={(showStereotypes) => set({ showStereotypes })}>Show stereotypes</Checkbox>
        </div>
      </Popup>
    </>
  )
}

/** A canvas-like image viewport with pan, zoom, fit, settings, and graceful image-load failures. */
export function DiagramViewer({ src, alt, downloadUrls, preferences, onPreferencesChange, height = 'min(70vh, 720px)' }: DiagramViewerProps) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [scale, setScale] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef<{ x: number; y: number; offsetX: number; offsetY: number } | null>(null)
  const lastViewportSize = useRef({ width: 0, height: 0 })

  const fitToViewport = useCallback(() => {
    const viewport = viewportRef.current
    const image = imageRef.current
    if (!viewport || !image || !image.naturalWidth || !image.naturalHeight || !viewport.clientWidth || !viewport.clientHeight) return
    setScale(Math.min(MAX_SCALE, Math.max(MIN_SCALE, Math.min(viewport.clientWidth / image.naturalWidth, viewport.clientHeight / image.naturalHeight))))
    setOffset({ x: 0, y: 0 })
  }, [])

  useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport || !window.ResizeObserver) return
    let frame = 0
    const observer = new window.ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      if (!width || !height || (width === lastViewportSize.current.width && height === lastViewportSize.current.height)) return
      lastViewportSize.current = { width, height }
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(fitToViewport)
    })
    observer.observe(viewport)
    return () => { cancelAnimationFrame(frame); observer.disconnect() }
  }, [fitToViewport])

  return (
    <div ref={viewportRef} style={{ position: 'relative', height, minHeight: 360, overflow: 'hidden', border: '1px solid var(--g-color-line-generic)', borderRadius: 8, background: 'var(--g-color-base-generic)' }}>
      {status === 'loading' && <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}><Loader size="m" /></div>}
      {status === 'error' ? <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', padding: 24, textAlign: 'center' }}><Text color="danger">The diagram could not be rendered. Please try again later.</Text></div> : (
        <img
          ref={imageRef}
          src={src}
          alt={alt}
          draggable={false}
          onLoad={() => { setStatus('ready'); fitToViewport() }}
          onError={() => setStatus('error')}
          style={{ position: 'absolute', top: '50%', left: '50%', maxWidth: 'none', maxHeight: 'none', opacity: status === 'ready' ? 1 : 0, transform: `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) scale(${scale})`, transformOrigin: 'center', cursor: isDragging ? 'grabbing' : 'grab', userSelect: 'none', touchAction: 'none' }}
          onPointerDown={(event) => { dragStart.current = { x: event.clientX, y: event.clientY, offsetX: offset.x, offsetY: offset.y }; setIsDragging(true); event.currentTarget.setPointerCapture(event.pointerId) }}
          onPointerMove={(event) => { if (!dragStart.current) return; setOffset({ x: dragStart.current.offsetX + event.clientX - dragStart.current.x, y: dragStart.current.offsetY + event.clientY - dragStart.current.y }) }}
          onPointerUp={() => { dragStart.current = null; setIsDragging(false) }}
          onPointerCancel={() => { dragStart.current = null; setIsDragging(false) }}
        />
      )}
      {status === 'ready' && <>
        <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', gap: 4 }}>
          <Tooltip content="Zoom in" placement="bottom"><Button view="raised" aria-label="Zoom in" onClick={() => setScale((value) => Math.min(MAX_SCALE, value + ZOOM_STEP))}><Icon data={MagnifierPlus} /></Button></Tooltip>
          <Tooltip content="Zoom out" placement="bottom"><Button view="raised" aria-label="Zoom out" onClick={() => setScale((value) => Math.max(MIN_SCALE, value - ZOOM_STEP))}><Icon data={MagnifierMinus} /></Button></Tooltip>
          <Tooltip content="Fit to viewport" placement="bottom"><Button view="raised" aria-label="Fit to viewport" onClick={fitToViewport}><Icon data={SquareDashed} /></Button></Tooltip>
          {downloadUrls && <Tooltip content="Download SVG" placement="bottom"><Button view="raised" aria-label="Download SVG" onClick={() => window.location.assign(downloadUrls.svg)}>SVG</Button></Tooltip>}
          {downloadUrls && <Tooltip content="Download PNG" placement="bottom"><Button view="raised" aria-label="Download PNG" onClick={() => window.location.assign(downloadUrls.png)}>PNG</Button></Tooltip>}
        </div>
        {preferences && onPreferencesChange && <div style={{ position: 'absolute', bottom: 12, left: 12 }}><DiagramSettings preferences={preferences} onChange={onPreferencesChange} /></div>}
      </>}
    </div>
  )
}

/** Fills the space below the tab strip down to the bottom of the viewport, the same as
 * `SystemMapPage`'s `SystemMapDiagram` — split out from `DiagramTab` so `useFillViewportHeight`'s
 * container ref exists from this component's very first render, matching that hook's documented
 * anti-pattern warning. `EntityDetailShell` keeps every tab's panel mounted (hidden via CSS)
 * rather than unmounting inactive ones, so this also relies on the hook re-measuring via
 * `ResizeObserver` once a hidden panel is shown again. */
function FillViewportDiagram({ kind, id, view, preferences, onPreferencesChange }: {
  kind: string
  id: string
  view: DiagramView
  preferences: DiagramRenderingPreferences
  onPreferencesChange: (preferences: DiagramRenderingPreferences) => void
}) {
  const { containerRef, height } = useFillViewportHeight()
  return (
    <div ref={containerRef}>
      <DiagramViewer
        src={diagramUrl(kind, id, view, { rendering: preferences })}
        alt={`${view} diagram`}
        preferences={preferences}
        onPreferencesChange={onPreferencesChange}
        downloadUrls={{
          svg: diagramUrl(kind, id, view, { download: true, rendering: preferences }),
          png: diagramUrl(kind, id, view, { format: 'png', download: true, rendering: preferences }),
        }}
        height={height}
      />
    </div>
  )
}

/** C4 diagram endpoint rendered through the shared interactive viewer. */
export function DiagramTab({ kind, id, view }: { kind: string; id: string; view: DiagramView }) {
  const [preferences, setPreferences] = useDiagramPreferences(view)
  return <FillViewportDiagram kind={kind} id={id} view={view} preferences={preferences} onPreferencesChange={setPreferences} />
}
