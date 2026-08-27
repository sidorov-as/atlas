// DAG layout for Flow diagrams: reworked from a strict divergence-only tree
// to an acyclic transition graph, with a plain, position-only layered layout
// selectable between `dagre` and `elkjs` (no custom ELK-ports/
// Coffman-Graham-alignment/bendpoint-routing pipeline).
//
// `steps[]` is validated server-side as an acyclic transition graph
// (`models.py`'s `validate_steps`): a step id may be the target of any number
// of incoming transitions (branches may diverge and reconverge), but a cycle
// — including a step transitioning to itself — is rejected. `buildForest()`
// still walks `steps[]` into a forest of trees for node placement/layout
// order, placing each step exactly once even against a cycle that may
// briefly exist mid-edit in the JSON preview (so recursion still terminates
// and a node still renders exactly once); the layout engines/
// `buildFlowNodesAndEdges` no longer derive their *edges* from that forest,
// though, since a step's second-plus incoming transition is a real edge, not
// a duplicate to drop — they read edges straight from `steps[]` instead (see
// `edgesOf`), so every transition renders regardless of how many incoming
// edges its target has.
//
// Node/edge output targets `@xyflow/react` directly. A step's `position` is
// governed by the Flow-level `autolayout_enabled` flag: while enabled, every step's `position` is a fresh
// `computeFlowAutolayout()` result, with no stored value ever consulted;
// while disabled, no engine ever runs and every step's `position` is exactly
// its own stored value. `mergeStepPositions()` is the mode-aware resolver
// call sites use for this.
//
// Connections render as a live `getSmoothStepPath` curve between their two
// nodes' actual handle positions (`FlowEdges.tsx`) — never a precomputed,
// obstacle-aware polyline. Neither engine below declares ports, fixed
// positions, or does any bendpoint/section extraction; each produces node
// positions only.

import dagre from 'dagre'
import ELK from 'elkjs/lib/elk.bundled.js'
import type { ElkNode } from 'elkjs'
import { MarkerType, type Edge, type Node } from '@xyflow/react'
import type { FlowStep, FlowStepRefStatus } from 'frontend/lib/types'

import { flowNodeKindOf, type FlowNodeKind } from './flowNodeKind'

// `FlowStep`/`FlowStepTransition`/`FlowStepLabelTheme` live in `frontend/lib/types`
// not here: core's `FlowEntity` needs the same shape
// independent of whether `atlas.flows` is selected. Re-exported so this
// package's own internal call sites (`from '../lib/flowLayout'`) don't need
// to change.
export type { FlowStep, FlowStepEventRef, FlowStepLabelTheme, FlowStepQueryRef, FlowStepRefStatus, FlowStepTransition } from 'frontend/lib/types'

/** Layout direction for autolayout — a persisted `Flow` field, not a per-viewer preference. */
export type FlowLayoutDirection = 'LAYOUT_TOP_DOWN' | 'LAYOUT_LEFT_RIGHT'

/** Which layout algorithm computes positions — a persisted, per-Flow field, alongside `layout_direction`. */
export type FlowLayoutEngine = 'dagre' | 'elk'

const ELK_DIRECTION: Record<FlowLayoutDirection, string> = {
  LAYOUT_TOP_DOWN: 'DOWN',
  LAYOUT_LEFT_RIGHT: 'RIGHT',
}

export interface FlowNodeData extends Record<string, unknown> {
  step: FlowStep
  /** Editable canvas only: hover delete affordance — clicking a node opens its edit modal, so deletion needs its own gesture rather than colliding with click-to-select. */
  onDelete?: (stepId: string) => void
  /** Editable canvas only: node-header add control — opens the node-type picker with this step recorded as the connect-from source. */
  onAddNext?: (stepId: string) => void
  /** Editable canvas only, Call/Event nodes with an active drift warning only: applies the step's live `query_ref`/`event_ref` values directly (`refreshStepRef`), no modal — exactly as reversible as any other canvas edit, undone by not saving the Flow. */
  onRefresh?: (stepId: string) => void
  /** This step's live `query_ref`/`event_ref` status, resolved at read time — undefined when the step has no such ref, or the ref no longer resolves. */
  refStatus?: FlowStepRefStatus
  /** Read-only-canvas-only: set only by `FlowGraph.tsx`, never by the editable canvas — a Flow/Link node's navigate control renders only when this is set, mirroring (inverted) how `onDelete`/`onAddNext`/`onRefresh` above are edit-canvas-only by being unset on the read-only canvas. Not itself a callback (there's nothing to call — the target is a real `<a>`/route href computed straight from the step's own `flow_ref`/`link_url`), just a capability flag. */
  showNavigate?: boolean
}

export type FlowNode = Node<FlowNodeData, FlowNodeKind>

/** Synthetic "add next step" placeholder — never written into `steps[]`; computed alongside real nodes for every step with no outgoing transition. */
export interface FlowPlaceholderNodeData extends Record<string, unknown> {
  /** The childless step this placeholder would connect from. */
  sourceId: string
  onAddNext?: (stepId: string) => void
}
export type FlowPlaceholderNode = Node<FlowPlaceholderNodeData, 'add-placeholder'>

export interface FlowLayout {
  nodes: FlowNode[]
  edges: Edge[]
}

/**
 * Fixed node footprint, shared with the typed node components so the layout
 * engines' reserved space matches what actually renders. `FLOW_NODE_HEIGHT`
 * matches a full three-line card (type row, title, subtitle/summary) — the
 * shape every entity-backed/External card always renders (their subtitle is
 * effectively always present) — measured directly from a real rendered card
 * rather than guessed, so `FlowNodes.tsx`'s now-fixed (not min-) card height
 * doesn't clip a three-line card, and every card kind — including a
 * two-line Step or the icon-only add-placeholder — ends up the same height
 * instead of shrinking to fit however many lines it happens to have.
 *
 * The three rows' natural content height (chip + title + subtitle, each
 * `overflow: hidden` for its own ellipsis truncation) plus their `gap`s
 * comes to exactly the old 74's content box (74 minus the card's own
 * vertical padding) with no slack — a flex column shrinks an
 * `overflow: hidden` item's automatic minimum size to 0 rather than its
 * content size (CSS Flexbox §4.5), so that zero-slack fit let a fractional
 * layout/font-metric rounding difference shrink a row below its line-height
 * and clip descenders (e.g. "g") instead of overflowing visibly. The extra
 * 10px here is slack, not new content.
 */
export const FLOW_NODE_WIDTH = 180
export const FLOW_NODE_HEIGHT = 84

/** Gap the layout engines reserve between layers; also reused, unscaled, as the gap below the flow's existing bounding box for a newly toolbar-added row, and as the gap past a source node for a connected-add's computed position. */
export const FLOW_LAYER_GAP = 60

/** Gap the layout engines reserve between sibling nodes in the same layer — otherwise siblings render edge-to-edge; a gap on the same order of magnitude as `FLOW_LAYER_GAP` reads as breathing room without materially changing the diagram's footprint. */
const FLOW_SIBLING_GAP = Math.round(FLOW_NODE_HEIGHT * 0.7)

interface LayoutNode {
  step: FlowStep
  children: LayoutNode[]
}

function childIdsOf(step: FlowStep): string[] {
  const ids: string[] = []
  if (step.next_step) ids.push(step.next_step.id)
  for (const transition of step.next_steps ?? []) ids.push(transition.id)
  return ids
}

function buildForest(steps: FlowStep[]): LayoutNode[] {
  const byId = new Map(steps.map((step) => [step.id, step]))
  const targeted = new Set<string>()
  for (const step of steps) {
    for (const id of childIdsOf(step)) targeted.add(id)
  }

  const placed = new Set<string>()
  function build(step: FlowStep): LayoutNode {
    placed.add(step.id)
    const children = childIdsOf(step)
      .map((id) => byId.get(id))
      .filter((child): child is FlowStep => child !== undefined && !placed.has(child.id))
      .map((child) => build(child))
    return { step, children }
  }

  const forest: LayoutNode[] = []
  // Preferred roots: steps with no incoming transition.
  for (const step of steps) {
    if (!targeted.has(step.id) && !placed.has(step.id)) forest.push(build(step))
  }
  // Fallback for input that isn't a valid tree yet (mid-edit in the JSON
  // preview) — e.g. a pure cycle has no step with zero incoming edges, so
  // nothing above matches. Root any step still unplaced so it still renders.
  for (const step of steps) {
    if (!placed.has(step.id)) forest.push(build(step))
  }
  return forest
}

function transitionLabel(step: FlowStep, targetId: string): string | undefined {
  if (step.next_step?.id === targetId) return step.next_step.label
  return step.next_steps?.find((transition) => transition.id === targetId)?.label
}

/** Flattens a forest into its node-placement order (one step per entry, first-reachable-root-first) — the ordering the layout engines/`buildFlowNodesAndEdges` use for their node lists, kept separate from edge derivation (see `edgesOf` below) now that a target's second-plus incoming edge must survive rather than being dropped by forest placement. */
function flattenForestOrder(forest: LayoutNode[]): FlowStep[] {
  const ordered: FlowStep[] = []
  function walk(node: LayoutNode): void {
    ordered.push(node.step)
    for (const child of node.children) walk(child)
  }
  for (const root of forest) walk(root)
  return ordered
}

/** One entry per real transition in `steps[]` whose target exists — independent of `buildForest`'s placement, so a target's second (or later) incoming transition renders as a real edge instead of being silently dropped. A dangling target (mid-edit invalid JSON) is skipped rather than throwing. */
function edgesOf(steps: FlowStep[]): { sourceId: string; targetId: string }[] {
  const ids = new Set(steps.map((step) => step.id))
  const edges: { sourceId: string; targetId: string }[] = []
  for (const step of steps) {
    for (const targetId of childIdsOf(step)) {
      if (ids.has(targetId)) edges.push({ sourceId: step.id, targetId })
    }
  }
  return edges
}

/** Fixed max-width the custom edge label renderer (`FlowEdges.tsx`'s `FlowTransitionEdge`) wraps a transition label within — shared here so a layout engine's reserved space matches what actually renders. */
export const FLOW_EDGE_LABEL_MAX_WIDTH = 140
const FLOW_EDGE_LABEL_LINE_HEIGHT = 16
// Same per-character/padding heuristic this estimate always used for a
// single line, now also used to derive how many characters fit per wrapped
// line at the renderer's fixed max-width.
const FLOW_EDGE_LABEL_CHAR_WIDTH = 8
const FLOW_EDGE_LABEL_PADDING = 16

// Neither engine needs a pixel-perfect label size to reserve enough gap
// between layers for an edge's label to render without overlapping a
// neighboring node — it doesn't need to match the canvas's actual text
// measurement. Estimates wrapped line count from the label's length and the
// renderer's fixed max-width, since a long label wraps instead of
// overflowing.
function estimateLabelSize(label: string): { width: number; height: number } {
  const charsPerLine = Math.max(1, Math.floor((FLOW_EDGE_LABEL_MAX_WIDTH - FLOW_EDGE_LABEL_PADDING) / FLOW_EDGE_LABEL_CHAR_WIDTH))
  const lines = Math.max(1, Math.ceil(label.length / charsPerLine))
  return {
    width: Math.min(label.length * FLOW_EDGE_LABEL_CHAR_WIDTH + FLOW_EDGE_LABEL_PADDING, FLOW_EDGE_LABEL_MAX_WIDTH),
    height: lines * FLOW_EDGE_LABEL_LINE_HEIGHT,
  }
}

export type FlowPositions = Record<string, { x: number; y: number }>

interface FlowLayoutEdge {
  sourceId: string
  targetId: string
  label?: string
}

/** One node/edge list, in the shape both layout engines below consume, derived once from `steps[]`. */
function flowLayoutGraph(steps: FlowStep[]): { nodeIds: string[]; edges: FlowLayoutEdge[] } {
  const nodeIds = flattenForestOrder(buildForest(steps)).map((step) => step.id)
  const edges = edgesOf(steps).map(({ sourceId, targetId }) => {
    const source = steps.find((step) => step.id === sourceId)!
    return { sourceId, targetId, label: transitionLabel(source, targetId) }
  })
  return { nodeIds, edges }
}

/**
 * Plain dagre layered layout — a fresh `dagre.graphlib.Graph` built per call,
 * one node per step at `FLOW_NODE_WIDTH`/`FLOW_NODE_HEIGHT`, one edge per
 * transition with `estimateLabelSize()`-derived label dimensions so dagre
 * reserves enough inter-layer space for a labeled edge. No ports or
 * bendpoint/section extraction, with `rankdir` following `direction` instead of always `'LR'`.
 */
function layoutWithDagre(nodeIds: string[], edges: FlowLayoutEdge[], direction: FlowLayoutDirection): FlowPositions {
  const graph = new dagre.graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({ rankdir: direction === 'LAYOUT_TOP_DOWN' ? 'TB' : 'LR', nodesep: FLOW_SIBLING_GAP, ranksep: FLOW_LAYER_GAP })
  for (const id of nodeIds) graph.setNode(id, { width: FLOW_NODE_WIDTH, height: FLOW_NODE_HEIGHT })
  // dagre reserves real layout space for an edge label when it's given a
  // `width`/`height` (its docs: this sizes "the space needed for edge
  // labels in the layout") — without it, every edge is spaced as if it
  // carried no label at all, regardless of how long the text actually is.
  // Calling `setEdge` with only 2 arguments for an unlabeled edge (not a
  // 3rd, explicit `undefined`) matters: graphlib's `setEdge` treats *any*
  // 3-argument call as "value specified" and skips its own default-label
  // fallback, which would otherwise leave `{}` in its place.
  for (const edge of edges) {
    if (edge.label) graph.setEdge(edge.sourceId, edge.targetId, estimateLabelSize(edge.label))
    else graph.setEdge(edge.sourceId, edge.targetId)
  }
  dagre.layout(graph)

  const positions: FlowPositions = {}
  for (const id of nodeIds) {
    const node = graph.node(id)
    // dagre positions a node at its own center; xyflow positions a node at
    // its top-left corner, same top-left convention this module uses
    // everywhere else.
    positions[id] = { x: node.x - FLOW_NODE_WIDTH / 2, y: node.y - FLOW_NODE_HEIGHT / 2 }
  }
  return positions
}

// A single shared instance is safe: each `elk.layout()` call is an
// independent, synchronous-under-the-hood computation wrapped in a Promise
// (this is the bundled, non-worker build), so there's no cross-call state to
// worry about.
const elk = new ELK()

/**
 * Plain elkjs layered layout — one flat ELK graph (all steps as siblings,
 * one edge per transition), no ports/`FIXED_POS`/bendpoint-or-section
 * extraction. This
 * keeps `elk.layered.layering.strategy: COFFMAN_GRAHAM`: independent of the
 * now-deleted sibling-column-alignment step, it alone keeps same-tree-depth
 * siblings in one shared layer rather than scattered across two or three
 * different ones by ELK's default edge-length-minimizing strategy (see the
 * "wide fan-out" regression test in `flowLayout.test.ts`).
 */
async function layoutWithElk(nodeIds: string[], edges: FlowLayoutEdge[], direction: FlowLayoutDirection): Promise<FlowPositions> {
  const graph: ElkNode = {
    id: 'root',
    layoutOptions: {
      'elk.direction': ELK_DIRECTION[direction],
      'elk.layered.spacing.nodeNodeBetweenLayers': String(FLOW_LAYER_GAP),
      'elk.spacing.nodeNode': String(FLOW_SIBLING_GAP),
      'elk.layered.layering.strategy': 'COFFMAN_GRAHAM',
    },
    children: nodeIds.map((id) => ({ id, width: FLOW_NODE_WIDTH, height: FLOW_NODE_HEIGHT })),
    edges: edges.map((edge) => ({
      id: `${edge.sourceId}->${edge.targetId}`,
      sources: [edge.sourceId],
      targets: [edge.targetId],
      labels: edge.label ? [{ text: edge.label, ...estimateLabelSize(edge.label) }] : undefined,
    })),
  }
  const result = await elk.layout(graph)
  const positions: FlowPositions = {}
  for (const child of result.children ?? []) positions[child.id] = { x: child.x ?? 0, y: child.y ?? 0 }
  return positions
}

/** Runs the selected layout engine over every step (ignoring any stored `position`) and returns the computed positions. `edgeRouting` no longer exists — every connection renders as a live curve between its endpoints' current positions instead (`FlowEdges.tsx`). */
export async function computeFlowAutolayout(steps: FlowStep[], direction: FlowLayoutDirection = 'LAYOUT_LEFT_RIGHT', engine: FlowLayoutEngine = 'dagre'): Promise<{ positions: FlowPositions }> {
  const { nodeIds, edges } = flowLayoutGraph(steps)
  const positions = engine === 'dagre' ? layoutWithDagre(nodeIds, edges, direction) : await layoutWithElk(nodeIds, edges, direction)
  return { positions }
}

/**
 * Mode-aware position resolution, replacing the old per-step "stored `position` always wins" merge.
 * While `autolayoutEnabled`, every step's position comes from
 * `autolayoutPositions` — a fresh `computeFlowAutolayout()` result — with no
 * per-step override, so a drag or any other stale value never survives the
 * next recompute. While not, `autolayoutPositions` is never consulted
 * (callers shouldn't even run a layout engine to produce one when the mode is
 * off — see call sites): every step's position is its own stored `position`,
 * falling back to `{0, 0}` only for a step that somehow has none.
 */
export function mergeStepPositions(steps: FlowStep[], autolayoutEnabled: boolean, autolayoutPositions?: FlowPositions): FlowPositions {
  const merged: FlowPositions = {}
  for (const step of steps) {
    merged[step.id] = autolayoutEnabled
      ? autolayoutPositions?.[step.id] ?? { x: 0, y: 0 }
      : step.position ?? { x: 0, y: 0 }
  }
  return merged
}

/**
 * Deterministic placement for a new, unconnected step added via the toolbar
 * a new row below the whole flow's
 * existing bounding box, left-aligned to it, so it never lands on top of an
 * existing node the way relying on the layout engine to place a second
 * disconnected root did. `resolvedPositions` should be the canvas's merged
 * (stored-or-autolayout) positions, not just steps' stored `position`, so a
 * never-dragged step still contributes a real coordinate. An empty flow has
 * nothing to avoid, so the new step starts at the origin.
 *
 * The new row starts a full `FLOW_NODE_HEIGHT` below the lowest existing
 * step's own (top-left) `position`, plus the gap — not just the gap alone —
 * since `position` is a node's top-left corner, not its bottom edge; adding
 * only the gap left rows just a few pixels apart (bug found by inspecting a
 * real Flow's diagram, see flow-canvas-fix-overlaps change).
 */
export function nextRowPosition(steps: FlowStep[], resolvedPositions: FlowPositions): { x: number; y: number } {
  if (steps.length === 0) return { x: 0, y: 0 }
  let minX = Infinity
  let maxY = -Infinity
  for (const step of steps) {
    const position = resolvedPositions[step.id] ?? { x: 0, y: 0 }
    minX = Math.min(minX, position.x)
    maxY = Math.max(maxY, position.y)
  }
  return { x: minX, y: maxY + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP }
}

/**
 * One layout-step past a source position — transposed for `LAYOUT_TOP_DOWN`
 * vs `LAYOUT_LEFT_RIGHT` — so a manually-added connected step (or its
 * add-next placeholder) lands in the same slot autolayout would have put it
 * in. This is the *naive* single-offset calculation,
 * unaware of any other node that might already occupy that slot — use
 * `resolveConnectedPosition` below for the collision-checked version real
 * call sites want.
 */
export function nextConnectedPosition(sourcePosition: { x: number; y: number }, direction: FlowLayoutDirection): { x: number; y: number } {
  return direction === 'LAYOUT_TOP_DOWN'
    ? { x: sourcePosition.x, y: sourcePosition.y + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP }
    : { x: sourcePosition.x + FLOW_NODE_WIDTH + FLOW_LAYER_GAP, y: sourcePosition.y }
}

/** True if two `FLOW_NODE_WIDTH` x `FLOW_NODE_HEIGHT` boxes anchored at their top-left `position` overlap. */
function positionsOverlap(a: { x: number; y: number }, b: { x: number; y: number }): boolean {
  return Math.abs(a.x - b.x) < FLOW_NODE_WIDTH && Math.abs(a.y - b.y) < FLOW_NODE_HEIGHT
}

/**
 * `nextConnectedPosition`, nudged further along the perpendicular axis (down
 * for `LAYOUT_LEFT_RIGHT`, right for `LAYOUT_TOP_DOWN`) in `FLOW_NODE_HEIGHT`/
 * `FLOW_NODE_WIDTH` + gap steps until it doesn't overlap any position in
 * `occupied`. The naive one-offset calculation only knows about its own
 * source — it has no idea a *sibling* of that source already has a deep
 * subtree autolayout placed at exactly that slot (e.g. two children of the
 * same step, one already connected further down the diagram) — so a
 * childless step's placeholder, or a just-added connected step, could
 * otherwise land on top of an already-real node (bug found by inspecting a
 * real Flow's diagram, see flow-canvas-fix-overlaps change). `occupied`
 * should include every other real step's resolved position and, when
 * resolving more than one placeholder in the same pass, every
 * already-resolved placeholder position too, so two placeholders never stack
 * on each other either.
 */
export function resolveConnectedPosition(sourcePosition: { x: number; y: number }, direction: FlowLayoutDirection, occupied: { x: number; y: number }[]): { x: number; y: number } {
  let position = nextConnectedPosition(sourcePosition, direction)
  while (occupied.some((candidate) => positionsOverlap(candidate, position))) {
    position = direction === 'LAYOUT_TOP_DOWN'
      ? { x: position.x + FLOW_NODE_WIDTH + FLOW_LAYER_GAP, y: position.y }
      : { x: position.x, y: position.y + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP }
  }
  return position
}

/** Builds render-ready React Flow nodes/edges from `steps` and a final (already-merged) position map. `refStatus` (a step id -> live status map, from `FlowEntity.refStatus`) is optional — omitted entirely by callers with no such data, e.g. a not-yet-saved draft. Every connection renders as a direct curve computed live at render time (`FlowEdges.tsx`'s `getSmoothStepPath`) — there is no more routing/staleness concept to thread through here. `onOpenTransitionModal`, when given, is threaded into each labeled edge's `data` so `FlowTransitionEdge`'s own label click can reopen that transition's edit modal — the editable canvas passes one, the read-only canvas (no such modal) omits it. */
export function buildFlowNodesAndEdges(steps: FlowStep[], positions: FlowPositions, refStatus?: Record<string, FlowStepRefStatus>, onOpenTransitionModal?: (sourceId: string, targetId: string, label?: string) => void): FlowLayout {
  const nodes: FlowNode[] = flattenForestOrder(buildForest(steps)).map((step) => ({
    id: step.id,
    type: flowNodeKindOf(step),
    position: positions[step.id] ?? { x: 0, y: 0 },
    // Matches every card kind's fixed `CARD_STYLE_BASE` size (`FlowNodes.tsx`)
    // exactly, so `fitView` (called right after nodes are set, in
    // `FlowGraph.tsx`/`FlowCanvasEditor.tsx`) can compute correct bounds
    // immediately instead of waiting for React Flow's async post-render
    // ResizeObserver measurement — without this, that first `fitView` ran
    // against unmeasured (zero-size) nodes and produced a visibly
    // off-center/shifted diagram on initial load.
    width: FLOW_NODE_WIDTH,
    height: FLOW_NODE_HEIGHT,
    data: { step, refStatus: refStatus?.[step.id] },
  }))

  const edges: Edge[] = edgesOf(steps).map(({ sourceId, targetId }) => {
    const source = steps.find((step) => step.id === sourceId)!
    const label = transitionLabel(source, targetId)
    return {
      id: `${sourceId}->${targetId}`,
      source: sourceId,
      target: targetId,
      // `'flow-transition'` (`FlowEdges.tsx`'s `FLOW_EDGE_TYPES`) replaces
      // the default `smoothstep` type's non-wrapping SVG label with an HTML
      // label that wraps onto multiple lines — same path geometry/marker, only the label's DOM changes.
      type: 'flow-transition',
      label,
      // Bigger than `@xyflow/react`'s default 12.5x12.5 marker — at that
      // size the arrowhead reads as barely more than the connection
      // handle dot it sits next to, undermining the one thing a marker
      // exists to show (which end is the target).
      markerEnd: { type: MarkerType.ArrowClosed, width: 22, height: 22 },
      data: onOpenTransitionModal ? { onOpenTransitionModal: () => onOpenTransitionModal(sourceId, targetId, label) } : undefined,
    }
  })

  return { nodes, edges }
}
