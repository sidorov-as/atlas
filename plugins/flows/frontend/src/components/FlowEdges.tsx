// Custom transition-edge rendering for Flow diagrams.
// `@xyflow/react`'s default `smoothstep` edge type renders its label through
// the library's built-in `EdgeText`, which emits a single SVG `<text>` node —
// SVG text never wraps, so a long transition label just overflows past the
// edge. `FlowTransitionEdge` keeps the same path geometry and arrowhead
// (`getSmoothStepPath()` via `<BaseEdge>`) but renders the label as an HTML
// `<div>` through `<EdgeLabelRenderer>`, xyflow's HTML-overlay escape hatch,
// so ordinary CSS wrapping (and, past a cap, `-webkit-line-clamp`) applies
//
// Every connection is always a direct `getSmoothStepPath` curve between its
// two nodes' live handle positions now — the ELK-derived, already-translated
// `data.routing` polyline branch this used to have is deleted along with the pipeline that produced it;
// there is no more routing/staleness concept for an edge to carry.
import { memo } from 'react'
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, type EdgeProps, type EdgeTypes } from '@xyflow/react'
import { Text, Tooltip } from '@gravity-ui/uikit'
import { FLOW_EDGE_LABEL_MAX_WIDTH, FLOW_NODE_HEIGHT } from '../lib/flowLayout'

const LABEL_LINE_HEIGHT = 16
const LABEL_VERTICAL_PADDING = 12 // 6px top + 6px bottom, matches the box's own `padding` below
const LABEL_BORDER_WIDTH = 2 // 1px top + 1px bottom
/** How many lines fit within the label box's own capped height before it clamps with an ellipsis (full text via `Tooltip`) instead of growing any taller. */
const LABEL_MAX_LINES = Math.max(1, Math.floor((FLOW_NODE_HEIGHT - LABEL_VERTICAL_PADDING - LABEL_BORDER_WIDTH) / LABEL_LINE_HEIGHT))

export interface FlowEdgeData extends Record<string, unknown> {
  /** Reopens the transition-edit modal for this connection — set by `buildFlowNodesAndEdges`'s caller (the editable canvas only; the read-only canvas passes none, so its label stays click-inert). `EdgeLabelRenderer` portals the label outside the edge's own `<g>`, so `pointerEvents: 'all'` here (for hover/click on the label itself) would otherwise swallow the click before it reaches React Flow's own `onEdgeClick` — this callback is that click's own path to the same modal; both remain valid ways to open it. */
  onOpenTransitionModal?: () => void
}

function FlowTransitionEdgeComponent({ id, sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, label, markerEnd, style, data }: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })
  const onOpenTransitionModal = (data as FlowEdgeData | undefined)?.onOpenTransitionModal

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />
      {typeof label === 'string' && label && (
        <EdgeLabelRenderer>
          <div
            onClick={onOpenTransitionModal && ((event) => { event.stopPropagation(); onOpenTransitionModal() })}
            className="nodrag nopan"
            // Duplicates the tooltip's own text as an `aria-label` (same
            // reasoning as `FlowNodes.tsx`'s chip/title tooltips): conveys it
            // to assistive tech, and makes the full label queryable in tests
            // without depending on `Tooltip`'s hover-triggered, portal-
            // rendered content.
            aria-label={label}
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              // Grows with the text, capped at `FLOW_EDGE_LABEL_MAX_WIDTH` x
              // `FLOW_NODE_HEIGHT` — the same footprint the layout engines
              // already reserve inter-layer space for
              // (`estimateLabelSize` in `flowLayout.ts`) — not a fixed size,
              // so a short label (e.g. "yes") still renders as a small pill.
              maxWidth: FLOW_EDGE_LABEL_MAX_WIDTH,
              maxHeight: FLOW_NODE_HEIGHT,
              boxSizing: 'border-box',
              overflow: 'hidden',
              padding: '6px 10px',
              // Only the editable canvas wires an `onOpenTransitionModal`
              // callback — the read-only canvas's
              // label stays click-inert, same as before this rewrite.
              pointerEvents: onOpenTransitionModal ? 'all' : 'none',
              cursor: onOpenTransitionModal ? 'pointer' : undefined,
              background: 'var(--g-color-base-background)',
              border: '1px solid var(--g-color-line-generic)',
              borderRadius: 6,
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
            }}
          >
            <Tooltip content={label} placement="top">
              <Text
                variant="caption-2"
                style={{
                  display: '-webkit-box',
                  WebkitLineClamp: LABEL_MAX_LINES,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  whiteSpace: 'normal',
                  wordBreak: 'break-word',
                  textAlign: 'center',
                }}
              >
                {label}
              </Text>
            </Tooltip>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
export const FlowTransitionEdge = memo(FlowTransitionEdgeComponent)

/** Shared `edgeTypes` map, consumed by both the read-only detail-page canvas and the editable canvas. */
export const FLOW_EDGE_TYPES: EdgeTypes = {
  'flow-transition': FlowTransitionEdge,
}
