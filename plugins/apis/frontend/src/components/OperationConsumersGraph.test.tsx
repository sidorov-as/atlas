// @vitest-environment jsdom
import type { ReactNode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationConsumersGraph } from './OperationConsumersGraph'
import { makeOperationConsumers, makeServiceSummary } from '../testFixtures'

const navigateSpy = vi.fn()

afterEach(() => {
  cleanup()
  navigateSpy.mockClear()
})
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateSpy }
})

// The full-screen control opens a real Gravity UI `Dialog`, whose `Modal`
// unconditionally calls `useMatchMedia`/`ResizeObserver`-backed hooks even
// while closed — jsdom has neither, so both need stubbing (same pattern as
// `LinkServiceDialog.test.tsx`).
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

// The graph's own layout/click/prop-wiring is covered elsewhere — actually
// mounting `@xyflow/react`'s canvas needs a lot more jsdom plumbing than that
// (SVG measurement, ResizeObserver-driven viewport fitting) and would test
// the library, not this component. `ReactFlow` is stubbed to just record the
// props this component passes it and let node clicks be simulated directly.
interface RecordedFlowProps {
  nodes: { id: string; type?: string }[]
  edges: { id: string; source: string; target: string }[]
  nodesDraggable?: boolean
  nodesConnectable?: boolean
  elementsSelectable?: boolean
  onNodeClick?: (event: unknown, node: { id: string; type?: string }) => void
}

vi.mock('@xyflow/react', () => ({
  ReactFlow: (props: RecordedFlowProps & { children?: ReactNode }) => (
    <div data-testid="react-flow">
      <div data-testid="flow-props">{JSON.stringify({
        nodes: props.nodes.map((node) => node.id),
        edges: props.edges,
        nodesDraggable: props.nodesDraggable,
        nodesConnectable: props.nodesConnectable,
        elementsSelectable: props.elementsSelectable,
      })}</div>
      {props.nodes.map((node) => (
        <button key={node.id} onClick={(event) => props.onNodeClick?.(event, node)}>
          node-{node.id}
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
}))

function renderGraph(props: Partial<Parameters<typeof OperationConsumersGraph>[0]> = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <OperationConsumersGraph
          consumers={null}
          isLoading={false}
          error={null}
          onRetry={vi.fn()}
          canLinkService
          onLinkService={vi.fn()}
          {...props}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('OperationConsumersGraph', () => {
  it('shows an isolated error state with a retry action when the graph fails to load', () => {
    const onRetry = vi.fn()
    renderGraph({ error: new Error('boom'), onRetry })

    expect(screen.getByText('boom')).toBeDefined()
    fireEvent.click(screen.getByText('Retry'))
    expect(onRetry).toHaveBeenCalled()
  })

  it('shows a loading skeleton while loading with no data yet', () => {
    renderGraph({ isLoading: true, consumers: null })
    expect(screen.queryByTestId('react-flow')).toBeNull()
  })

  it('shows an empty state with a Link service action when there are no participants', () => {
    const onLinkService = vi.fn()
    renderGraph({ consumers: makeOperationConsumers([]), onLinkService, canLinkService: true })

    expect(screen.getByText('No services are linked to this channel yet')).toBeDefined()
    fireEvent.click(screen.getByText('Link service'))
    expect(onLinkService).toHaveBeenCalled()
  })

  it('does not offer Link service in the empty state when linking is not allowed', () => {
    renderGraph({ consumers: makeOperationConsumers([]), canLinkService: false })

    expect(screen.getByText('No services are linked to this channel yet')).toBeDefined()
    expect(screen.queryByText('Link service')).toBeNull()
  })

  it('draws an edge from a publisher into the channel, and from the channel out to a subscriber (inline graph)', () => {
    renderGraph({
      consumers: makeOperationConsumers([
        { service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' },
        { service: makeServiceSummary({ id: 'service-2' }), role: 'subscriber' },
      ]),
    })

    // The full-screen dialog starts closed, so its `ReactFlow` isn't mounted
    // yet — the only `flow-props` node present is the inline graph's.
    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.edges).toContainEqual({ id: 'publisher-service-1-edge', source: 'publisher-service-1', target: 'channel', type: 'straight' })
    expect(props.edges).toContainEqual({ id: 'subscriber-service-2-edge', source: 'channel', target: 'subscriber-service-2', type: 'straight' })
  })

  it('sets nodesDraggable/nodesConnectable to false and elementsSelectable to true (no drag/connect/delete, inline graph)', () => {
    renderGraph({ consumers: makeOperationConsumers([{ service: makeServiceSummary(), role: 'publisher' }]) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.nodesDraggable).toBe(false)
    expect(props.nodesConnectable).toBe(false)
    expect(props.elementsSelectable).toBe(true)
  })

  it('caps the compact inline graph at 12 participant nodes and shows an overflow indicator', () => {
    const participants = Array.from({ length: 15 }, (_, index) => ({
      service: makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }),
      role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers(participants) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    // 12 participant nodes + 1 channel node.
    expect(props.nodes.length).toBe(13)
    expect(screen.getByText('12 of 15 participants shown')).toBeDefined()
  })

  it('shows no overflow indicator on the inline graph at or under the 12-node cap', () => {
    const participants = Array.from({ length: 12 }, (_, index) => ({
      service: makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }),
      role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers(participants) })

    expect(screen.queryByText(/participants shown/)).toBeNull()
  })

  it('aggregates participants across operations from a different API sharing the same channel', () => {
    // The `/consumers` response's `participants` already reflects cross-API
    // aggregation server-side — this component just
    // renders whatever it's given, including a provider from another API.
    renderGraph({
      consumers: makeOperationConsumers([
        { service: makeServiceSummary({ id: 'own-provider' }), role: 'publisher' },
        { service: makeServiceSummary({ id: 'other-api-provider' }), role: 'subscriber' },
      ]),
    })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.nodes).toContain('publisher-own-provider')
    expect(props.nodes).toContain('subscriber-other-api-provider')
  })

  it('clicking a Service node navigates to that Service', () => {
    renderGraph({ consumers: makeOperationConsumers([{ service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' }]) })

    fireEvent.click(screen.getByText('node-publisher-service-1'))

    expect(navigateSpy).toHaveBeenCalledWith('/components/service-1')
  })

  it('clicking the channel node does not navigate away', () => {
    renderGraph({ consumers: makeOperationConsumers([{ service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' }]) })

    fireEvent.click(screen.getByText('node-channel'))

    expect(navigateSpy).not.toHaveBeenCalled()
  })

  it('opens the full-screen dialog showing every participant uncapped', async () => {
    const participants = Array.from({ length: 15 }, (_, index) => ({
      service: makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }),
      role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers(participants) })

    fireEvent.click(screen.getByText('Full screen'))

    await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    const [, fullscreenProps] = screen.getAllByTestId('flow-props').map((node) => JSON.parse(node.textContent!))
    // 15 participant nodes + 1 channel node — no 12-node cap in full screen.
    expect(fullscreenProps.nodes.length).toBe(16)
  })

  it('closes the full-screen dialog via its close action, returning to the Overview tab', async () => {
    renderGraph({ consumers: makeOperationConsumers([{ service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' }]) })

    fireEvent.click(screen.getByText('Full screen'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(2))

    fireEvent.click(screen.getByLabelText('Close dialog'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(1))
  })
})
