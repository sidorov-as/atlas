// @vitest-environment jsdom
import type { ReactNode } from 'react'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { ReactFlowProvider, type EdgeProps } from '@xyflow/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FlowTransitionEdge, type FlowEdgeData } from './FlowEdges'
import { FLOW_EDGE_LABEL_MAX_WIDTH, FLOW_NODE_HEIGHT } from '../lib/flowLayout'

// `getSmoothStepPath` is a pure geometry function from the library — stubbed
// here so the expected path is a known, fixed value rather than a real
// smoothstep computation we'd have to duplicate to assert against (mirrors
// FlowNodes.test.tsx's approach of stubbing a library primitive rather than
// re-deriving its output). `EdgeLabelRenderer` is also stubbed to render its
// children in place: the real one portals into a `.react-flow__edgelabel-
// renderer` div that only exists once a full `<ReactFlow>` tree has mounted
// and registered its `domNode` — this test renders `FlowTransitionEdge` in
// isolation (no such tree), so without this stub the label would silently
// render nothing rather than actually failing to find it.
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return {
    ...actual,
    getSmoothStepPath: () => ['M 0 0 Q 50 0 50 50 L 100 100', 50, 50],
    EdgeLabelRenderer: ({ children }: { children: ReactNode }) => children,
  }
})

afterEach(() => cleanup())

function edgeProps(overrides: Partial<EdgeProps> = {}): EdgeProps {
  return {
    id: 'a->b',
    source: 'a',
    target: 'b',
    sourceX: 0,
    sourceY: 0,
    targetX: 100,
    targetY: 100,
    sourcePosition: 'right' as never,
    targetPosition: 'left' as never,
    ...overrides,
  } as EdgeProps
}

function renderEdge(props: EdgeProps) {
  return render(
    <ReactFlowProvider>
      <svg>
        <FlowTransitionEdge {...props} />
      </svg>
    </ReactFlowProvider>,
  )
}

function labelBox(container: HTMLElement): HTMLElement {
  return container.querySelector('.nodrag.nopan') as HTMLElement
}

describe('FlowTransitionEdge', () => {
  it('always renders the path via getSmoothStepPath — there is no routing branch left to take', () => {
    const { container } = renderEdge(edgeProps({ data: {} }))
    const path = container.querySelector('path')
    expect(path?.getAttribute('d')).toBe('M 0 0 Q 50 0 50 50 L 100 100')
  })

  it('renders no label box when the edge has no label', () => {
    const { container } = renderEdge(edgeProps({ data: {} }))
    expect(labelBox(container)).toBeNull()
  })

  it("caps the label box at the layout engines' reserved footprint, so a long label grows only up to that size", () => {
    const label = 'a fairly long transition label that would overflow a short pill'
    const { container } = renderEdge(edgeProps({ data: {}, label }))
    const box = labelBox(container)
    expect(box.style.maxWidth).toBe(`${FLOW_EDGE_LABEL_MAX_WIDTH}px`)
    expect(box.style.maxHeight).toBe(`${FLOW_NODE_HEIGHT}px`)
  })

  it('makes the full label available via a tooltip/aria-label even once clamped', () => {
    const label = 'a fairly long transition label that would overflow a short pill'
    const { container, getByText } = renderEdge(edgeProps({ data: {}, label }))
    expect(getByText(label)).toBeTruthy()
    expect(labelBox(container).getAttribute('aria-label')).toBe(label)
  })

  it('is click-inert with no onOpenTransitionModal callback (read-only canvas)', () => {
    const { container } = renderEdge(edgeProps({ data: {}, label: 'yes' }))
    expect(labelBox(container).style.pointerEvents).toBe('none')
  })

  it("clicking the label opens the transition modal when the editable canvas wires a callback", () => {
    const onOpenTransitionModal = vi.fn()
    const { container } = renderEdge(edgeProps({ data: { onOpenTransitionModal } satisfies FlowEdgeData, label: 'yes' }))
    const box = labelBox(container)
    expect(box.style.pointerEvents).toBe('all')
    fireEvent.click(box)
    expect(onOpenTransitionModal).toHaveBeenCalledTimes(1)
  })
})
