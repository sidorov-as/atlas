import { useEffect, useRef, useState } from 'react'
import { Background, getNodesBounds, ReactFlow, ReactFlowProvider, useReactFlow, useStore, type Edge } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { toPng, toSvg } from 'html-to-image'
import { Button, Checkbox, Icon, Popup, SegmentedRadioGroup, Text, Tooltip } from '@gravity-ui/uikit'
import { ArrowUpRightFromSquare, MagnifierMinus, MagnifierPlus, SquareDashed } from '@gravity-ui/icons'
import { downloadDataUrl } from 'frontend/lib/diagramExport'

import { FLOW_EDGE_TYPES } from './FlowEdges'
import { FLOW_NODE_TYPES } from './FlowNodes'
import {
  buildFlowNodesAndEdges,
  computeFlowAutolayout,
  mergeStepPositions,
  type FlowLayoutDirection,
  type FlowLayoutEngine,
  type FlowNode,
  type FlowPositions,
  type FlowStep,
  type FlowStepRefStatus,
} from '../lib/flowLayout'
import { useDebouncedValue } from 'frontend/lib/useDebouncedValue'

/** Floating zoom/fit toolbar, driven by React Flow's own camera. Shared with the editable canvas (`FlowCanvasEditor.tsx`). */
export function FlowGraphToolbar() {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  return (
    <div className="flow-graph__zoom">
      <Tooltip content="Zoom in" placement="right">
        <Button view="raised" aria-label="Zoom in" onClick={() => void zoomIn()}>
          <Icon data={MagnifierPlus} />
        </Button>
      </Tooltip>
      <Tooltip content="Fit to viewport" placement="right">
        <Button view="raised" aria-label="Fit to viewport" onClick={() => void fitView({ duration: 200, padding: 0.2 })}>
          <Icon data={SquareDashed} />
        </Button>
      </Tooltip>
      <Tooltip content="Zoom out" placement="right">
        <Button view="raised" aria-label="Zoom out" onClick={() => void zoomOut()}>
          <Icon data={MagnifierMinus} />
        </Button>
      </Tooltip>
    </div>
  )
}

// `html-to-image` clones the export target's DOM tree and inlines each
// element's computed style, except for anything nested inside an `<svg>`,
// which it deep-clones natively via `svg.cloneNode(true)` and never walks
// individually. React Flow's edges are exactly that shape, and their stroke
// (paths/markers) comes only from `@xyflow/react/dist/style.css` class rules
// — via CSS custom properties that don't resolve once cloned outside the live
// document — never an inline style. Resolve each element's computed stroke
// onto its own `style` attribute right before capture, and revert after
// (matches `ErDiagramView.tsx`'s `inlineEdgeStrokeStyles`).
//
// The transition label needs no such workaround: `FlowTransitionEdge`
// renders it as an HTML
// `<div>` via `EdgeLabelRenderer`, which portals it outside the `<svg>`
// entirely, so `html-to-image` walks and inlines its computed style (colors,
// border, background) the normal way — confirmed by inspecting an actual
// export: the label's resolved styles are already present as
// literal values, not `var(--g-color-...)` references. `.react-flow__edge-
// textbg`/`.react-flow__edge-text` — xyflow's *built-in* smoothstep-label DOM
// classes — never matched anything here even before this rewrite, since this
// component has never used the built-in `EdgeText` label.
function inlineEdgeExportStyles(root: HTMLElement): () => void {
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

interface DiagramExportOptions {
  format: 'svg' | 'png'
  transparent: boolean
  showGrid: boolean
}

/** Export trigger button + options popup (format/transparent/grid, always reset to their defaults on open, never persisted). Kept private to this file rather than shared with `ErDiagramView.tsx`'s equivalent (minimal sharing). */
function DiagramExportControl({ exporting, onExport }: { exporting: boolean, onExport: (options: DiagramExportOptions) => Promise<void> }) {
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

/**
 * Read-only canvas, mode-aware like the editor: a Flow's persisted `steps[].position` is only
 * authoritative while `autolayoutEnabled` is `false` — while `true`, this
 * view can't rely on it being ELK-fresh, since that freshness is only
 * guaranteed by the *editor's* passive effect writing recomputed positions
 * back via an explicit Save; a Flow whose steps were seeded or
 * otherwise never round-tripped through the editor has no stored `position`
 * at all, which collapsed every node onto the origin here before this fix
 * (found during manual verification against the reseeded demo
 * Flows). So this view recomputes via ELK itself whenever `autolayoutEnabled`
 * is `true`, exactly mirroring `FlowCanvasEditor.tsx`'s passive effect minus
 * the write-back (nothing here ever persists).
 */
function FlowGraphCanvas({ steps, refStatus, autolayoutEnabled, layoutDirection, layoutEngine, onBlockClick }: { steps: FlowStep[], refStatus?: Record<string, FlowStepRefStatus>, autolayoutEnabled: boolean, layoutDirection: FlowLayoutDirection, layoutEngine: FlowLayoutEngine, onBlockClick?: (stepId: string) => void }) {
  const [nodes, setNodes] = useState<FlowNode[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [exporting, setExporting] = useState(false)
  const { fitBounds } = useReactFlow()
  const viewportRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    async function run() {
      let autolayoutPositions: FlowPositions | undefined
      if (autolayoutEnabled) {
        ;({ positions: autolayoutPositions } = await computeFlowAutolayout(steps, layoutDirection, layoutEngine))
      }
      if (cancelled) return
      const positions = mergeStepPositions(steps, autolayoutEnabled, autolayoutPositions)
      const layout = buildFlowNodesAndEdges(steps, positions, refStatus)
      // `showNavigate: true` only here — the editable canvas (`FlowCanvasEditor.tsx`) never sets
      // it, so a Flow/Link node's navigate control renders only on this
      // read-only canvas.
      setNodes(layout.nodes.map((node) => ({ ...node, data: { ...node.data, showNavigate: true } })))
      setEdges(layout.edges)
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [steps, refStatus, autolayoutEnabled, layoutDirection, layoutEngine])

  // The container this canvas renders into doesn't have a fixed size: its
  // caller (`FlowDetailPage.tsx`) sizes it via `useFillViewportHeight`, which
  // starts at a hardcoded placeholder (600) and corrects it to the real
  // fill-to-viewport height in an effect that runs shortly after mount —
  // React Flow's own tracked `width`/`height` (below, backed by a
  // `ResizeObserver` on the actual container) picks up that correction as a
  // second, distinct resize. A fit computed once, synchronously, right after
  // `setNodes` above landed before that correction and used the wrong
  // (placeholder) container size — reproducible: `fitBounds` and the
  // toolbar's manually-clicked `fitView` visibly disagreed on the resulting
  // zoom/position even though both compute from the exact same node bounds
  // (confirmed by direct comparison while diagnosing this). Depending on
  // `width`/`height` here — not just `nodes` — means this reruns and
  // self-corrects the moment the container's real size is known, the same
  // way this effect already reruns for every `steps`/mode change.
  //
  // `fitView()` itself only considers nodes React Flow has actually
  // *measured* via its own `ResizeObserver` (`node.measured.width`/`height`)
  // — never a node's own declared `width`/`height` — so it can't be used
  // here directly: on a fresh load, before any node has been measured, it
  // finds zero fittable nodes and silently leaves the camera untransformed.
  // `getNodesBounds` (unlike `fitView`'s internal node filter) *does* fall
  // back to a node's declared `width`/`height` (`flowLayout.ts`'s
  // `buildFlowNodesAndEdges` sets both to the fixed card size every kind
  // actually renders at), so it's safe to call synchronously off of `nodes`
  // state directly. `<ReactFlow>` below deliberately has no `fitView` prop of
  // its own: once nodes eventually *do* get measured, that mechanism would
  // still fire (queued from mount) and re-fit with its own default padding,
  // visibly jumping the camera right after this effect's fit already
  // rendered correctly.
  const width = useStore((state) => state.width)
  const height = useStore((state) => state.height)
  useEffect(() => {
    if (nodes.length === 0) return
    const bounds = getNodesBounds(nodes)
    // `duration: 0` (not the toolbar Fit button's animated 200) is
    // deliberate: `@xyflow/system`'s `getD3Transition` only drives an actual
    // d3 `.transition()` (backed by `requestAnimationFrame`) when
    // `duration > 0` — at `0` it applies the transform synchronously and
    // resolves immediately instead. A backgrounded/never-foregrounded tab can
    // throttle `requestAnimationFrame` indefinitely, which left an animated
    // call here permanently unresolved in exactly that situation (caught
    // testing this fix); nothing about an automatic, un-requested fit
    // benefits from animating anyway, so `0` sidesteps the dependency
    // entirely rather than merely making it rare.
    void fitBounds(bounds, { duration: 0, padding: 0.2 })
  }, [nodes, width, height, fitBounds])

  async function handleExport({ format, transparent, showGrid }: DiagramExportOptions) {
    const element = viewportRef.current
    if (!element) return
    setExporting(true)
    const restoreEdgeStyles = inlineEdgeExportStyles(element)
    const gridElement = element.querySelector<HTMLElement>('.react-flow__background')
    if (gridElement && !showGrid) gridElement.style.display = 'none'
    try {
      const options = { backgroundColor: transparent ? undefined : '#ffffff' }
      const dataUrl = format === 'svg' ? await toSvg(element, options) : await toPng(element, options)
      downloadDataUrl(dataUrl, `flow.${format}`)
    } finally {
      if (gridElement && !showGrid) gridElement.style.display = ''
      restoreEdgeStyles()
      setExporting(false)
    }
  }

  return (
    <>
      <div ref={viewportRef} style={{ position: 'absolute', inset: 0 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={FLOW_NODE_TYPES}
          edgeTypes={FLOW_EDGE_TYPES}
          nodesConnectable={false}
          nodesDraggable={false}
          onNodeClick={(_event, node) => onBlockClick?.(node.id)}
          minZoom={0.05}
        >
          <Background />
        </ReactFlow>
      </div>
      <FlowGraphToolbar />
      <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, display: 'flex', gap: 4 }}>
        <DiagramExportControl exporting={exporting} onExport={handleExport} />
      </div>
    </>
  )
}

export interface FlowGraphProps {
  steps: FlowStep[]
  /** Live status of each step's `query_ref`/`event_ref` (`FlowEntity.refStatus`), for the stale-reference warning icon. Omitted by a caller with no such data (e.g. a not-yet-saved draft). */
  refStatus?: Record<string, FlowStepRefStatus>
  /** The Flow's persisted mode fields — this read-only view needs all three to resolve positions the same way the editor would. */
  autolayoutEnabled: boolean
  layoutDirection: FlowLayoutDirection
  layoutEngine: FlowLayoutEngine
  height?: number | string
  onBlockClick?: (stepId: string) => void
}

/** Renders a Flow's `steps` as a read-only, typed/colored node diagram. */
export function FlowGraph({ steps, refStatus, autolayoutEnabled, layoutDirection, layoutEngine, height = 'min(75vh, 760px)', onBlockClick }: FlowGraphProps) {
  // Debounced so ELK isn't re-run on every keystroke; the last-good layout
  // stays on screen while a new pass is pending.
  const debouncedSteps = useDebouncedValue(steps, 300)

  if (debouncedSteps.length === 0) {
    return <Text color="secondary">No steps yet</Text>
  }

  return (
    <div className="flow-graph flow-graph--readonly" style={{ height }}>
      <ReactFlowProvider>
        <FlowGraphCanvas steps={debouncedSteps} refStatus={refStatus} autolayoutEnabled={autolayoutEnabled} layoutDirection={layoutDirection} layoutEngine={layoutEngine} onBlockClick={onBlockClick} />
      </ReactFlowProvider>
    </div>
  )
}
