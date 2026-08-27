// Interactive canvas editor replacing `FlowStepEditor.tsx`'s card list
// Structurally mirrors `ErDiagramView.tsx`:
// `useNodesState` drives smooth local dragging, while a step's `position` is
// only written back to the caller's `steps` on drag *stop* — unlike
// ErDiagramView's session-only positions, Flow persists them, so every drag frame must not thrash the parent's state.
import { useEffect, useRef, useState } from 'react'
import {
  Background,
  getNodesBounds,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useReactFlow,
  useStore,
  type Connection,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Gear, MagicWand } from '@gravity-ui/icons'
import { Button, Icon, Popup, SegmentedRadioGroup, Switch, Text, Tooltip } from '@gravity-ui/uikit'

import { FLOW_EDGE_TYPES } from './FlowEdges'
import { FlowGraphToolbar } from './FlowGraph'
import { FLOW_NODE_TYPES } from './FlowNodes'
import { FlowStepModal } from './FlowStepModal'
import { FlowTransitionModal } from './FlowTransitionModal'
import { addConnectedStep, addTransition, canUseTransition, refreshStepRef, removeTransition, transitionTargets, updateTransitionLabel, validateFlowSteps } from './flowSteps'
import {
  buildFlowNodesAndEdges,
  computeFlowAutolayout,
  mergeStepPositions,
  resolveConnectedPosition,
  FLOW_NODE_HEIGHT,
  FLOW_NODE_WIDTH,
  type FlowLayoutDirection,
  type FlowLayoutEngine,
  type FlowNode,
  type FlowPlaceholderNode,
  type FlowPositions,
  type FlowStep,
  type FlowStepRefStatus,
} from '../lib/flowLayout'

type CanvasNode = FlowNode | FlowPlaceholderNode

// A placeholder's own node id, so `handleEdgeClick` can tell a real
// transition edge apart from one of these connectors without threading an
// extra flag through `Edge` (id namespacing already does the job cleanly).
const PLACEHOLDER_SUFFIX = '::add-placeholder'

/**
 * One add-next placeholder for every
 * step with no outgoing transition, positioned exactly like a connected-add's
 * resulting real node (`resolveConnectedPosition`, shared with
 * `addConnectedStep`'s call site below) so it occupies the slot that node
 * would take. Checked against every other real step's position *and* every
 * placeholder already resolved earlier in this same pass, so a childless
 * step whose naive slot is already occupied — e.g. a sibling's own subtree
 * autolayout placed there — gets pushed to a free one instead of drawing on
 * top of it (bug found by inspecting a real Flow's diagram: a childless
 * step's placeholder overlapping an unrelated, already-real node one column
 * over). Given `deletable: false`/`selectable: false`/`draggable: false` at
 * creation as the first line of defense against code that
 * iterates `nodes` assuming every entry is a real step.
 */
function buildPlaceholderNodes(steps: FlowStep[], positions: FlowPositions, direction: FlowLayoutDirection, onAddNext: (stepId: string) => void): FlowPlaceholderNode[] {
  const occupied = steps.map((step) => positions[step.id] ?? { x: 0, y: 0 })
  const placeholders: FlowPlaceholderNode[] = []
  for (const step of steps) {
    if (transitionTargets(step).length > 0) continue
    const sourcePosition = positions[step.id] ?? { x: 0, y: 0 }
    const position = resolveConnectedPosition(sourcePosition, direction, [...occupied, ...placeholders.map((placeholder) => placeholder.position)])
    placeholders.push({
      id: `${step.id}${PLACEHOLDER_SUFFIX}`,
      type: 'add-placeholder',
      position,
      // Same fixed card size as a real step node (`CARD_STYLE_BASE`,
      // `FlowNodes.tsx`) — see `buildFlowNodesAndEdges`'s matching fields for
      // why `fitView` needs this set up front.
      width: FLOW_NODE_WIDTH,
      height: FLOW_NODE_HEIGHT,
      data: { sourceId: step.id, onAddNext },
      draggable: false,
      selectable: false,
      deletable: false,
    })
  }
  return placeholders
}

/**
 * Dashed, unlabeled connector from each placeholder's source step to the
 * placeholder itself, so it's still legible which step a placeholder
 * belongs to once collision-avoidance (`resolveConnectedPosition`) has
 * pushed it away from the naive "immediately past its source" slot — without
 * this, a shifted placeholder reads as an unowned card floating on the
 * canvas. Reuses the same `flow-transition` edge type as real transitions
 * (no label) rather than a second edge component; only `strokeDasharray` is
 * overridden — same default stroke color/weight as a real transition, since
 * the muted `--g-color-line-generic` token this used at first all but
 * disappeared against the canvas's dot grid, undermining the very thing this
 * connector exists to make legible. The dash pattern alone already reads
 * clearly as "preview, not a real transition" — it doesn't also need to be
 * fainter. `selectable: false` and no `markerEnd` keep it visually and
 * interactively inert — clicking it does nothing (`handleEdgeClick` below
 * also guards by id, as a second line of defense mirroring the
 * placeholder-node one).
 */
function buildPlaceholderEdges(placeholders: FlowPlaceholderNode[]): Edge[] {
  return placeholders.map((placeholder) => ({
    id: `${placeholder.data.sourceId}->${placeholder.id}`,
    source: placeholder.data.sourceId,
    target: placeholder.id,
    type: 'flow-transition',
    style: { strokeDasharray: '4 4' },
    selectable: false,
    focusable: false,
  }))
}

/** Gear-icon `Popup` housing canvas layout settings — the `autolayoutEnabled` toggle plus the `layoutEngine` choice — so the toolbar keeps a single settings entry point instead of a bare switch sitting in it directly. */
function FlowCanvasSettings({ autolayoutEnabled, onAutolayoutEnabledChange, layoutEngine, onLayoutEngineChange }: { autolayoutEnabled: boolean, onAutolayoutEnabledChange: (enabled: boolean) => void, layoutEngine: FlowLayoutEngine, onLayoutEngineChange: (engine: FlowLayoutEngine) => void }) {
  const [open, setOpen] = useState(false)
  const [anchorElement, setAnchorElement] = useState<HTMLButtonElement | null>(null)

  return (
    <>
      <Tooltip content="Layout settings" placement="bottom">
        <Button ref={setAnchorElement} view="raised" aria-label="Layout settings" onClick={() => setOpen((value) => !value)}>
          <Icon data={Gear} />
        </Button>
      </Tooltip>
      <Popup anchorElement={anchorElement} open={open} placement="bottom-end" onOpenChange={setOpen}>
        <div style={{ width: 220, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <Text variant="body-short" color="secondary">Autolayout</Text>
            <Switch checked={autolayoutEnabled} onUpdate={onAutolayoutEnabledChange} size="m" />
          </div>
          <div>
            <Text variant="body-short" color="secondary">Layout engine</Text>
            <div style={{ marginTop: 6 }}>
              <SegmentedRadioGroup value={layoutEngine} onUpdate={(value) => onLayoutEngineChange(value as FlowLayoutEngine)} width="max">
                <SegmentedRadioGroup.Option value="dagre">Dagre</SegmentedRadioGroup.Option>
                <SegmentedRadioGroup.Option value="elk">ELK.js</SegmentedRadioGroup.Option>
              </SegmentedRadioGroup>
            </div>
          </div>
        </div>
      </Popup>
    </>
  )
}

export interface FlowCanvasEditorProps {
  steps: FlowStep[]
  onChange: (steps: FlowStep[]) => void
  /** Flow-level, persisted autolayout mode — while `true`, every `steps` mutation recomputes and persists every step's `position` via ELK; while `false`, ELK never runs and `position` only changes via drag or deterministic new-step placement. Replaces this component's old local direction-preference state. */
  autolayoutEnabled: boolean
  /** Persisted Flow field — no longer a per-viewer `localStorage` preference. */
  layoutDirection: FlowLayoutDirection
  /** Persisted Flow field — which layout algorithm (`dagre` or `elk`) the automatic layout pass and the manual layout control use. */
  layoutEngine: FlowLayoutEngine
  /** Toggles `autolayoutEnabled` itself; the toggle's caller owns the persisted value, this component only requests the change. */
  onAutolayoutEnabledChange: (enabled: boolean) => void
  /** Changes `layoutEngine` itself; the toggle's caller owns the persisted value, this component only requests the change. */
  onLayoutEngineChange: (engine: FlowLayoutEngine) => void
  /** Opens the step-edit modal for `stepId` (a plain node click; the `↻` control applies directly via `refreshStepRef` instead, see `onRefresh` wiring below). */
  onEditStep: (stepId: string) => void
  /** A step to pan/center the camera onto once it lands in `nodes`. No current caller uses this — kept as the simplest way to focus a single node if a future entry point needs it. */
  focusStepId?: string | null
  /** A step (typically just-added via the toolbar) to fit the whole diagram into view for, once it lands in `nodes`, instead of panning to it. */
  fitViewStepId?: string | null
  /** Notified with the canvas's merged (stored-or-autolayout) positions on every layout recompute, so a caller can place a new step relative to the current diagram without redoing ELK's layout itself. */
  onPositionsChange?: (positions: FlowPositions) => void
  /** Live status of each step's `query_ref`/`event_ref` (`FlowEntity.refStatus`), for the stale-reference warning icon — from the Flow as last loaded, so it may lag a still-unsaved edit. */
  refStatus?: Record<string, FlowStepRefStatus>
  height?: number
}

function FlowCanvasEditorGraph({ steps, onChange, autolayoutEnabled, layoutDirection, layoutEngine, onAutolayoutEnabledChange, onLayoutEngineChange, onEditStep, focusStepId, fitViewStepId, onPositionsChange, refStatus }: Required<Pick<FlowCanvasEditorProps, 'steps' | 'onChange' | 'autolayoutEnabled' | 'layoutDirection' | 'layoutEngine' | 'onAutolayoutEnabledChange' | 'onLayoutEngineChange' | 'onEditStep'>> & Pick<FlowCanvasEditorProps, 'focusStepId' | 'fitViewStepId' | 'onPositionsChange' | 'refStatus'>) {
  const [nodes, setNodes, onNodesChange] = useNodesState<CanvasNode>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [connectError, setConnectError] = useState<string | null>(null)
  const [selectedTransition, setSelectedTransition] = useState<{ sourceId: string; targetId: string; label?: string } | null>(null)
  // Node-header add control / add-next placeholder: both entry points call `openAddNext` with the clicked
  // node's id, which opens this canvas's own `FlowStepModal` instance
  // (distinct from `FlowFormPage`'s toolbar-add/edit instance) so its save
  // handler has direct access to the source node's resolved position and the
  // canvas's current layout `direction` for `addConnectedStep`.
  const [addNextSourceId, setAddNextSourceId] = useState<string | null>(null)
  const structuralErrors = validateFlowSteps(steps)
  const { setCenter, fitView, fitBounds } = useReactFlow()
  const centeredOnRef = useRef<string | null>(null)
  // The `fitView` prop `<ReactFlow>` used to carry below only fits once,
  // against whatever `nodes` holds at that first render — which is `[]`, since the
  // initial layout effect below fills it in asynchronously afterwards — so it
  // fit an empty diagram and left the camera at its default position/zoom
  // once the real nodes landed, reading as the diagram sitting slightly off
  // to one side. `fitView()` itself only considers nodes React Flow has
  // actually *measured* via its own `ResizeObserver`
  // (`node.measured.width`/`height`), never a node's own declared
  // `width`/`height` — so even deferring it a `requestAnimationFrame` after
  // `setNodes` (this effect's prior approach) still ran before any node had
  // been measured on a true first load, found nothing fittable, and left the
  // camera at its untransformed default; reproduced live on the read-only
  // canvas (`FlowGraph.tsx`), whose viewport `transform` stayed
  // `translate(0px, 0px) scale(1)` indefinitely until the toolbar's own Fit
  // button was clicked by hand. `getNodesBounds` (unlike `fitView`'s internal
  // node filter) *does* fall back to a node's declared `width`/`height`
  // (`flowLayout.ts`'s `buildFlowNodesAndEdges`/this file's
  // `buildPlaceholderNodes` both set it to the fixed card size every kind
  // actually renders at) — so computing bounds from it works synchronously,
  // right after the first `setNodes`. Guarded to fire only once (not on every
  // later recompute) so autolayout/edits don't yank an editing user's camera
  // back.
  //
  // That single fit is still deferred a little further (see the dedicated
  // effect below, keyed on the container's own tracked `width`/`height`):
  // this canvas's container doesn't have a fixed size — its caller sizes it
  // via `useFillViewportHeight`, which starts at a hardcoded placeholder
  // (600) and corrects it to the real fill-to-viewport height in an effect
  // that runs shortly after mount. Computing the one-shot fit synchronously
  // inside *this* effect used that still-wrong placeholder size — confirmed
  // by comparing this fit's resulting transform against the toolbar's own
  // (identically-computed) Fit button clicked moments later: same node
  // bounds, visibly different zoom/position, because the container had
  // since resized out from under it.
  const initialFitDoneRef = useRef(false)
  const lastFitNodesRef = useRef<CanvasNode[] | null>(null)
  const [pendingFitVersion, setPendingFitVersion] = useState(0)

  // Recomputes on every `steps` change: a discrete user action (drag stop,
  // connect, delete, modal save), never a per-frame drag update — those stay
  // local to `useNodesState` below.
  //
  // Mode-aware: while
  // `autolayoutEnabled`, ELK runs on every pass and its result is the only
  // position that matters — but ELK is deterministic for a given `steps`
  // shape/`layoutDirection`, so once a prior pass has already written that
  // exact result back (below), a later pass recomputing the *same* value
  // finds nothing stale and just renders, rather than looping. When it *is*
  // stale (a step has no stored position yet, or was just dragged — a drag is
  // itself a `steps` change with no lasting
  // effect), this writes the fresh positions back via `onChange` and returns
  // without rendering this pass; the resulting `steps` update re-triggers
  // this same effect, which then finds the now-matching positions and
  // renders. While not `autolayoutEnabled`, ELK never runs at all (Decision
  // 4) and every step renders at exactly its own stored `position`.
  useEffect(() => {
    let cancelled = false
    async function run() {
      let autolayoutPositions: FlowPositions | undefined
      if (autolayoutEnabled) {
        ;({ positions: autolayoutPositions } = await computeFlowAutolayout(steps, layoutDirection, layoutEngine))
      }
      if (cancelled) return
      const positions = mergeStepPositions(steps, autolayoutEnabled, autolayoutPositions)
      if (autolayoutEnabled) {
        const stale = steps.some((step) => step.position?.x !== positions[step.id]?.x || step.position?.y !== positions[step.id]?.y)
        if (stale) {
          onChange(steps.map((step) => ({ ...step, position: positions[step.id] })))
          return
        }
      }
      const layout = buildFlowNodesAndEdges(steps, positions, refStatus, openTransitionModal)
      // `onRefresh` applies `refreshStepRef` straight to `steps` — no modal, matching
      // `removeSteps`'s directness below: exactly as reversible as any other canvas edit
      // (undone by not saving the Flow), so gating it behind an extra "open the modal, click
      // Save" round trip was pure friction. The modal's own `↻` (shown when a step happens to be open and stale)
      // is unaffected — it still only commits on the modal's explicit Save.
      const stepNodes = layout.nodes.map((node) => ({ ...node, data: { ...node.data, onDelete: removeSteps, onAddNext: setAddNextSourceId, onRefresh: (stepId: string) => onChange(refreshStepRef(steps, stepId, refStatus?.[stepId]?.live)) } }))
      const placeholderNodes = buildPlaceholderNodes(steps, positions, layoutDirection, setAddNextSourceId)
      setNodes([...stepNodes, ...placeholderNodes])
      setEdges([...layout.edges, ...buildPlaceholderEdges(placeholderNodes)])
      onPositionsChange?.(positions)
      if (!initialFitDoneRef.current && (stepNodes.length > 0 || placeholderNodes.length > 0)) {
        lastFitNodesRef.current = [...stepNodes, ...placeholderNodes]
        setPendingFitVersion((version) => version + 1)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
    // `onChange` deliberately excluded: including it would re-run this effect
    // (and re-invoke the layout engine) on every parent re-render that
    // happens to pass a new function identity, not just on an actual
    // `steps`/mode change. Since a fresh closure is captured on every render
    // regardless, the effect still always calls the *latest* `onChange`
    // whenever it actually runs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [steps, refStatus, setNodes, autolayoutEnabled, layoutDirection, layoutEngine])

  // Performs the one-shot initial fit recorded above, but only once the
  // container's own tracked `width`/`height` (from `useStore`, backed by a
  // `ResizeObserver` on the real container — unlike the `steps`-driven effect
  // above, this reacts to a pure container *resize*, e.g.
  // `useFillViewportHeight`'s correction) has gone a short moment without
  // changing again. Debounced (not applied on the very first fire) because
  // that correction lands as a *second*, separate resize shortly after
  // mount: applying immediately on the first `width`/`height` this effect
  // ever sees would just as easily catch the pre-correction placeholder size
  // instead of the real one.
  const width = useStore((state) => state.width)
  const height = useStore((state) => state.height)
  useEffect(() => {
    if (initialFitDoneRef.current) return
    const nodesForFit = lastFitNodesRef.current
    if (!nodesForFit || nodesForFit.length === 0) return
    const timer = window.setTimeout(() => {
      initialFitDoneRef.current = true
      const bounds = getNodesBounds(lastFitNodesRef.current ?? [])
      // `padding: 0.2` matches `FlowGraphToolbar`'s Fit button
      // (`FlowGraph.tsx`) exactly — left at the default (0.1) here, this fit
      // and a manual click of that same button computed visibly different
      // zooms off the *same* bounds (caught testing this fix).
      void fitBounds(bounds, { duration: 0, padding: 0.2 })
    }, 100)
    return () => window.clearTimeout(timer)
  }, [pendingFitVersion, width, height, fitBounds])

  // Pans to a just-added (or otherwise externally focused) node exactly once
  // per `focusStepId` value, as soon as it appears in the (asynchronously
  // rebuilt) `nodes` state — not on every later `nodes` update, or every drag
  // would yank the camera back to it.
  useEffect(() => {
    if (!focusStepId || centeredOnRef.current === focusStepId) return
    const node = nodes.find((candidate) => candidate.id === focusStepId)
    if (!node) return
    centeredOnRef.current = focusStepId
    void setCenter(node.position.x + FLOW_NODE_WIDTH / 2, node.position.y + FLOW_NODE_HEIGHT / 2, { duration: 200 })
  }, [focusStepId, nodes, setCenter])

  // Toolbar "Add Step" path: since that path
  // now gives the new step a deterministic, non-colliding `position` up
  // front, there's no longer a need to pan the camera to it specifically —
  // fitting the whole (now-taller) diagram into view, once the new node
  // lands in `nodes`, shows it in context instead.
  const fitOnRef = useRef<string | null>(null)
  useEffect(() => {
    if (!fitViewStepId || fitOnRef.current === fitViewStepId) return
    const node = nodes.find((candidate) => candidate.id === fitViewStepId)
    if (!node) return
    fitOnRef.current = fitViewStepId
    requestAnimationFrame(() => fitView({ duration: 200 }))
  }, [fitViewStepId, nodes, fitView])

  // While `autolayoutEnabled`, dragging is left enabled rather than disabled
  // on the canvas — but instead of just
  // writing the dragged position back and relying on the passive layout
  // effect above to notice it's stale and correct it on the next pass
  // this re-invokes the
  // layout engine directly and writes its result back immediately. Observable
  // behavior is unchanged — the dragged node still snaps back — only the
  // mechanism (direct recompute vs. diff-and-correct) differs.
  function handleNodeDragStop(_event: unknown, node: CanvasNode) {
    if (node.type === 'add-placeholder') return
    if (autolayoutEnabled) {
      void (async () => {
        const { positions } = await computeFlowAutolayout(steps, layoutDirection, layoutEngine)
        onChange(steps.map((step) => ({ ...step, position: positions[step.id] ?? step.position })))
      })()
      return
    }
    onChange(steps.map((step) => (step.id === node.id ? { ...step, position: node.position } : step)))
  }

  // Explicit, user-initiated escape hatch, available only in manual mode
  // unlike the passive effect above,
  // this always recomputes and overwrites every visible step's position with
  // the freshly computed layout, without changing `autolayoutEnabled`.
  // Sets `nodes`/`edges` directly (rather than only via `onChange`, which
  // reaches this component's layout effect on the *next* render) so the
  // following `fitView` always measures the freshly laid-out positions.
  async function handleAutoLayout() {
    const { positions } = await computeFlowAutolayout(steps, layoutDirection, layoutEngine)
    const nextSteps = steps.map((step) => ({ ...step, position: positions[step.id] ?? step.position }))
    const layout = buildFlowNodesAndEdges(nextSteps, positions, refStatus, openTransitionModal)
    const stepNodes = layout.nodes.map((node) => ({ ...node, data: { ...node.data, onDelete: removeSteps, onAddNext: setAddNextSourceId, onRefresh: (stepId: string) => onChange(refreshStepRef(steps, stepId, refStatus?.[stepId]?.live)) } }))
    const placeholderNodes = buildPlaceholderNodes(nextSteps, positions, layoutDirection, setAddNextSourceId)
    setNodes([...stepNodes, ...placeholderNodes])
    setEdges([...layout.edges, ...buildPlaceholderEdges(placeholderNodes)])
    requestAnimationFrame(() => fitView({ duration: 200 }))
    onChange(nextSteps)
  }

  function handleConnect(connection: Connection) {
    const { source, target } = connection
    if (!source || !target) return
    const error = canUseTransition(steps, source, target)
    if (error) {
      setConnectError(error)
      return
    }
    setConnectError(null)
    onChange(addTransition(steps, source, target))
  }

  // Shared by keyboard/selection deletion (`onNodesDelete`, below) and each
  // node's hover delete button (`FlowNodes.tsx`'s `NodeDeleteButton`, wired
  // via `data.onDelete` above) — removes the step(s) and cascade-clears any
  // transition that targeted them (matching `FlowStepEditor.remove()`'s
  // prior behavior).
  function removeStepIds(removedIds: Set<string>) {
    onChange(steps
      .filter((step) => !removedIds.has(step.id))
      .map((step) => ({
        ...step,
        next_step: step.next_step && removedIds.has(step.next_step.id) ? undefined : step.next_step,
        next_steps: step.next_steps?.filter((transition) => !removedIds.has(transition.id)),
      })))
  }

  function removeSteps(stepId: string) {
    removeStepIds(new Set([stepId]))
  }

  // `deletable: false` on placeholder nodes (`buildPlaceholderNodes`) already
  // keeps React Flow from including them here; this filter is a
  // second line of defense against a placeholder ever reaching
  // code that assumes every `nodes` entry is a real step.
  function handleNodesDelete(deleted: CanvasNode[]) {
    removeStepIds(new Set(deleted.filter((node) => node.type !== 'add-placeholder').map((node) => node.id)))
  }

  // Shared by both ways to open a transition's edit modal: a click on the edge's own path (`handleEdgeClick` below) and
  // a click directly on the edge's HTML label (`FlowEdges.tsx`'s
  // `FlowTransitionEdge`, wired via `buildFlowNodesAndEdges`'s
  // `onOpenTransitionModal` parameter) — both remain valid gestures for the
  // same outcome.
  function openTransitionModal(sourceId: string, targetId: string, label?: string) {
    setSelectedTransition({ sourceId, targetId, label })
  }

  // Scoped to the one edge clicked, not a node-level
  // interaction, so a click on an edge's own path — not a node — opens the
  // transition modal instead of the step edit modal (`onNodeClick`, above).
  // A placeholder connector (`buildPlaceholderEdges`) isn't a real transition
  // — its target is a synthetic placeholder id, not a step — so it's not a
  // valid `FlowTransitionModal` subject; `selectable: false` already keeps
  // React Flow from treating it as clickable, this is the second line of
  // defense (mirrors `onNodeClick`'s placeholder-node guard below).
  function handleEdgeClick(_event: unknown, edge: Edge) {
    if (edge.target.endsWith(PLACEHOLDER_SUFFIX)) return
    openTransitionModal(edge.source, edge.target, typeof edge.label === 'string' ? edge.label : undefined)
  }

  // `addConnectedStep` needs the source
  // node's *resolved* position — read from `nodes`, which already carries
  // the merged (stored-or-autolayout) position the layout effect above just
  // computed, rather than recomputing it here. `resolveConnectedPosition`
  // checks the naive slot against every other real node currently on the
  // canvas (placeholders excluded — they're not real obstacles, and the
  // clicked one is often sitting exactly where the new step is about to
  // land) so the added step never lands on top of one of them either.
  function handleAddNextSave(nextStep: FlowStep) {
    if (!addNextSourceId) return
    const sourcePosition = nodes.find((node) => node.id === addNextSourceId)?.position ?? { x: 0, y: 0 }
    const occupied = nodes.filter((node) => node.type !== 'add-placeholder').map((node) => node.position)
    const position = resolveConnectedPosition(sourcePosition, layoutDirection, occupied)
    onChange(addConnectedStep(steps, addNextSourceId, nextStep, position))
    setAddNextSourceId(null)
  }

  function handleTransitionSave(sourceId: string, targetId: string, label: string) {
    onChange(updateTransitionLabel(steps, sourceId, targetId, label))
  }

  // Cascades the same way `removeStepIds` cascades a whole node's
  // transitions, but scoped to the one edge clicked —
  // neither endpoint step is touched.
  function handleTransitionDelete(sourceId: string, targetId: string) {
    onChange(removeTransition(steps, sourceId, targetId))
  }

  return (
    <>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onNodeDragStop={handleNodeDragStop}
        onNodesDelete={handleNodesDelete}
        onConnect={handleConnect}
        onEdgeClick={handleEdgeClick}
        onNodeClick={(event, node) => {
          // A click on the node's own delete or add-next button (`FlowNodes.tsx`)
          // still reaches this handler — React Flow's node-click handling
          // isn't stopped by that button's React `stopPropagation()` — so
          // ignore it here instead of also reopening the edit modal.
          if ((event.target as HTMLElement).closest('.flow-graph__node-delete')) return
          if ((event.target as HTMLElement).closest('.flow-graph__node-add-next')) return
          // The placeholder card is a click target in its own right — identical to the node-header add control,
          // same `setAddNextSourceId`/`addConnectedStep` code path, keyed off
          // this synthetic node's `sourceId` rather than a real step's id.
          if (node.type === 'add-placeholder') {
            setAddNextSourceId((node.data as FlowPlaceholderNode['data']).sourceId)
            return
          }
          onEditStep(node.id)
        }}
        nodeTypes={FLOW_NODE_TYPES}
        edgeTypes={FLOW_EDGE_TYPES}
        nodesDraggable
        nodesConnectable
        deleteKeyCode={['Backspace', 'Delete']}
        minZoom={0.05}
      >
        <Background />
      </ReactFlow>
      <FlowGraphToolbar />
      <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, display: 'flex', gap: 4, alignItems: 'center' }}>
        <FlowCanvasSettings autolayoutEnabled={autolayoutEnabled} onAutolayoutEnabledChange={onAutolayoutEnabledChange} layoutEngine={layoutEngine} onLayoutEngineChange={onLayoutEngineChange} />
        {/* Manual-mode-only one-shot recompute: renamed away from
            "Auto layout" so it doesn't read as the same thing as the setting above, and
            hidden while that setting is on since there's nothing to tidy — every `steps`
            change already keeps positions fully recomputed. */}
        {!autolayoutEnabled && (
          <Tooltip content="Tidy layout" placement="bottom">
            <Button view="raised" aria-label="Tidy layout" onClick={() => void handleAutoLayout()}>
              <Icon data={MagicWand} />
            </Button>
          </Tooltip>
        )}
      </div>
      <FlowTransitionModal
        transition={selectedTransition}
        onClose={() => setSelectedTransition(null)}
        onSave={handleTransitionSave}
        onDelete={handleTransitionDelete}
      />
      <FlowStepModal
        open={addNextSourceId !== null}
        steps={steps}
        step={null}
        onClose={() => setAddNextSourceId(null)}
        onSave={handleAddNextSave}
      />
      {(structuralErrors.length > 0 || connectError) && (
        <div style={{ position: 'absolute', bottom: 12, left: 12, right: 12, display: 'flex', flexDirection: 'column', gap: 4, pointerEvents: 'none' }}>
          {connectError && (
            <div style={{ background: 'var(--g-color-base-danger-light)', borderRadius: 6, padding: '6px 10px', pointerEvents: 'auto' }}>
              <Text color="danger" variant="caption-2">{connectError}</Text>
            </div>
          )}
          {structuralErrors.length > 0 && (
            <div style={{ background: 'var(--g-color-base-danger-light)', borderRadius: 6, padding: '6px 10px', pointerEvents: 'auto' }}>
              <Text color="danger" variant="caption-2">{structuralErrors.join(' · ')}</Text>
            </div>
          )}
        </div>
      )}
    </>
  )
}

/** Editable canvas: add/edit via `onEditStep` (opens `FlowStepModal`), connect via drag, position via drag, delete via selection. */
export function FlowCanvasEditor({ steps, onChange, autolayoutEnabled, layoutDirection, layoutEngine, onAutolayoutEnabledChange, onLayoutEngineChange, onEditStep, focusStepId, fitViewStepId, onPositionsChange, refStatus, height = 600 }: FlowCanvasEditorProps) {
  return (
    <div className="flow-graph" style={{ height, position: 'relative' }}>
      <ReactFlowProvider>
        <FlowCanvasEditorGraph
          steps={steps}
          onChange={onChange}
          autolayoutEnabled={autolayoutEnabled}
          layoutDirection={layoutDirection}
          layoutEngine={layoutEngine}
          onAutolayoutEnabledChange={onAutolayoutEnabledChange}
          onLayoutEngineChange={onLayoutEngineChange}
          onEditStep={onEditStep}
          focusStepId={focusStepId}
          fitViewStepId={fitViewStepId}
          onPositionsChange={onPositionsChange}
          refStatus={refStatus}
        />
      </ReactFlowProvider>
    </div>
  )
}
