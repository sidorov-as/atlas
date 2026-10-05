// Shared `@xyflow/react` stand-in for the graph component tests. Mounting the
// real canvas needs a lot more jsdom plumbing than these tests care about
// (SVG measurement, ResizeObserver-driven viewport fitting) and would test the
// library, not our components. `ReactFlow` records the props the component
// passes it and lets node clicks and drags be simulated directly; the real
// `useNodesState` is kept so drag changes flow through `onNodesChange`.
import type { ReactNode } from 'react'

interface MockNode {
  id: string
  type?: string
  position: { x: number; y: number }
  className?: string
  draggable?: boolean
  data?: { count?: number; total?: number; expanded?: boolean; name?: string; dimmed?: boolean }
}

interface MockFlowProps {
  nodes: MockNode[]
  edges: { id: string; source: string; target: string }[]
  nodesDraggable?: boolean
  nodesConnectable?: boolean
  elementsSelectable?: boolean
  onNodeClick?: (event: unknown, node: MockNode) => void
  onNodesChange?: (changes: unknown[]) => void
  children?: ReactNode
}

export const DRAG_TARGET = { x: 1234, y: -567 }

export function reactFlowMock(actual: { useNodesState: unknown }) {
  return {
    useNodesState: actual.useNodesState,
    ReactFlow: (props: MockFlowProps) => (
      <div data-testid="react-flow">
        <div data-testid="flow-props">{JSON.stringify({
          nodes: props.nodes.map((node) => node.id),
          edges: props.edges,
          nodesDraggable: props.nodesDraggable,
          nodesConnectable: props.nodesConnectable,
          elementsSelectable: props.elementsSelectable,
          positions: Object.fromEntries(props.nodes.map((node) => [node.id, node.position])),
          classNames: Object.fromEntries(props.nodes.map((node) => [node.id, node.className ?? ''])),
          draggable: Object.fromEntries(props.nodes.map((node) => [node.id, node.draggable ?? null])),
          moreCounts: Object.fromEntries(props.nodes.filter((node) => node.type === 'more').map((node) => [node.id, node.data?.count])),
          groups: Object.fromEntries(props.nodes.filter((node) => node.type === 'consumerGroup').map((node) => [node.id, {
            name: node.data?.name, count: node.data?.count, total: node.data?.total, expanded: node.data?.expanded, dimmed: node.data?.dimmed ?? false,
          }])),
        })}</div>
        {props.nodes.map((node) => (
          <button key={node.id} onClick={(event) => props.onNodeClick?.(event, node)}>
            node-{node.id}
          </button>
        ))}
        {props.nodes.map((node) => (
          <button
            key={`drag-${node.id}`}
            onClick={() => props.onNodesChange?.([{ type: 'position', id: node.id, position: DRAG_TARGET, dragging: false }])}
          >
            drag-{node.id}
          </button>
        ))}
        {props.children}
      </div>
    ),
    Background: () => null,
    Controls: () => null,
    Panel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
    Handle: () => null,
    Position: { Top: 'top' },
  }
}

/** This Node/jsdom combination exposes no usable `window.localStorage`; give tests an in-memory one. */
export function installMemoryLocalStorage() {
  const store = new Map<string, string>()
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => { store.set(key, String(value)) },
      removeItem: (key: string) => { store.delete(key) },
      clear: () => store.clear(),
    },
  })
}
