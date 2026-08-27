import { MarkerType } from '@xyflow/react'
import { describe, expect, it } from 'vitest'

import {
  buildFlowNodesAndEdges,
  computeFlowAutolayout,
  mergeStepPositions,
  nextConnectedPosition,
  nextRowPosition,
  resolveConnectedPosition,
  FLOW_LAYER_GAP,
  FLOW_NODE_HEIGHT,
  FLOW_NODE_WIDTH,
  type FlowLayoutEngine,
  type FlowStep,
} from './flowLayout'

// Actual autolayout coordinates come from `dagre`/`elkjs` via the async
// `computeFlowAutolayout` and aren't asserted in detail here — that's
// implementation detail owned by each library, verified manually.
// `buildFlowNodesAndEdges` covers the parts of the
// pipeline that stay pure and synchronous (forest construction, cycle/
// reconvergence tolerance, connection/label wiring).

describe('computeFlowAutolayout', () => {
  const engines: FlowLayoutEngine[] = ['dagre', 'elk']

  it.each(engines)('returns a position for every step id (engine: %s)', async (engine) => {
    const steps: FlowStep[] = [
      { id: 'start', next_steps: [{ id: 'success', label: 'ok' }, { id: 'failure', label: 'err' }] },
      { id: 'success' },
      { id: 'failure' },
    ]

    const { positions } = await computeFlowAutolayout(steps, 'LAYOUT_LEFT_RIGHT', engine)

    expect(Object.keys(positions).sort()).toEqual(['failure', 'start', 'success'])
    for (const position of Object.values(positions)) {
      expect(Number.isFinite(position.x)).toBe(true)
      expect(Number.isFinite(position.y)).toBe(true)
    }
  })

  it.each(engines)('places every root/step even with no transitions at all (engine: %s)', async (engine) => {
    const steps: FlowStep[] = [{ id: 'root-1' }, { id: 'root-2' }]

    const { positions } = await computeFlowAutolayout(steps, 'LAYOUT_LEFT_RIGHT', engine)

    expect(Object.keys(positions).sort()).toEqual(['root-1', 'root-2'])
  })

  it.each(engines)('terminates on a cycle instead of hanging, placing every step once (engine: %s)', async (engine) => {
    const steps: FlowStep[] = [
      { id: 'a', next_step: { id: 'b' } },
      { id: 'b', next_step: { id: 'a' } },
    ]

    const { positions } = await computeFlowAutolayout(steps, 'LAYOUT_LEFT_RIGHT', engine)

    expect(Object.keys(positions).sort()).toEqual(['a', 'b'])
  })

  it('defaults to the dagre engine when none is specified', async () => {
    const { positions } = await computeFlowAutolayout([{ id: 'a' }], 'LAYOUT_LEFT_RIGHT')
    expect(positions.a).toBeDefined()
  })
})

describe('computeFlowAutolayout — a wide fan-out with an uneven-depth sibling (real-world regression)', () => {
  // `a` has 5 direct children: two (`b1`, `b2`) that branch further before
  // reaching `z`, and three (`b3`/`b4`/`b5`) that go straight to it. A
  // layering strategy that only minimizes total edge length can pull a
  // single-edge sibling toward whatever layer shortens its own edge,
  // scattering same-depth siblings across different layers and potentially
  // rendering two of them on top of each other. Each engine here is
  // expected to keep same-depth siblings spaced apart on its own — the
  // `elk` engine keeps `COFFMAN_GRAHAM` layering for exactly this reason
  // (see `flowLayout.ts`'s `layoutWithElk`), and `dagre`'s own layered
  // algorithm handles sibling spacing without any bespoke post-processing.
  const engines: FlowLayoutEngine[] = ['dagre', 'elk']

  it.each(engines)('never renders two siblings at the same, or a too-close, position (engine: %s)', async (engine) => {
    const steps: FlowStep[] = [
      { id: 'a', next_steps: [{ id: 'b1' }, { id: 'b2' }, { id: 'b3' }, { id: 'b4' }, { id: 'b5' }] },
      { id: 'b1', next_steps: [{ id: 'c1' }, { id: 'c2' }] },
      { id: 'b2', next_steps: [{ id: 'c3' }, { id: 'c4' }] },
      { id: 'b3', next_step: { id: 'z' } },
      { id: 'b4', next_step: { id: 'z' } },
      { id: 'b5', next_step: { id: 'z' } },
      { id: 'c1', next_step: { id: 'z' } },
      { id: 'c2', next_step: { id: 'z' } },
      { id: 'c3', next_step: { id: 'z' } },
      { id: 'c4', next_step: { id: 'z' } },
      { id: 'z' },
    ]

    const { positions } = await computeFlowAutolayout(steps, 'LAYOUT_LEFT_RIGHT', engine)
    const ids = Object.keys(positions)
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = positions[ids[i]]
        const b = positions[ids[j]]
        const overlaps = Math.abs(a.x - b.x) < FLOW_NODE_WIDTH && Math.abs(a.y - b.y) < FLOW_NODE_HEIGHT
        expect(overlaps, `${ids[i]} ${JSON.stringify(a)} vs ${ids[j]} ${JSON.stringify(b)}`).toBe(false)
      }
    }
  })
})

describe('mergeStepPositions', () => {
  it('while autolayout is enabled, always returns the fresh autolayout position, ignoring any stored one', () => {
    const steps: FlowStep[] = [{ id: 'a', position: { x: 5, y: 6 } }, { id: 'b' }]

    const merged = mergeStepPositions(steps, true, { a: { x: 100, y: 100 }, b: { x: 10, y: 20 } })

    expect(merged.a).toEqual({ x: 100, y: 100 })
    expect(merged.b).toEqual({ x: 10, y: 20 })
  })

  it('while autolayout is enabled, falls back to the origin for a step missing from the autolayout positions', () => {
    const merged = mergeStepPositions([{ id: 'a' }], true, {})
    expect(merged.a).toEqual({ x: 0, y: 0 })
  })

  it('while autolayout is disabled, always returns each step\'s own stored position, ignoring any autolayout positions passed in', () => {
    const steps: FlowStep[] = [{ id: 'a', position: { x: 5, y: 6 } }, { id: 'b' }]

    const merged = mergeStepPositions(steps, false, { a: { x: 100, y: 100 }, b: { x: 10, y: 20 } })

    expect(merged.a).toEqual({ x: 5, y: 6 })
    expect(merged.b).toEqual({ x: 0, y: 0 })
  })

  it('while autolayout is disabled, works with no autolayout positions supplied at all (no layout engine call needed)', () => {
    const steps: FlowStep[] = [{ id: 'a', position: { x: 5, y: 6 } }, { id: 'b' }]

    const merged = mergeStepPositions(steps, false)

    expect(merged.a).toEqual({ x: 5, y: 6 })
    expect(merged.b).toEqual({ x: 0, y: 0 })
  })
})

describe('nextRowPosition', () => {
  it('starts at the origin for an empty flow', () => {
    expect(nextRowPosition([], {})).toEqual({ x: 0, y: 0 })
  })

  it('lands one gap below a single-root flow, left-aligned to it', () => {
    const steps: FlowStep[] = [{ id: 'a' }]
    const position = nextRowPosition(steps, { a: { x: 40, y: 100 } })
    expect(position.x).toBe(40)
    expect(position.y).toBeGreaterThan(100)
  })

  it('clears the full node height below the lowest step, not just the layer gap (a `position` is a node\'s top-left corner, not its bottom edge)', () => {
    const steps: FlowStep[] = [{ id: 'a' }]
    const position = nextRowPosition(steps, { a: { x: 0, y: 100 } })
    expect(position.y).toBe(100 + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP)
  })

  it('left-aligns to the leftmost step and sits below the lowest one across a multi-row flow', () => {
    const steps: FlowStep[] = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]
    const position = nextRowPosition(steps, {
      a: { x: 0, y: 0 },
      b: { x: 200, y: 0 },
      c: { x: 100, y: 150 },
    })
    expect(position.x).toBe(0)
    expect(position.y).toBeGreaterThan(150)
  })

  it('treats a step missing from the resolved positions as sitting at the origin', () => {
    const position = nextRowPosition([{ id: 'a' }], {})
    expect(position.x).toBe(0)
    expect(position.y).toBeGreaterThan(0)
  })
})

describe('nextConnectedPosition', () => {
  it('lands one node-width + gap to the right for a left-right layout', () => {
    expect(nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT')).toEqual({ x: 100 + FLOW_NODE_WIDTH + FLOW_LAYER_GAP, y: 40 })
  })

  it('lands one node-height + gap below for a top-down layout', () => {
    expect(nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_TOP_DOWN')).toEqual({ x: 100, y: 40 + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP })
  })
})

describe('resolveConnectedPosition', () => {
  it('returns the naive position when nothing occupies it', () => {
    const position = resolveConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT', [])
    expect(position).toEqual(nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT'))
  })

  it('pushes straight past a real node that already occupies the naive slot (left-right: down)', () => {
    const naive = nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT')
    const position = resolveConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT', [naive])
    expect(position).not.toEqual(naive)
    expect(position.x).toBe(naive.x)
    expect(position.y).toBe(naive.y + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP)
  })

  it('pushes past a node that already occupies the naive slot (top-down: right)', () => {
    const naive = nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_TOP_DOWN')
    const position = resolveConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_TOP_DOWN', [naive])
    expect(position.x).toBe(naive.x + FLOW_NODE_WIDTH + FLOW_LAYER_GAP)
    expect(position.y).toBe(naive.y)
  })

  it('keeps pushing until it clears every occupied slot, not just the first one it tries', () => {
    const naive = nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT')
    const secondSlot = { x: naive.x, y: naive.y + FLOW_NODE_HEIGHT + FLOW_LAYER_GAP }
    const position = resolveConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT', [naive, secondSlot])
    expect(position).not.toEqual(naive)
    expect(position).not.toEqual(secondSlot)
  })

  it('does not flag a nearby-but-non-overlapping position as occupied', () => {
    const naive = nextConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT')
    // Far enough along the layering axis that it's a different column, not the same slot.
    const distant = { x: naive.x + 1000, y: naive.y }
    expect(resolveConnectedPosition({ x: 100, y: 40 }, 'LAYOUT_LEFT_RIGHT', [distant])).toEqual(naive)
  })
})

describe('buildFlowNodesAndEdges', () => {
  it('places each node at its given position and falls back to the origin if missing', () => {
    const steps: FlowStep[] = [
      { id: 'a', next_step: { id: 'b' } },
      { id: 'b' },
    ]

    const { nodes } = buildFlowNodesAndEdges(steps, { a: { x: 10, y: 20 } })

    expect(nodes.find((node) => node.id === 'a')).toMatchObject({ position: { x: 10, y: 20 } })
    expect(nodes.find((node) => node.id === 'b')).toMatchObject({ position: { x: 0, y: 0 } })
  })

  it('derives each node type from its step data', () => {
    const steps: FlowStep[] = [
      { id: 'svc', entity_ref: 'component:checkout-api' },
      { id: 'ext', external_label: 'Payment Gateway' },
      { id: 'plain' },
    ]

    const { nodes } = buildFlowNodesAndEdges(steps, {})

    expect(nodes.find((node) => node.id === 'svc')?.type).toBe('component')
    expect(nodes.find((node) => node.id === 'ext')?.type).toBe('external')
    expect(nodes.find((node) => node.id === 'plain')?.type).toBe('step')
  })

  it('carries each transition label onto its edge, leaving unlabeled transitions undefined', () => {
    const steps: FlowStep[] = [
      { id: 'start', next_steps: [{ id: 'success', label: 'ok' }, { id: 'failure', label: 'err' }] },
      { id: 'success' },
      { id: 'failure' },
    ]

    const { edges } = buildFlowNodesAndEdges(steps, {})

    expect(edges).toHaveLength(2)
    expect(edges.find((edge) => edge.target === 'success')?.label).toBe('ok')
    expect(edges.find((edge) => edge.target === 'failure')?.label).toBe('err')
  })

  it('uses the custom wrapping-label edge type instead of the default smoothstep', () => {
    const steps: FlowStep[] = [
      { id: 'a', next_step: { id: 'b' } },
      { id: 'b' },
    ]

    const { edges } = buildFlowNodesAndEdges(steps, {})

    expect(edges[0].type).toBe('flow-transition')
  })

  it('gives every edge a closed arrowhead marker, sized well past the default so it reads as more than the connection handle dot', () => {
    const steps: FlowStep[] = [
      { id: 'a', next_step: { id: 'b' } },
      { id: 'b' },
    ]

    const { edges } = buildFlowNodesAndEdges(steps, {})

    expect(edges).toHaveLength(1)
    expect(edges[0].markerEnd).toMatchObject({ type: MarkerType.ArrowClosed })
    const markerEnd = edges[0].markerEnd as { width: number; height: number }
    expect(markerEnd.width).toBeGreaterThan(12.5)
    expect(markerEnd.height).toBeGreaterThan(12.5)
  })

  it('drops a dangling transition target instead of throwing', () => {
    const steps: FlowStep[] = [{ id: 'a', next_step: { id: 'does-not-exist' } }]

    const { nodes, edges } = buildFlowNodesAndEdges(steps, {})

    expect(nodes.map((node) => node.id)).toEqual(['a'])
    expect(edges).toEqual([])
  })

  it('terminates on a cycle instead of recursing forever, rendering each node once but every real transition as an edge', () => {
    const steps: FlowStep[] = [
      { id: 'a', next_step: { id: 'b' } },
      { id: 'b', next_step: { id: 'a' } },
    ]

    const { nodes, edges } = buildFlowNodesAndEdges(steps, {})

    expect(nodes.map((node) => node.id).sort()).toEqual(['a', 'b'])
    expect(edges).toHaveLength(2)
  })

  it('never attaches a routing field to an edge — every connection renders as a live curve, not a precomputed route', () => {
    const steps: FlowStep[] = [
      { id: 'a', next_step: { id: 'b' } },
      { id: 'b', next_step: { id: 'c' } },
      { id: 'c' },
    ]

    const { edges } = buildFlowNodesAndEdges(steps, {})

    for (const edge of edges) {
      expect((edge.data as { routing?: unknown } | undefined)?.routing).toBeUndefined()
    }
  })

  it('renders two independent edges into a target reconverged from two different sources, each with its own label', () => {
    const steps: FlowStep[] = [
      { id: 'start', next_steps: [{ id: 'a' }, { id: 'b' }] },
      { id: 'a', next_step: { id: 'end', label: 'via a' } },
      { id: 'b', next_step: { id: 'end', label: 'via b' } },
      { id: 'end' },
    ]

    const { nodes, edges } = buildFlowNodesAndEdges(steps, {})

    expect(nodes.filter((node) => node.id === 'end')).toHaveLength(1)
    const intoEnd = edges.filter((edge) => edge.target === 'end')
    expect(intoEnd).toHaveLength(2)
    expect(intoEnd.find((edge) => edge.source === 'a')?.label).toBe('via a')
    expect(intoEnd.find((edge) => edge.source === 'b')?.label).toBe('via b')
  })
})
