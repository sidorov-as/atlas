// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { toPng } from 'html-to-image'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadDataUrl } from 'frontend/lib/diagramExport'
import { OperationConsumersGraph } from './OperationConsumersGraph'
import { operationServicesApi } from '../lib/entities'
import { makeOperationConsumers, makeServiceSummary } from '../testFixtures'
import { DRAG_TARGET, installMemoryLocalStorage } from '../testReactFlowMock'

vi.mock('../lib/entities', () => ({ operationServicesApi: { consumers: vi.fn() } }))

vi.mock('html-to-image', () => ({ toSvg: vi.fn(), toPng: vi.fn() }))
vi.mock('frontend/lib/diagramExport', () => ({ downloadDataUrl: vi.fn() }))

installMemoryLocalStorage()

const navigateSpy = vi.fn()

// Most tests here exercise the ungrouped graph, which graphs of 10+ Services no
// longer open with by default; the grouping tests clear or change this.
beforeEach(() => {
  window.localStorage.setItem('atlas.apis.graphGroupBy', 'none')
})

afterEach(() => {
  cleanup()
  navigateSpy.mockClear()
  vi.mocked(operationServicesApi.consumers).mockReset()
  window.localStorage.clear()
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

vi.mock('@xyflow/react', async (importOriginal) => (
  (await import('../testReactFlowMock')).reactFlowMock(await importOriginal<typeof import('@xyflow/react')>())
))

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

  it('caps the compact inline graph at 6 participants across roles, publishers first, with one "more" node per side', () => {
    const publishers = Array.from({ length: 4 }, (_, index) => ({
      service: makeServiceSummary({ id: `pub-${index}`, name: `pub-${index}` }), role: 'publisher' as const,
    }))
    const subscribers = Array.from({ length: 10 }, (_, index) => ({
      service: makeServiceSummary({ id: `sub-${index}`, name: `sub-${index}` }), role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers([...publishers, ...subscribers]) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.nodes).toEqual([
      'channel',
      'publisher-pub-0', 'publisher-pub-1', 'publisher-pub-2', 'publisher-pub-3',
      'subscriber-sub-0', 'subscriber-sub-1', 'more-subscriber',
    ])
  })

  it('draws a "more" node for a side with no drawn participants so its Services are never invisible', () => {
    const publishers = Array.from({ length: 8 }, (_, index) => ({
      service: makeServiceSummary({ id: `pub-${index}`, name: `pub-${index}` }), role: 'publisher' as const,
    }))
    const subscribers = [{ service: makeServiceSummary({ id: 'sub-0', name: 'sub-0' }), role: 'subscriber' as const }]
    renderGraph({ consumers: makeOperationConsumers([...publishers, ...subscribers]) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    expect(props.nodes).toContain('more-publisher')
    expect(props.nodes).toContain('more-subscriber')
    expect(props.nodes.filter((id: string) => id.startsWith('subscriber-'))).toEqual([])
  })

  it('draws no "more" node at or under the 6-participant cap', () => {
    const participants = Array.from({ length: 6 }, (_, index) => ({
      service: makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }),
      role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers(participants) })

    expect(screen.queryByText(/node-more/)).toBeNull()
  })

  it('clicking a "more" node opens the full-screen graph and never navigates', async () => {
    const participants = Array.from({ length: 9 }, (_, index) => ({
      service: makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }),
      role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers(participants) })

    fireEvent.click(screen.getByText('node-more-subscriber'))

    await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    expect(navigateSpy).not.toHaveBeenCalled()
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

  it('opens the full-screen dialog showing every loaded participant without the compact cap', async () => {
    const participants = Array.from({ length: 15 }, (_, index) => ({
      service: makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }),
      role: 'subscriber' as const,
    }))
    renderGraph({ consumers: makeOperationConsumers(participants) })

    fireEvent.click(screen.getByText('Full screen'))

    await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    const [, fullscreenProps] = screen.getAllByTestId('flow-props').map((node) => JSON.parse(node.textContent!))
    // 15 participant nodes + 1 channel node — no compact cap in full screen.
    expect(fullscreenProps.nodes.length).toBe(16)
  })

  it('closes the full-screen dialog via its close action, returning to the Overview tab', async () => {
    renderGraph({ consumers: makeOperationConsumers([{ service: makeServiceSummary({ id: 'service-1' }), role: 'publisher' }]) })

    fireEvent.click(screen.getByText('Full screen'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(2))

    fireEvent.click(screen.getByLabelText('Close dialog'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(1))
  })

  describe('full screen', () => {
    const participants = (count: number, role: 'publisher' | 'subscriber', prefix = role === 'publisher' ? 'pub' : 'sub') =>
      Array.from({ length: count }, (_, index) => ({
        service: makeServiceSummary({ id: `${prefix}-${index}`, name: `${prefix}-${index}`, title: `${prefix} ${index}` }),
        role,
      }))

    async function openFullscreen() {
      fireEvent.click(screen.getByText('Full screen'))
      await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    }
    const fullscreenProps = () => JSON.parse(screen.getAllByTestId('flow-props')[1].textContent!)
    type Positions = Record<string, { x: number; y: number }>

    it('makes nodes draggable in full screen, and Auto-layout restores dragged positions', async () => {
      renderGraph({ consumers: makeOperationConsumers([...participants(2, 'publisher'), ...participants(2, 'subscriber')]) })
      await openFullscreen()
      expect(fullscreenProps().nodesDraggable).toBe(true)
      expect(fullscreenProps().nodesConnectable).toBe(false)
      const original = fullscreenProps().positions

      fireEvent.click(screen.getAllByText('drag-publisher-pub-1')[1])
      await waitFor(() => expect(fullscreenProps().positions['publisher-pub-1']).toEqual(DRAG_TARGET))
      fireEvent.click(screen.getByLabelText('Auto-layout'))

      await waitFor(() => expect(fullscreenProps().positions).toEqual(original))
    })

    it('caps the full-screen graph at 50 participants across roles with one "more" node per role', async () => {
      renderGraph({
        consumers: {
          ...makeOperationConsumers([...participants(30, 'publisher'), ...participants(30, 'subscriber')]),
          publisherCount: 40,
          subscriberCount: 70,
          count: 110,
        },
      })
      await openFullscreen()

      const props = fullscreenProps()
      // 50 drawn: 30 publishers + 20 subscribers, in the response's order.
      expect(props.nodes.filter((id: string) => id.startsWith('publisher-'))).toHaveLength(30)
      expect(props.nodes.filter((id: string) => id.startsWith('subscriber-'))).toHaveLength(20)
      expect(props.moreCounts).toEqual({ 'more-publisher': 10, 'more-subscriber': 50 })
    })

    it('keeps publishers and subscribers on opposite sides of the channel in two-sided Columns', async () => {
      renderGraph({ consumers: makeOperationConsumers([...participants(12, 'publisher'), ...participants(12, 'subscriber')]) })
      await openFullscreen()

      const positions = fullscreenProps().positions as Positions
      const sides = (role: string) => Object.entries(positions).filter(([id]) => id.startsWith(`${role}-`)).map(([, position]) => position.x)
      expect(new Set(sides('publisher')).size).toBe(1)
      expect(sides('publisher').every((x) => x < 0)).toBe(true)
      expect(sides('subscriber').every((x) => x > 0)).toBe(true)
    })

    it('draws rounded step edges between node sides in full screen and straight ones inline', async () => {
      renderGraph({ consumers: makeOperationConsumers([...participants(2, 'publisher'), ...participants(2, 'subscriber')]) })
      await openFullscreen()

      const edges = fullscreenProps().edges
      expect(edges).toContainEqual(expect.objectContaining({ source: 'publisher-pub-0', sourceHandle: 'right', target: 'channel', targetHandle: 'left', type: 'smoothstep', pathOptions: { borderRadius: 16 } }))
      expect(edges).toContainEqual(expect.objectContaining({ source: 'channel', sourceHandle: 'right', target: 'subscriber-sub-0', targetHandle: 'left', type: 'smoothstep' }))
      expect(JSON.parse(screen.getAllByTestId('flow-props')[0].textContent!).edges.every((edge: { type: string }) => edge.type === 'straight')).toBe(true)
    })

    it('closes the full-screen dialog when a "more" node opens Linked services', async () => {
      renderGraph({ consumers: { ...makeOperationConsumers(participants(50, 'subscriber')), subscriberCount: 80, count: 80 } })
      await openFullscreen()

      fireEvent.click(screen.getAllByText('node-more-subscriber')[1])

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services' })
      await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(1))
    })

    it('offers no layout choice in full screen', async () => {
      renderGraph({ consumers: makeOperationConsumers([...participants(2, 'publisher'), ...participants(2, 'subscriber')]) })
      await openFullscreen()

      fireEvent.click(screen.getByLabelText('Graph settings'))
      expect(await screen.findByText('Group by: Team')).toBeTruthy()
      expect(screen.queryByText(/^Layout:/)).toBeNull()
      expect(screen.getByLabelText('Auto-layout')).toBeTruthy()
    })

    it('ignores a stored Rings choice without rewriting it', async () => {
      window.localStorage.setItem('atlas.apis.graphLayout', 'rings')
      renderGraph({ consumers: makeOperationConsumers([...participants(12, 'publisher'), ...participants(12, 'subscriber')]) })
      await openFullscreen()

      const positions = fullscreenProps().positions as Positions
      const publisherXs = Object.entries(positions).filter(([id]) => id.startsWith('publisher-')).map(([, position]) => position.x)
      expect(new Set(publisherXs).size).toBe(1)
      fireEvent.click(screen.getByLabelText('Auto-layout'))
      expect(window.localStorage.getItem('atlas.apis.graphLayout')).toBe('rings')
    })

    it('searches on the server, reveals a match beyond the cap and highlights it', async () => {
      const hidden = { service: makeServiceSummary({ id: 'hidden', name: 'zed-service', title: 'Zed' }), role: 'subscriber' as const }
      vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers([hidden]))
      renderGraph({
        consumers: {
          ...makeOperationConsumers([...participants(50, 'publisher')]),
          publisherCount: 50,
          subscriberCount: 5,
          count: 55,
        },
      })
      await openFullscreen()
      expect(fullscreenProps().moreCounts).toEqual({ 'more-subscriber': 5 })

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'zed' } })

      await waitFor(() => expect(fullscreenProps().nodes).toContain('subscriber-hidden'))
      expect(vi.mocked(operationServicesApi.consumers).mock.calls[0].slice(0, 2)).toEqual(['operation-1', { pageSize: 50, search: 'zed' }])
      const props = fullscreenProps()
      expect(props.classNames['subscriber-hidden']).toBe('dependency-graph-node-match')
      expect(props.classNames['publisher-pub-0']).toBe('dependency-graph-node-dimmed')
      expect(props.classNames.channel).toBe('')
      // The one match is drawn, so no "more" node is left for it.
      expect(props.moreCounts).toEqual({})
    })

    it('carries the search text to the Linked services tab from a "more" node', async () => {
      vi.mocked(operationServicesApi.consumers).mockResolvedValue({
        ...makeOperationConsumers(participants(50, 'subscriber', 'zed')),
        publisherCount: 0,
        subscriberCount: 60,
        count: 60,
      })
      renderGraph({
        consumers: { ...makeOperationConsumers(participants(50, 'subscriber')), subscriberCount: 80, count: 80 },
      })
      await openFullscreen()

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'zed' } })
      await waitFor(() => expect(fullscreenProps().moreCounts).toEqual({ 'more-subscriber': 10 }))
      fireEvent.click(screen.getAllByText('node-more-subscriber')[1])

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services&search=zed' })
    })

    it('shows "No matching services" when nothing matches and clears it with the search', async () => {
      vi.mocked(operationServicesApi.consumers).mockResolvedValue(makeOperationConsumers([]))
      renderGraph({ consumers: makeOperationConsumers(participants(3, 'publisher')) })
      await openFullscreen()
      const search = screen.getByPlaceholderText('Search services')

      fireEvent.change(search, { target: { value: 'nothing' } })
      await waitFor(() => expect(screen.getByText('No matching services')).toBeDefined())
      fireEvent.change(search, { target: { value: '' } })

      await waitFor(() => expect(screen.queryByText('No matching services')).toBeNull())
      expect(Object.values(fullscreenProps().classNames).every((value) => value === '')).toBe(true)
    })
    it('exports the full-screen graph as an image named after the graph', async () => {
      vi.mocked(toPng).mockResolvedValue('data:image')
      renderGraph({ consumers: makeOperationConsumers([...participants(2, 'publisher'), ...participants(2, 'subscriber')]) })
      await openFullscreen()
      // Only the full-screen view offers an export.
      expect(screen.getAllByLabelText('Export')).toHaveLength(1)

      fireEvent.click(screen.getByLabelText('Export'))
      fireEvent.click(await screen.findByText('PNG'))
      fireEvent.click(screen.getAllByRole('button', { name: 'Export' }).at(-1)!)

      await waitFor(() => expect(downloadDataUrl).toHaveBeenCalledWith('data:image', 'operation-participants.png'))
      // The exported element is the full-screen canvas, not the page.
      expect((vi.mocked(toPng).mock.calls[0][0] as HTMLElement).className).toContain('compact-dependency-graph-canvas')
    })
  })

  describe('grouped full screen', () => {
    type Participant = ReturnType<typeof makeOperationConsumers>['participants'][number]
    const participants = (count: number, role: 'publisher' | 'subscriber', prefix = role === 'publisher' ? 'pub' : 'sub'): Participant[] =>
      Array.from({ length: count }, (_, index) => ({
        service: makeServiceSummary({ id: `${prefix}-${index}`, name: `${prefix}-${index}`, title: `${prefix} ${index}` }),
        role,
      }))
    const group = (id: string, name: string, count: number) => ({ id, name, count })

    // Team A holds 3 publishers and 2 subscribers, Team C 4 subscribers; one publisher and one subscriber stand alone.
    const GROUPED = {
      ...makeOperationConsumers([...participants(1, 'publisher', 'solo-pub'), ...participants(1, 'subscriber', 'solo-sub')]),
      count: 11,
      publisherCount: 4,
      subscriberCount: 7,
      publisherGroups: [group('team-a', 'Team A', 3)],
      subscriberGroups: [group('team-a', 'Team A', 2), group('team-c', 'Team C', 4)],
      participantsCount: 2,
    }

    function mockServer(members: Record<string, Participant[]> = {}, totals: Record<string, number> = {}) {
      vi.mocked(operationServicesApi.consumers).mockImplementation(async (_id, params) => {
        if (params?.groupId) {
          const key = `${params.role}|${params.groupId}`
          return { ...makeOperationConsumers(members[key] ?? []), count: totals[key] ?? (members[key] ?? []).length }
        }
        return GROUPED
      })
    }

    async function openFullscreen() {
      fireEvent.click(screen.getByText('Full screen'))
      await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    }
    const fullscreenProps = () => JSON.parse(screen.getAllByTestId('flow-props')[1].textContent!)
    type Positions = Record<string, { x: number; y: number }>

    beforeEach(() => window.localStorage.removeItem('atlas.apis.graphGroupBy'))

    it('groups from 10 participants and not below, when nothing is stored', async () => {
      mockServer()
      renderGraph({ consumers: makeOperationConsumers([...participants(5, 'publisher'), ...participants(4, 'subscriber')]) })
      await openFullscreen()
      expect(operationServicesApi.consumers).not.toHaveBeenCalled()
      expect(fullscreenProps().groups).toEqual({})
      cleanup()

      renderGraph({ consumers: makeOperationConsumers([...participants(5, 'publisher'), ...participants(5, 'subscriber')]) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toHaveLength(3))
      expect(vi.mocked(operationServicesApi.consumers).mock.calls[0].slice(0, 2)).toEqual(['operation-1', { pageSize: 50, groupBy: 'team', search: '' }])
    })

    it('draws publisher groups on the left and subscriber groups on the right, a team on both sides with each side\'s count', async () => {
      mockServer()
      renderGraph({ consumers: makeOperationConsumers([...participants(6, 'publisher'), ...participants(6, 'subscriber')]) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toHaveLength(3))

      const props = fullscreenProps()
      expect(props.groups['group-publisher-team-a']).toMatchObject({ count: 3 })
      expect(props.groups['group-subscriber-team-a']).toMatchObject({ count: 2 })
      expect(props.groups['group-subscriber-team-c']).toMatchObject({ count: 4 })
      const positions = props.positions as Positions
      expect(positions['group-publisher-team-a'].x).toBeLessThan(0)
      expect(positions['group-subscriber-team-a'].x).toBeGreaterThan(0)
      expect(positions['group-subscriber-team-c'].x).toBeGreaterThan(0)
      // Plain participants stay on their own side, and no member is drawn while groups are collapsed.
      expect(positions['publisher-solo-pub-0'].x).toBeLessThan(0)
      expect(positions['subscriber-solo-sub-0'].x).toBeGreaterThan(0)
      expect(props.nodes).toHaveLength(1 + 3 + 2)
      // Data flows into the channel from publisher groups and out of it to subscriber groups.
      expect(props.edges).toEqual(expect.arrayContaining([
        expect.objectContaining({ id: 'group-publisher-team-a-edge', source: 'group-publisher-team-a', sourceHandle: 'right', target: 'channel', targetHandle: 'left', type: 'smoothstep' }),
        expect.objectContaining({ id: 'group-subscriber-team-c-edge', source: 'channel', sourceHandle: 'right', target: 'group-subscriber-team-c', targetHandle: 'left', type: 'smoothstep' }),
      ]))
    })

    it('expands a subscriber group by group id and role, with its block opening away from the channel', async () => {
      mockServer({ 'subscriber|team-c': participants(4, 'subscriber', 'c') })
      renderGraph({ consumers: makeOperationConsumers([...participants(6, 'publisher'), ...participants(6, 'subscriber')]) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toHaveLength(3))

      fireEvent.click(screen.getByText('node-group-subscriber-team-c'))

      await waitFor(() => expect(fullscreenProps().nodes).toContain('subscriber-c-3'))
      expect(vi.mocked(operationServicesApi.consumers).mock.calls.at(-1)!.slice(0, 2)).toEqual(
        ['operation-1', { pageSize: 50, groupBy: 'team', groupId: 'team-c', role: 'subscriber' }],
      )
      const positions = fullscreenProps().positions as Positions
      expect(positions['subscriber-c-0'].x).toBeGreaterThan(positions['group-subscriber-team-c'].x)
      expect(fullscreenProps().groups['group-subscriber-team-c'].expanded).toBe(true)
      // The same team's publisher group stays collapsed.
      expect(fullscreenProps().groups['group-publisher-team-a'].expanded).toBe(false)

      fireEvent.click(screen.getByText('node-group-subscriber-team-c'))
      await waitFor(() => expect(fullscreenProps().nodes).not.toContain('subscriber-c-0'))
    })

    it('ends an expanded group with its own "+N more" that opens Linked Services narrowed to the team', async () => {
      mockServer({ 'subscriber|team-c': participants(50, 'subscriber', 'c') }, { 'subscriber|team-c': 80 })
      renderGraph({ consumers: makeOperationConsumers([...participants(6, 'publisher'), ...participants(6, 'subscriber')]) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toHaveLength(3))

      fireEvent.click(screen.getByText('node-group-subscriber-team-c'))
      // Two plain participants take two of the 50 slots.
      await waitFor(() => expect(fullscreenProps().moreCounts).toEqual({ 'more-group-subscriber-team-c': 32 }))
      fireEvent.click(screen.getByText('node-more-group-subscriber-team-c'))

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services&team=team-c' })
    })

    it('counts "N of M matches" per role while searching and dims a group without a match', async () => {
      const searched = {
        ...GROUPED,
        count: 2,
        publisherCount: 0,
        subscriberCount: 2,
        participants: [],
        publisherGroups: [],
        subscriberGroups: [group('team-c', 'Team C', 2)],
        participantsCount: 0,
      }
      vi.mocked(operationServicesApi.consumers).mockImplementation(async (_id, params) => (params?.search ? searched : GROUPED))
      renderGraph({ consumers: makeOperationConsumers([...participants(6, 'publisher'), ...participants(6, 'subscriber')]) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toHaveLength(3))

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'notif' } })

      await waitFor(() => expect(fullscreenProps().groups['group-subscriber-team-c'].total).toBe(4))
      const props = fullscreenProps()
      expect(props.groups['group-subscriber-team-c']).toMatchObject({ count: 2, total: 4, dimmed: false })
      expect(props.groups['group-publisher-team-a']).toMatchObject({ count: 0, total: 3, dimmed: true })
      expect(props.groups['group-subscriber-team-a']).toMatchObject({ count: 0, total: 2, dimmed: true })
      expect(props.classNames['group-publisher-team-a']).toBe('dependency-graph-node-dimmed')
    })
  })
})

