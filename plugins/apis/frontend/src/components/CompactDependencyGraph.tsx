// Shared graph shell for the compact dependency graphs on the Endpoint and
// Operation Overview tabs — owns the chrome that was
// byte-for-byte duplicated between `EndpointConsumersGraph` and
// `OperationConsumersGraph`: loading/error/empty states, the `<ReactFlow>`
// wrapper with its standard read-only configuration, the overflow indicator,
// and the full-screen `Dialog`. Each caller keeps its own `buildGraph()`
// layout math and node type components — those are genuinely different
// shapes (single ring vs. role-split arcs), so only the surrounding chrome
// is unified.
import { useId, useState } from 'react'
import {
  Background,
  Controls,
  Panel,
  ReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type NodeTypes,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowsExpand } from '@gravity-ui/icons'
import { Alert, Button, Dialog, Icon, Label, Skeleton, Text } from '@gravity-ui/uikit'
import { errorMessage } from 'frontend/lib/api'
import './CompactDependencyGraph.css'

const GRAPH_HEIGHT = 480

export function CompactDependencyGraph({
  title,
  nodes,
  edges,
  fullscreenNodes,
  fullscreenEdges,
  nodeTypes,
  onNodeClick,
  isLoading,
  error,
  errorFallback,
  onRetry,
  emptyMessage,
  canLinkService,
  onLinkService,
  overflowLabel,
  fillHeight,
}: {
  /** Caption shown in the full-screen dialog's header. */
  title: string
  /** Capped node/edge pair rendered inline (the compact, `MAX_GRAPH_*`-limited view). */
  nodes: Node[]
  edges: Edge[]
  /** Uncapped node/edge pair rendered in the full-screen dialog — same already-loaded data, no cap. */
  fullscreenNodes: Node[]
  fullscreenEdges: Edge[]
  nodeTypes: NodeTypes
  onNodeClick: NodeMouseHandler<Node>
  isLoading: boolean
  error: Error | null
  errorFallback: string
  onRetry: () => void
  emptyMessage: string
  canLinkService?: boolean
  onLinkService?: () => void
  /** Text for the compact-view overflow indicator (e.g. "12 of 15 services shown") — omitted when nothing is capped. */
  overflowLabel?: string
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

  return (
    <div style={{ ...(fillHeight ? { height: '100%', minHeight: GRAPH_HEIGHT } : { height: GRAPH_HEIGHT }), border: '1px solid var(--g-color-line-generic)', borderRadius: 8 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        onNodeClick={onNodeClick}
        fitView
        minZoom={0.2}
      >
        <Background />
        <Controls showInteractive={false} />
        <Panel position="top-right" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {overflowLabel && <Label>{overflowLabel}</Label>}
          <Button size="s" onClick={() => setFullscreenOpen(true)}>
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
        onClose={() => { setFullscreenOpen(false); setFullscreenReady(false) }}
        onTransitionInComplete={() => setFullscreenReady(true)}
        hasCloseButton
        aria-labelledby={titleId}
        modalClassName="compact-dependency-graph-modal"
        className="compact-dependency-graph-dialog"
      >
        <Dialog.Header caption={title} id={titleId} />
        <Dialog.Body className="compact-dependency-graph-dialog-body">
          <div>
            {fullscreenReady && (
              <ReactFlow
                nodes={fullscreenNodes}
                edges={fullscreenEdges}
                nodeTypes={nodeTypes}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable
                onNodeClick={onNodeClick}
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
