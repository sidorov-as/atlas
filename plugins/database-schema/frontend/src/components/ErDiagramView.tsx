// Renders `parsed_schema` as a read-only, pannable/zoomable React Flow graph
// (read-only is enforced via
// `nodesConnectable={false}` and no add/remove-node UI, while `nodesDraggable`
// stays on for repositioning). Chrome (zoom/fit/export button cluster) is
// reimplemented against `useReactFlow()`, matching the C4 plugin's
// `DiagramViewer` icon set and placement, not its `<img>`-based CSS-transform
// approach (which cannot support draggable nodes).
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useReactFlow,
  type EdgeTypes,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { toPng, toSvg } from 'html-to-image'
import { ArrowUpRightFromSquare, MagicWand, MagnifierMinus, MagnifierPlus, SquareDashed } from '@gravity-ui/icons'
import { Button, Checkbox, Icon, Loader, Popup, SegmentedRadioGroup, Text, Tooltip } from '@gravity-ui/uikit'
import { downloadDataUrl } from 'frontend/lib/diagramExport'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'
import { isUpgradedSchema, type ParsedSchema, type ParsedSchemaRelation, type ParsedSchemaTable } from '../lib/databaseSchemaApi'
import { layoutErDiagramTables, type ErDiagramPositions } from '../lib/erDiagramLayout'
import { tableNodeSize } from '../lib/tableNodeGeometry'
import { RelationshipEdge, type RelationshipFlowEdge } from './RelationshipEdge'
import { TableNode, type TableFlowNode } from './TableNode'

const NODE_TYPES: NodeTypes = { table: TableNode }
const EDGE_TYPES: EdgeTypes = { relationship: RelationshipEdge }

// `onlyRenderVisibleElements` carries its own overhead,
// so it's only worth it once a schema is big enough that off-screen nodes
// would otherwise dominate render cost.
const LARGE_SCHEMA_TABLE_THRESHOLD = 50

function primaryAndForeignKeyColumns(table: ParsedSchemaTable): { primaryKeyColumns: Set<string>, foreignKeyColumns: Set<string> } {
  const primaryKeyColumns = new Set<string>()
  const foreignKeyColumns = new Set<string>()
  for (const constraint of table.constraints) {
    if (constraint.type === 'PRIMARY KEY') for (const column of constraint.columns) primaryKeyColumns.add(column)
    if (constraint.type === 'FOREIGN KEY') for (const column of constraint.columns) foreignKeyColumns.add(column)
  }
  return { primaryKeyColumns, foreignKeyColumns }
}

function buildNodes(tables: ParsedSchemaTable[], positions: ErDiagramPositions): TableFlowNode[] {
  return tables.map((table) => {
    const { primaryKeyColumns, foreignKeyColumns } = primaryAndForeignKeyColumns(table)
    return {
      id: table.name,
      type: 'table',
      position: positions[table.name] ?? { x: 0, y: 0 },
      data: { table, primaryKeyColumns, foreignKeyColumns },
      connectable: false,
    }
  })
}

// One edge per FK column, anchored to that column's own handle,
// so composite foreign keys draw one line per column pair rather than one
// ambiguous table-to-table line. `parent_columns[columnIndex]` falls back to
// `parent_columns[0]` when the two arrays don't line up 1:1.
function buildEdges(relations: ParsedSchemaRelation[]): RelationshipFlowEdge[] {
  return relations.flatMap((relation, relationIndex) => relation.columns
    .map((column, columnIndex) => {
      const parentColumn = relation.parent_columns[columnIndex] ?? relation.parent_columns[0]
      if (!parentColumn) return null
      const edge: RelationshipFlowEdge = {
        id: `rel-${relationIndex}-${columnIndex}`,
        source: relation.table,
        sourceHandle: `${column}-source`,
        target: relation.parent_table,
        targetHandle: `${parentColumn}-target`,
        type: 'relationship',
        data: { cardinality: relation.cardinality },
      }
      return edge
    })
    .filter((edge): edge is RelationshipFlowEdge => edge !== null))
}

// `html-to-image` clones the export target's DOM tree and inlines each
// element's computed style (so the exported image doesn't depend on the
// page's stylesheets) — except for anything nested inside an `<svg>`, which
// it deep-clones natively via `svg.cloneNode(true)` and never walks
// individually. React Flow's edges are exactly that shape (`<div
// class="react-flow__edges"><svg><path class="react-flow__edge-path">`),
// and their stroke color/width come only from `@xyflow/react/dist/style.css`
// class rules, never an inline style — so the exported `<path>` keeps its
// geometry but loses its paint, rendering invisible. Work around it by
// resolving each edge path's (and marker's) computed stroke onto its own
// `style` attribute right before capture: a real DOM attribute, so it *is*
// preserved by the `cloneNode(true)` shortcut. Reverted after capture so the
// live canvas isn't left with stale inline overrides (e.g. across a later
// theme change).
export function inlineEdgeStrokeStyles(root: HTMLElement): () => void {
  const elements = root.querySelectorAll<SVGElement>(
    '.react-flow__edge-path, .react-flow__marker path, .react-flow__marker polyline',
  )
  const restores = Array.from(elements).map((element) => {
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

/** Export trigger button + options popup (format/transparent/grid, always reset to their defaults on open, never persisted). Kept private to this file rather than shared with `FlowGraph.tsx`'s equivalent (minimal sharing). */
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

function ErDiagramGraph({ tables, relations }: { tables: ParsedSchemaTable[], relations: ParsedSchemaRelation[] }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<TableFlowNode>([])
  const [isLayouting, setIsLayouting] = useState(true)
  const [exporting, setExporting] = useState(false)
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  const viewportRef = useRef<HTMLDivElement>(null)
  const { containerRef, height } = useFillViewportHeight()
  const edges = buildEdges(relations)

  // Autolayout runs once on mount and again only on an explicit button press
  // never on every render, so manual dragging in between two
  // presses is never overwritten.
  const runAutolayout = useCallback(async () => {
    setIsLayouting(true)
    try {
      const positions = await layoutErDiagramTables(tables, relations, tableNodeSize)
      setNodes(buildNodes(tables, positions))
      requestAnimationFrame(() => fitView({ duration: 200 }))
    } finally {
      setIsLayouting(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tables, relations])

  useEffect(() => {
    void runAutolayout()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tables, relations])

  // `EntityDetailShell` keeps every tab's `TabPanel` mounted, including
  // hidden ones (@gravity-ui/uikit's `TabPanel`, matching the C4 plugin's
  // `DiagramViewer` — see its own `ResizeObserver` for the identical
  // problem) — so on first mount, if the ER Diagram tab isn't the active
  // one, this container measures 0x0 and `runAutolayout`'s `fitView` computes
  // against garbage bounds. Re-fit whenever the container's real size
  // appears (or changes), which fires the moment the tab becomes visible.
  useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport || !window.ResizeObserver) return
    let frame = 0
    const lastSize = { width: 0, height: 0 }
    const observer = new window.ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      if (!width || !height || (width === lastSize.width && height === lastSize.height)) return
      lastSize.width = width
      lastSize.height = height
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => fitView({ duration: 200 }))
    })
    observer.observe(viewport)
    return () => { cancelAnimationFrame(frame); observer.disconnect() }
  }, [fitView])

  async function handleExport({ format, transparent, showGrid }: DiagramExportOptions) {
    const element = viewportRef.current
    if (!element) return
    setExporting(true)
    const restoreEdgeStyles = inlineEdgeStrokeStyles(element)
    const gridElement = element.querySelector<HTMLElement>('.react-flow__background')
    if (gridElement && !showGrid) gridElement.style.display = 'none'
    try {
      const options = { backgroundColor: transparent ? undefined : '#ffffff' }
      const dataUrl = format === 'svg' ? await toSvg(element, options) : await toPng(element, options)
      downloadDataUrl(dataUrl, `schema.${format}`)
    } finally {
      if (gridElement && !showGrid) gridElement.style.display = ''
      restoreEdgeStyles()
      setExporting(false)
    }
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', height, minHeight: 360, border: '1px solid var(--g-color-line-generic)', borderRadius: 8 }}>
      <div ref={viewportRef} style={{ position: 'absolute', inset: 0 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          nodesConnectable={false}
          nodesDraggable
          onlyRenderVisibleElements={tables.length > LARGE_SCHEMA_TABLE_THRESHOLD}
          minZoom={0.05}
          fitView
        >
          <Background />
        </ReactFlow>
      </div>
      {isLayouting && (
        <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', background: 'var(--g-color-base-float)' }}>
          <Loader size="m" />
        </div>
      )}
      <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', gap: 4 }}>
        <Tooltip content="Auto layout" placement="bottom">
          <Button view="raised" aria-label="Auto layout" onClick={() => void runAutolayout()}><Icon data={MagicWand} /></Button>
        </Tooltip>
        <Tooltip content="Zoom in" placement="bottom">
          <Button view="raised" aria-label="Zoom in" onClick={() => void zoomIn()}><Icon data={MagnifierPlus} /></Button>
        </Tooltip>
        <Tooltip content="Zoom out" placement="bottom">
          <Button view="raised" aria-label="Zoom out" onClick={() => void zoomOut()}><Icon data={MagnifierMinus} /></Button>
        </Tooltip>
        <Tooltip content="Fit to viewport" placement="bottom">
          <Button view="raised" aria-label="Fit to viewport" onClick={() => void fitView({ duration: 200 })}><Icon data={SquareDashed} /></Button>
        </Tooltip>
        <DiagramExportControl exporting={exporting} onExport={handleExport} />
      </div>
    </div>
  )
}

export function ErDiagramView({ schema }: { schema: ParsedSchema }) {
  // Old-shape `parsed_schema` rows (a lightweight shape check with a re-save
  // prompt) predate
  // `relations[]` entirely — treat as not-yet-upgraded rather than crash.
  if (!isUpgradedSchema(schema)) {
    return (
      <Text color="secondary">
        This schema was saved before the ER Diagram upgrade. Open the Schema tab and save it again to see the graph view.
      </Text>
    )
  }
  if (schema.tables.length === 0) {
    return <Text color="secondary">This schema has no tables.</Text>
  }
  return (
    <ReactFlowProvider>
      <ErDiagramGraph tables={schema.tables} relations={schema.relations ?? []} />
    </ReactFlowProvider>
  )
}
