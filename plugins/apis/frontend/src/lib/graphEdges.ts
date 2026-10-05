// Edges of the full-screen graphs: rounded step edges that leave and enter
// nodes on their left or right side, like the Flow and ER diagrams. The inline
// graphs draw plain straight edges between node centers.
import type { Edge } from '@xyflow/react'

export type NodeSide = 'left' | 'right'

const EDGE_CORNER_RADIUS = 16

export function sideEdge(id: string, source: string, sourceSide: NodeSide, target: string, targetSide: NodeSide): Edge {
  return {
    id,
    source,
    sourceHandle: sourceSide,
    target,
    targetHandle: targetSide,
    type: 'smoothstep',
    pathOptions: { borderRadius: EDGE_CORNER_RADIUS },
  } as Edge
}
