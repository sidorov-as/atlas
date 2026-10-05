// Shared graph shell for the dependency graphs on the Endpoint and Operation
// Overview tabs — owns the chrome that would otherwise be duplicated between
// `EndpointConsumersGraph` and `OperationConsumersGraph`: loading/error/empty
// states, the read-only inline `<ReactFlow>`, the "+N more" node handling, and
// the full-screen `Dialog` with its grouping choice, Auto-layout, dragging,
// server-side search and the click on a group node. Each caller keeps its own
// graph builders and node type components — those are genuinely different
// shapes (single ring vs. role-split arcs), so only the surrounding chrome is
// unified.
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  Background,
  Controls,
  Panel,
  ReactFlow,
  useNodesState,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowsExpand, Gear, MagicWand } from '@gravity-ui/icons'
import { Alert, Button, Dialog, DropdownMenu, Icon, Loader, Skeleton, Text, TextInput, Tooltip } from '@gravity-ui/uikit'
import { errorMessage } from 'frontend/lib/api'
import { exportGraphImage, GraphExportControl, type GraphExportOptions } from './GraphExportControl'
import { GROUP_NODE_TYPE } from './GroupNode'
import { resolveGraphGrouping, writeGraphGrouping, type GraphGroupingId } from '../lib/graphGrouping'
import type { ConsumerGroupBy, OperationRole } from '../lib/types'
import './CompactDependencyGraph.css'

const GRAPH_HEIGHT = 480
const SEARCH_DEBOUNCE_MS = 300

const GROUPING_LABELS: Record<GraphGroupingId, string> = { none: 'No grouping', team: 'Group by: Team', system: 'Group by: System' }

/** One group of an Operation side (`role`) or of an Endpoint graph (no role). */
export interface GroupRef {
  groupId: string
  role?: OperationRole
}

export function groupKey(ref: GroupRef): string {
  return `${ref.role ?? ''}|${ref.groupId}`
}

/** The group a "+N more" node belongs to, so it can open Linked Services narrowed to that group. */
export interface MoreGroup {
  groupBy: ConsumerGroupBy
  groupId: string
  name: string
}

/** What a caller's full-screen builder returns. */
export interface FullscreenGraph {
  nodes: Node[]
  edges: Edge[]
  /** The node every Service connects to — never dimmed or highlighted. */
  centerId: string
  /** Drawn nodes that match the active search. */
  matchIds: ReadonlySet<string>
  /** Total linked Services matching the active search, once the server answered; `null` before that. */
  matchCount: number | null
}

/** What the full-screen builder draws from, besides the data set it already holds. */
export interface GraphView<C, M> {
  /** Trimmed search text; empty when no search is active. */
  query: string
  /** Ungrouped graph: the server's answer for the latest settled search, kept while a newer one loads. */
  result: C | null
  /** The active grouping; `null` draws every Service individually. */
  groupBy: ConsumerGroupBy | null
  /** Grouped graph: the unsearched grouped response (groups plus the Services outside them). */
  grouped: C | null
  /** Grouped graph: the grouped response for the active search text, when one is active and has settled. */
  groupedSearch: C | null
  /** Keys (`groupKey`) of the expanded groups. */
  expanded: ReadonlySet<string>
  /** First page of the members of each group that has been loaded, by `groupKey`. */
  members: ReadonlyMap<string, M>
}

/** Keep the position of every node that is already on screen, unless `reset` asks for the layout's positions. */
export function mergeNodePositions(previous: Node[], next: Node[], reset: boolean): Node[] {
  if (reset) return next
  const positions = new Map(previous.map((node) => [node.id, node.position]))
  return next.map((node) => ({ ...node, position: positions.get(node.id) ?? node.position }))
}

export function CompactDependencyGraph<C, M>({
  title,
  nodes,
  edges,
  buildFullscreenGraph,
  searchConsumers,
  loadGrouped,
  loadGroupMembers,
  totalCount,
  onOpenLinkedServices,
  nodeTypes,
  onNodeClick,
  exportName,
  isLoading,
  error,
  errorFallback,
  onRetry,
  emptyMessage,
  canLinkService,
  onLinkService,
  fillHeight,
}: {
  /** Caption shown in the full-screen dialog's header. */
  title: string
  /** Capped node/edge pair rendered inline; a `more` node stands in for the Services not drawn. */
  nodes: Node[]
  edges: Edge[]
  /** Builds the full-screen graph (always the Columns layout) for the active view (search, grouping, expansion). Must be stable per data set (memoize it). */
  buildFullscreenGraph: (view: GraphView<C, M>) => FullscreenGraph
  /** Asks the server for the Services matching `query`, across every linked Service. */
  searchConsumers: (query: string, signal: AbortSignal) => Promise<C>
  /** Asks the server for the groups of `groupBy` (with the Services outside them), narrowed by `query` — empty for the whole set. */
  loadGrouped: (groupBy: ConsumerGroupBy, query: string, signal: AbortSignal) => Promise<C>
  /** Asks the server for the first page of one group's members. */
  loadGroupMembers: (groupBy: ConsumerGroupBy, group: GroupRef, signal: AbortSignal) => Promise<M>
  /** Total linked Services — decides whether grouping is on by default. */
  totalCount: number
  /** The full-screen "+N more" node: open the Linked Services tab, pre-filled with the active search text (empty when none) and, for a group's own node, narrowed to that group. */
  onOpenLinkedServices: (search: string, group?: MoreGroup) => void
  nodeTypes: NodeTypes
  onNodeClick: NodeMouseHandler<Node>
  /** File name (without extension) of the full-screen image export. */
  exportName: string
  isLoading: boolean
  error: Error | null
  errorFallback: string
  onRetry: () => void
  emptyMessage: string
  canLinkService?: boolean
  onLinkService?: () => void
  /** Stretch to the parent's height (via a `flex: 1` wrapper, e.g. EndpointOverviewTab's right column) instead of the fixed `GRAPH_HEIGHT` — keeps the graph's bottom edge level with a sibling card that can grow taller than `GRAPH_HEIGHT` (e.g. a long Documentation card pushing Details down). `GRAPH_HEIGHT` remains the floor via `minHeight`. */
  fillHeight?: boolean
}) {
  const titleId = useId()
  const [fullscreenOpen, setFullscreenOpen] = useState(false)
  // `ReactFlow`'s `fitView` only runs once, against whatever size its
  // container has at mount time — mounting it while the Dialog's open
  // transition is still animating measures a not-yet-final container and
  // leaves the graph tiny and mis-fit in a corner. Deferring the mount until
  // the transition completes (`onTransitionInComplete`) ensures `fitView`
  // sees the dialog's final, settled size.
  const [fullscreenReady, setFullscreenReady] = useState(false)

  // Bumped by Auto-layout, by opening and by every change of the drawn Services: the next build then replaces
  // every position instead of keeping the dragged ones.
  const [layoutRevision, setLayoutRevision] = useState(0)
  const appliedRevision = useRef(-1)

  const [queryText, setQueryText] = useState('')
  const query = queryText.trim()
  const [searchState, setSearchState] = useState<{ query: string; result: C | null; failed: boolean }>({ query: '', result: null, failed: false })
  const searchSettled = searchState.query === query

  const [grouping, setGrouping] = useState<GraphGroupingId>('none')
  const groupBy = grouping === 'none' ? null : grouping
  const [baseGrouped, setBaseGrouped] = useState<{ groupBy: ConsumerGroupBy | null; result: C | null; failed: boolean }>({ groupBy: null, result: null, failed: false })
  const [groupedSearch, setGroupedSearch] = useState<{ groupBy: ConsumerGroupBy | null; query: string; result: C | null; failed: boolean }>({ groupBy: null, query: '', result: null, failed: false })
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set())
  const [members, setMembers] = useState<ReadonlyMap<string, M>>(new Map())
  const [memberFailed, setMemberFailed] = useState(false)
  const memberRequests = useRef(new Set<AbortController>())

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node>([])
  const canvasRef = useRef<HTMLDivElement>(null)
  const [exporting, setExporting] = useState(false)

  function cancelMemberRequests() {
    for (const controller of memberRequests.current) controller.abort()
    memberRequests.current.clear()
  }

  function collapseAll() {
    setExpanded(new Set())
    setMemberFailed(false)
  }

  function openFullscreen() {
    setGrouping(resolveGraphGrouping(totalCount))
    setLayoutRevision((revision) => revision + 1)
    setFullscreenOpen(true)
  }

  function closeFullscreen() {
    setFullscreenOpen(false)
    setFullscreenReady(false)
    setQueryText('')
    setSearchState({ query: '', result: null, failed: false })
    setBaseGrouped({ groupBy: null, result: null, failed: false })
    setGroupedSearch({ groupBy: null, query: '', result: null, failed: false })
    cancelMemberRequests()
    collapseAll()
    setMembers(new Map())
    setFlowNodes([])
  }

  async function handleExport(options: GraphExportOptions) {
    const element = canvasRef.current
    if (!element) return
    setExporting(true)
    try {
      await exportGraphImage(element, options, exportName)
    } finally {
      setExporting(false)
    }
  }

  function chooseGrouping(next: GraphGroupingId) {
    if (next === grouping) return
    setGrouping(next)
    writeGraphGrouping(next)
    cancelMemberRequests()
    collapseAll()
    setMembers(new Map())
    setLayoutRevision((revision) => revision + 1)
  }

  // A group expands and collapses in place. Its first page is requested on the
  // first expansion and cached; the layout is rebuilt each time the set of
  // drawn Services changes so nothing overlaps.
  function toggleGroup(ref: GroupRef) {
    const key = groupKey(ref)
    if (expanded.has(key)) {
      setExpanded((previous) => { const next = new Set(previous); next.delete(key); return next })
      setLayoutRevision((revision) => revision + 1)
      return
    }
    setExpanded((previous) => new Set(previous).add(key))
    setMemberFailed(false)
    if (members.has(key) || !groupBy) {
      setLayoutRevision((revision) => revision + 1)
      return
    }
    const controller = new AbortController()
    memberRequests.current.add(controller)
    loadGroupMembers(groupBy, ref, controller.signal).then(
      (page) => {
        if (controller.signal.aborted) return
        memberRequests.current.delete(controller)
        setMembers((previous) => new Map(previous).set(key, page))
        setLayoutRevision((revision) => revision + 1)
      },
      () => {
        if (controller.signal.aborted) return
        memberRequests.current.delete(controller)
        setExpanded((previous) => { const next = new Set(previous); next.delete(key); return next })
        setMemberFailed(true)
      },
    )
  }

  // Changing the search text collapses every group (their cached pages stay) and, if any was open, refits the view to the smaller graph.
  const hadExpanded = useRef(false)
  hadExpanded.current = expanded.size > 0
  useEffect(() => {
    if (hadExpanded.current) setLayoutRevision((revision) => revision + 1)
    collapseAll()
  }, [query])

  // Grouped graph: the unsearched groups, requested when the dialog opens or the grouping changes.
  useEffect(() => {
    if (!fullscreenOpen || !groupBy) return
    const controller = new AbortController()
    setBaseGrouped({ groupBy, result: null, failed: false })
    loadGrouped(groupBy, '', controller.signal).then(
      (result) => { if (!controller.signal.aborted) setBaseGrouped({ groupBy, result, failed: false }) },
      () => { if (!controller.signal.aborted) setBaseGrouped({ groupBy, result: null, failed: true }) },
    )
    return () => controller.abort()
  }, [fullscreenOpen, groupBy, loadGrouped])

  // Grouped graph: the groups narrowed by the search, debounced like the ungrouped search.
  useEffect(() => {
    if (!fullscreenOpen || !groupBy) return
    if (!query) {
      setGroupedSearch({ groupBy, query: '', result: null, failed: false })
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(() => {
      loadGrouped(groupBy, query, controller.signal).then(
        (result) => { if (!controller.signal.aborted) setGroupedSearch({ groupBy, query, result, failed: false }) },
        () => { if (!controller.signal.aborted) setGroupedSearch((previous) => ({ ...previous, groupBy, query, failed: true })) },
      )
    }, SEARCH_DEBOUNCE_MS)
    return () => { clearTimeout(timer); controller.abort() }
  }, [fullscreenOpen, groupBy, query, loadGrouped])

  // Debounced, cancellable server search. The previous result stays on screen
  // while a newer one loads.
  useEffect(() => {
    if (!fullscreenOpen || groupBy) return
    if (!query) {
      setSearchState({ query: '', result: null, failed: false })
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(() => {
      searchConsumers(query, controller.signal).then(
        (result) => { if (!controller.signal.aborted) setSearchState({ query, result, failed: false }) },
        () => { if (!controller.signal.aborted) setSearchState((previous) => ({ ...previous, query, failed: true })) },
      )
    }, SEARCH_DEBOUNCE_MS)
    return () => { clearTimeout(timer); controller.abort() }
  }, [query, fullscreenOpen, groupBy, searchConsumers])

  const groupedReady = !groupBy || (baseGrouped.groupBy === groupBy && baseGrouped.result !== null)
  const groupedSearchSettled = !groupBy || !query || (groupedSearch.groupBy === groupBy && groupedSearch.query === query)
  const groupedSearchFailed = Boolean(groupBy && query && groupedSearch.groupBy === groupBy && groupedSearch.query === query && groupedSearch.failed)
  const activeSearchSettled = groupBy ? groupedSearchSettled : searchSettled
  const activeSearchFailed = groupBy ? groupedSearchFailed : searchState.failed

  const fullscreenGraph = useMemo(
    () => {
      if (!fullscreenReady || !groupedReady) return null
      return buildFullscreenGraph({
        query,
        result: groupBy ? null : searchState.result,
        groupBy,
        grouped: groupBy ? baseGrouped.result : null,
        groupedSearch: groupBy && query && groupedSearch.groupBy === groupBy ? groupedSearch.result : null,
        expanded,
        members,
      })
    },
    [fullscreenReady, groupedReady, buildFullscreenGraph, query, groupBy, searchState.result, baseGrouped.result, groupedSearch.groupBy, groupedSearch.result, expanded, members],
  )

  useEffect(() => {
    if (!fullscreenGraph) {
      setFlowNodes([])
      return
    }
    const reset = appliedRevision.current !== layoutRevision
    appliedRevision.current = layoutRevision
    const decorated = fullscreenGraph.nodes.map((node): Node => {
      const isGroup = node.type === GROUP_NODE_TYPE
      const isService = node.id !== fullscreenGraph.centerId && node.type !== 'more' && !isGroup
      // A group is dimmed by its own data (no match inside it), never highlighted as a match.
      const groupClass = isGroup && (node.data as { dimmed?: boolean }).dimmed ? 'dependency-graph-node-dimmed' : undefined
      const searchClass = query && isService ? (fullscreenGraph.matchIds.has(node.id) ? 'dependency-graph-node-match' : 'dependency-graph-node-dimmed') : groupClass
      return { ...node, draggable: true, className: searchClass }
    })
    setFlowNodes((previous) => mergeNodePositions(previous, decorated, reset))
  }, [fullscreenGraph, layoutRevision, query, setFlowNodes])

  // The canvas is mounted for a fresh view only once the groups it draws are here.
  const groupsFailed = Boolean(groupBy && baseGrouped.groupBy === groupBy && baseGrouped.failed)

  // A `more` node in the compact graph opens the full-screen view; every other
  // node type is the caller's.
  const handleInlineNodeClick: NodeMouseHandler<Node> = (event, node) => {
    if (node.type === 'more') {
      openFullscreen()
      return
    }
    onNodeClick(event, node)
  }

  const handleFullscreenNodeClick: NodeMouseHandler<Node> = (event, node) => {
    if (node.type === 'more') {
      onOpenLinkedServices(query, (node.data as { group?: MoreGroup }).group)
      // The Linked Services tab opens on the same page, so the dialog would otherwise stay on top of it.
      closeFullscreen()
      return
    }
    if (node.type === GROUP_NODE_TYPE) {
      const { groupId, role } = node.data as { groupId: string; role?: OperationRole }
      toggleGroup({ groupId, role })
      return
    }
    onNodeClick(event, node)
  }

  if (error) {
    return (
      <Alert
        theme="danger"
        message={errorMessage(error, errorFallback)}
        actions={<Alert.Action onClick={onRetry}>Retry</Alert.Action>}
      />
    )
  }

  if (isLoading && nodes.length === 0) {
    return <Skeleton style={fillHeight ? { height: '100%', minHeight: GRAPH_HEIGHT, borderRadius: 8 } : { height: GRAPH_HEIGHT, borderRadius: 8 }} />
  }

  if (nodes.length <= 1) {
    return (
      <div
        style={{
          ...(fillHeight ? { height: '100%', minHeight: 200 } : { height: 200 }),
          border: '1px dashed var(--g-color-line-generic)',
          borderRadius: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
        }}
      >
        <Text color="secondary">{emptyMessage}</Text>
        {canLinkService && <Button view="action" onClick={onLinkService}>Link service</Button>}
      </div>
    )
  }

  const noMatches = Boolean(query) && activeSearchSettled && !activeSearchFailed && fullscreenGraph?.matchCount === 0

  return (
    <div style={{ ...(fillHeight ? { height: '100%', minHeight: GRAPH_HEIGHT } : { height: GRAPH_HEIGHT }), border: '1px solid var(--g-color-line-generic)', borderRadius: 8 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        onNodeClick={handleInlineNodeClick}
        fitView
        minZoom={0.2}
      >
        <Background />
        <Controls showInteractive={false} />
        <Panel position="top-right" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Button size="s" onClick={openFullscreen}>
            <Icon data={ArrowsExpand} size={14} />
            Full screen
          </Button>
        </Panel>
      </ReactFlow>

      {/* Near-viewport sizing via CSS custom properties set through
          `modalClassName`/`className` — `Dialog`'s built-in `maxWidth` tops
          out at 'l', with no fullscreen tier (confirmed against
          `Dialog.d.ts`). */}
      <Dialog
        open={fullscreenOpen}
        onClose={closeFullscreen}
        onTransitionInComplete={() => setFullscreenReady(true)}
        hasCloseButton
        aria-labelledby={titleId}
        modalClassName="compact-dependency-graph-modal"
        className="compact-dependency-graph-dialog"
      >
        <Dialog.Header caption={title} id={titleId} />
        <Dialog.Body className="compact-dependency-graph-dialog-body">
          <div className="compact-dependency-graph-toolbar">
            <TextInput
              className="compact-dependency-graph-search"
              placeholder="Search services"
              aria-label="Search services"
              value={queryText}
              onUpdate={setQueryText}
              hasClear
              endContent={query && !activeSearchSettled && !activeSearchFailed ? <Loader size="s" /> : undefined}
            />
            {noMatches && <Text color="secondary">No matching services</Text>}
            {activeSearchFailed && query && <Text color="danger">Search failed</Text>}
            {groupsFailed && <Text color="danger">Failed to load groups</Text>}
            {memberFailed && <Text color="danger">Failed to load the group's services</Text>}
            <div className="compact-dependency-graph-toolbar-actions">
              <Tooltip content="Auto-layout" placement="bottom">
                <Button view="raised" aria-label="Auto-layout" onClick={() => setLayoutRevision((revision) => revision + 1)}>
                  <Icon data={MagicWand} />
                </Button>
              </Tooltip>
              <DropdownMenu
                renderSwitcher={(props) => (
                  <Tooltip content="Graph settings" placement="bottom">
                    <Button {...props} view="raised" aria-label="Graph settings">
                      <Icon data={Gear} />
                    </Button>
                  </Tooltip>
                )}
                items={(Object.keys(GROUPING_LABELS) as GraphGroupingId[]).map((id) => ({
                  text: GROUPING_LABELS[id],
                  selected: id === grouping,
                  action: () => chooseGrouping(id),
                }))}
              />
              <GraphExportControl exporting={exporting} onExport={handleExport} />
            </div>
          </div>
          <div className="compact-dependency-graph-canvas" ref={canvasRef}>
            {/* Mounted once there are nodes to fit, and re-keyed by every
                re-layout so `fitView` frames the new positions. */}
            {fullscreenReady && !groupedReady && !groupsFailed && <Loader size="l" />}
            {fullscreenReady && flowNodes.length > 0 && (
              <ReactFlow
                key={layoutRevision}
                nodes={flowNodes}
                edges={fullscreenGraph?.edges ?? []}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                nodesDraggable
                nodesConnectable={false}
                elementsSelectable
                onNodeClick={handleFullscreenNodeClick}
                fitView
                minZoom={0.2}
              >
                <Background />
                <Controls showInteractive={false} />
              </ReactFlow>
            )}
          </div>
        </Dialog.Body>
      </Dialog>
    </div>
  )
}
