// Invisible handles on the left and right edge of a graph node. The full-screen
// graphs draw rounded step edges between node sides; the compact inline graphs
// keep straight edges between node centers and use each node's centered handle
// instead. A side needs both a source and a target handle so an edge can leave
// or enter on either end.
import { Handle, Position } from '@xyflow/react'

const HIDDEN = { opacity: 0, pointerEvents: 'none' } as const

export function SideHandles() {
  return (
    <>
      <Handle id="left" type="source" position={Position.Left} style={HIDDEN} />
      <Handle id="left" type="target" position={Position.Left} style={HIDDEN} />
      <Handle id="right" type="source" position={Position.Right} style={HIDDEN} />
      <Handle id="right" type="target" position={Position.Right} style={HIDDEN} />
    </>
  )
}
