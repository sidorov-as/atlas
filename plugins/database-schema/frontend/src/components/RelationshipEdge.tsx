// ChartDB-style cardinality badges ("1"/"N") at each end of a relation edge
// (docs.chartdb.io/docs/diagrams/relationships: "ChartDB will display
// cardinality indicators (e.g., 1, N) on the relationship lines"). Wraps the
// same `getSmoothStepPath` the built-in `smoothstep` edge type uses — same
// default `borderRadius` (5), so the line itself looks identical to before —
// and adds two small badges via `EdgeLabelRenderer`, offset past each
// handle's anchor point so they sit in the gap between tables rather than on
// top of a border.
import { BaseEdge, EdgeLabelRenderer, Position, getSmoothStepPath, type Edge, type EdgeProps } from '@xyflow/react'
import type { ParsedSchemaCardinality } from '../lib/databaseSchemaApi'

export interface RelationshipEdgeData extends Record<string, unknown> {
  cardinality: ParsedSchemaCardinality
}

export type RelationshipFlowEdge = Edge<RelationshipEdgeData, 'relationship'>

const BADGE_OFFSET = 12

function offsetAlong(x: number, y: number, position: Position, distance: number): { x: number, y: number } {
  switch (position) {
    case Position.Left: return { x: x - distance, y }
    case Position.Right: return { x: x + distance, y }
    case Position.Top: return { x, y: y - distance }
    case Position.Bottom: return { x, y: y + distance }
  }
}

function CardinalityBadge({ x, y, label }: { x: number, y: number, label: string }) {
  return (
    <div
      className="nodrag nopan"
      style={{
        position: 'absolute',
        transform: `translate(-50%, -50%) translate(${x}px, ${y}px)`,
        width: 16,
        height: 16,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '50%',
        border: '1px solid var(--g-color-line-generic)',
        background: 'var(--g-color-base-background)',
        color: 'var(--g-color-text-secondary)',
        fontSize: 9,
        fontWeight: 600,
        lineHeight: 1,
        pointerEvents: 'none',
      }}
    >
      {label}
    </div>
  )
}

export function RelationshipEdge({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, style, data }: EdgeProps<RelationshipFlowEdge>) {
  const [path] = getSmoothStepPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })
  const cardinality = data?.cardinality ?? 'many_to_one'
  // The FK-holding table (edge source) is the "many" side in a many-to-one
  // relation; the referenced table (edge target) is always the "one" side.
  const sourceLabel = cardinality === 'one_to_one' ? '1' : 'N'
  const sourceBadge = offsetAlong(sourceX, sourceY, sourcePosition, BADGE_OFFSET)
  const targetBadge = offsetAlong(targetX, targetY, targetPosition, BADGE_OFFSET)
  return (
    <>
      <BaseEdge path={path} style={style} />
      <EdgeLabelRenderer>
        <CardinalityBadge x={sourceBadge.x} y={sourceBadge.y} label={sourceLabel} />
        <CardinalityBadge x={targetBadge.x} y={targetBadge.y} label="1" />
      </EdgeLabelRenderer>
    </>
  )
}
