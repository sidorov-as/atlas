// @vitest-environment jsdom
import type { ReactNode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointConsumersGraph } from './EndpointConsumersGraph'
import { makeConsumers, makeServiceSummary } from '../testFixtures'

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

function renderGraph(props: Partial<Parameters<typeof EndpointConsumersGraph>[0]> = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EndpointConsumersGraph
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

describe('EndpointConsumersGraph', () => {
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

  it('shows an empty state with a Link service action when there are no linked services', () => {
    const onLinkService = vi.fn()
    renderGraph({ consumers: makeConsumers([]), onLinkService, canLinkService: true })

    expect(screen.getByText('No services are linked to this endpoint yet')).toBeDefined()
    fireEvent.click(screen.getByText('Link service'))
    expect(onLinkService).toHaveBeenCalled()
  })

  it('does not offer Link service in the empty state when linking is not allowed', () => {
    renderGraph({ consumers: makeConsumers([]), canLinkService: false })

    expect(screen.getByText('No services are linked to this endpoint yet')).toBeDefined()
    expect(screen.queryByText('Link service')).toBeNull()
  })

  it('draws edges from each Service to the Endpoint, not the reverse (inline graph)', () => {
    renderGraph({ consumers: makeConsumers([makeServiceSummary({ id: 'service-1' })]) })

    // The full-screen dialog starts closed, so its `ReactFlow` isn't mounted
    // yet — the only `flow-props` node present is the inline graph's.
    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.edges).toEqual([{ id: 'service-1-endpoint', source: 'service-1', target: 'endpoint', type: 'straight' }])
  })

  it('sets nodesDraggable/nodesConnectable to false and elementsSelectable to true (no drag/connect/delete, inline graph)', () => {
    renderGraph({ consumers: makeConsumers([makeServiceSummary()]) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.nodesDraggable).toBe(false)
    expect(props.nodesConnectable).toBe(false)
    expect(props.elementsSelectable).toBe(true)
  })

  it('caps the compact inline graph at 12 service nodes and shows an overflow indicator', () => {
    const services = Array.from({ length: 15 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    // 12 service nodes + 1 endpoint node.
    expect(props.nodes.length).toBe(13)
    expect(screen.getByText('12 of 15 services shown')).toBeDefined()
  })

  it('shows no overflow indicator on the inline graph at or under the 12-node cap', () => {
    const services = Array.from({ length: 12 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    expect(screen.queryByText(/services shown/)).toBeNull()
  })

  it('clicking a Service node navigates to that Service', () => {
    renderGraph({ consumers: makeConsumers([makeServiceSummary({ id: 'service-1' })]) })

    fireEvent.click(screen.getByText('node-service-1'))

    expect(navigateSpy).toHaveBeenCalledWith('/components/service-1')
  })

  it('clicking the Endpoint node does not navigate away', () => {
    renderGraph({ consumers: makeConsumers([makeServiceSummary({ id: 'service-1' })]) })

    fireEvent.click(screen.getByText('node-endpoint'))

    expect(navigateSpy).not.toHaveBeenCalled()
  })

  it('opens the full-screen dialog showing every linked Service uncapped', async () => {
    const services = Array.from({ length: 15 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    fireEvent.click(screen.getByText('Full screen'))

    await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    const [, fullscreenProps] = screen.getAllByTestId('flow-props').map((node) => JSON.parse(node.textContent!))
    // 15 service nodes + 1 endpoint node — no 12-node cap in full screen.
    expect(fullscreenProps.nodes.length).toBe(16)
  })

  it('closes the full-screen dialog via its close action, returning to the Overview tab', async () => {
    renderGraph({ consumers: makeConsumers([makeServiceSummary({ id: 'service-1' })]) })

    fireEvent.click(screen.getByText('Full screen'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(2))

    fireEvent.click(screen.getByLabelText('Close dialog'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(1))
  })
})
