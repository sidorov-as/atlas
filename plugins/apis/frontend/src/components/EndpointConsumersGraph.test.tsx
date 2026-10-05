// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { toSvg } from 'html-to-image'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadDataUrl } from 'frontend/lib/diagramExport'
import { EndpointConsumersGraph } from './EndpointConsumersGraph'
import { endpointServicesApi } from '../lib/entities'
import { makeConsumers, makeServiceSummary } from '../testFixtures'
import { DRAG_TARGET, installMemoryLocalStorage } from '../testReactFlowMock'

vi.mock('../lib/entities', () => ({ endpointServicesApi: { consumers: vi.fn() } }))

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
  vi.mocked(endpointServicesApi.consumers).mockReset()
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

  it('caps the compact inline graph at 6 Services plus a "+N more" node', () => {
    const services = Array.from({ length: 18 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    const props = JSON.parse(screen.getByTestId('flow-props').textContent!)
    // endpoint + 6 Services + more
    expect(props.nodes).toEqual(['endpoint', ...services.slice(0, 6).map((service) => service.id), 'more'])
    expect(screen.getByText('node-more')).toBeDefined()
    // The "more" node is not a Service: no edge touches it.
    expect(props.edges.every((edge: { source: string; target: string }) => edge.source !== 'more' && edge.target !== 'more')).toBe(true)
  })

  it('counts the "more" node from the total, not from the loaded page', () => {
    const services = Array.from({ length: 50 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: { ...makeConsumers(services), count: 120 } })

    // Rendered by the stubbed node component, so check the data it receives.
    expect(screen.getByTestId('flow-props').textContent).toContain('"more"')
    expect(JSON.parse(screen.getByTestId('flow-props').textContent!).nodes).toHaveLength(8)
  })

  it('draws no "more" node when 6 or fewer Services are linked', () => {
    const services = Array.from({ length: 6 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    expect(screen.queryByText('node-more')).toBeNull()
    expect(JSON.parse(screen.getByTestId('flow-props').textContent!).nodes).toHaveLength(7)
  })

  it('clicking the "more" node opens the full-screen graph and never navigates', async () => {
    const services = Array.from({ length: 18 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    fireEvent.click(screen.getByText('node-more'))

    await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    expect(navigateSpy).not.toHaveBeenCalled()
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

  it('opens the full-screen dialog showing every loaded Service without the compact cap', async () => {
    const services = Array.from({ length: 15 }, (_, index) => makeServiceSummary({ id: `service-${index}`, name: `service-${index}` }))
    renderGraph({ consumers: makeConsumers(services) })

    fireEvent.click(screen.getByText('Full screen'))

    await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    const [, fullscreenProps] = screen.getAllByTestId('flow-props').map((node) => JSON.parse(node.textContent!))
    // 15 service nodes + 1 endpoint node — no compact cap in full screen.
    expect(fullscreenProps.nodes.length).toBe(16)
  })

  it('closes the full-screen dialog via its close action, returning to the Overview tab', async () => {
    renderGraph({ consumers: makeConsumers([makeServiceSummary({ id: 'service-1' })]) })

    fireEvent.click(screen.getByText('Full screen'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(2))

    fireEvent.click(screen.getByLabelText('Close dialog'))
    await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(1))
  })

  describe('full screen', () => {
    const services = (count: number, prefix = 'service') =>
      Array.from({ length: count }, (_, index) => makeServiceSummary({ id: `${prefix}-${index}`, name: `${prefix}-${index}`, title: `${prefix} ${index}` }))

    async function openFullscreen() {
      fireEvent.click(screen.getByText('Full screen'))
      await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    }
    const fullscreenProps = () => JSON.parse(screen.getAllByTestId('flow-props')[1].textContent!)

    it('makes nodes draggable in full screen, never connectable', async () => {
      renderGraph({ consumers: makeConsumers(services(3)) })
      await openFullscreen()

      const props = fullscreenProps()
      expect(props.nodesDraggable).toBe(true)
      expect(props.nodesConnectable).toBe(false)
      expect(Object.values(props.draggable).every((value) => value === true)).toBe(true)
    })

    it('keeps a dragged node where it was dropped and Auto-layout restores every position', async () => {
      renderGraph({ consumers: makeConsumers(services(3)) })
      await openFullscreen()
      const original = fullscreenProps().positions

      fireEvent.click(screen.getAllByText('drag-service-1')[1])
      await waitFor(() => expect(fullscreenProps().positions['service-1']).toEqual(DRAG_TARGET))
      expect(fullscreenProps().positions['service-0']).toEqual(original['service-0'])

      fireEvent.click(screen.getByLabelText('Auto-layout'))
      await waitFor(() => expect(fullscreenProps().positions).toEqual(original))
    })

    it('draws at most 50 Services and a "more" node counted from the total, never navigating to a Service', async () => {
      renderGraph({ consumers: { ...makeConsumers(services(50)), count: 120 } })
      await openFullscreen()

      const props = fullscreenProps()
      expect(props.nodes).toHaveLength(1 + 50 + 1)
      expect(props.moreCounts).toEqual({ more: 70 })
      expect(props.edges.every((edge: { source: string; target: string }) => edge.source !== 'more' && edge.target !== 'more')).toBe(true)
    })

    it('opens the Linked services tab from the "more" node, without search text when none is active', async () => {
      renderGraph({ consumers: { ...makeConsumers(services(50)), count: 120 } })
      await openFullscreen()

      fireEvent.click(screen.getAllByText('node-more')[1])

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services' })
    })

    it('searches on the server, reveals a match beyond the cap and highlights it while dimming the rest', async () => {
      const hidden = makeServiceSummary({ id: 'hidden', name: 'zed-service', title: 'Zed' })
      vi.mocked(endpointServicesApi.consumers).mockResolvedValue({ ...makeConsumers([hidden]), count: 1 })
      renderGraph({ consumers: { ...makeConsumers(services(50)), count: 120 } })
      await openFullscreen()

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'zed' } })

      await waitFor(() => expect(fullscreenProps().nodes).toContain('hidden'))
      expect(endpointServicesApi.consumers).toHaveBeenCalledTimes(1)
      expect(vi.mocked(endpointServicesApi.consumers).mock.calls[0].slice(0, 2)).toEqual(['endpoint-1', { pageSize: 50, search: 'zed' }])
      const props = fullscreenProps()
      expect(props.classNames.hidden).toBe('dependency-graph-node-match')
      expect(props.classNames['service-0']).toBe('dependency-graph-node-dimmed')
      expect(props.classNames.endpoint).toBe('')
      // 50 slots: the match first, 49 of the loaded page after it.
      expect(props.nodes).toHaveLength(1 + 50)
      // Only the matches count towards "more": 1 of 1 is drawn, so none are left.
      expect(props.nodes).not.toContain('more')
    })

    it('carries the search text to the Linked services tab from the "more" node', async () => {
      const matches = services(60, 'zed')
      vi.mocked(endpointServicesApi.consumers).mockResolvedValue({ ...makeConsumers(matches.slice(0, 50)), count: 60 })
      renderGraph({ consumers: { ...makeConsumers(services(50)), count: 120 } })
      await openFullscreen()

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'zed' } })
      await waitFor(() => expect(fullscreenProps().moreCounts).toEqual({ more: 10 }))
      fireEvent.click(screen.getAllByText('node-more')[1])

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services&search=zed' })
    })

    it('shows "No matching services" and keeps every Service dimmed when nothing matches', async () => {
      vi.mocked(endpointServicesApi.consumers).mockResolvedValue({ ...makeConsumers([]), count: 0 })
      renderGraph({ consumers: makeConsumers(services(3)) })
      await openFullscreen()

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'nothing' } })

      await waitFor(() => expect(screen.getByText('No matching services')).toBeDefined())
      expect(Object.entries(fullscreenProps().classNames).filter(([id]) => id !== 'endpoint').every(([, value]) => value === 'dependency-graph-node-dimmed')).toBe(true)
    })

    it('clearing the search removes the highlighting and the nodes added only by the search', async () => {
      const hidden = makeServiceSummary({ id: 'hidden', name: 'zed-service', title: 'Zed' })
      vi.mocked(endpointServicesApi.consumers).mockResolvedValue({ ...makeConsumers([hidden]), count: 1 })
      renderGraph({ consumers: makeConsumers(services(3)) })
      await openFullscreen()
      const search = screen.getByPlaceholderText('Search services')

      fireEvent.change(search, { target: { value: 'zed' } })
      await waitFor(() => expect(fullscreenProps().nodes).toContain('hidden'))
      fireEvent.change(search, { target: { value: '' } })

      await waitFor(() => expect(fullscreenProps().nodes).not.toContain('hidden'))
      expect(Object.values(fullscreenProps().classNames).every((value) => value === '')).toBe(true)
    })

    it('debounces typing into one request and cancels the one in flight', async () => {
      vi.mocked(endpointServicesApi.consumers).mockImplementation(() => new Promise(() => {}))
      renderGraph({ consumers: makeConsumers(services(3)) })
      await openFullscreen()
      const search = screen.getByPlaceholderText('Search services')

      fireEvent.change(search, { target: { value: 'z' } })
      fireEvent.change(search, { target: { value: 'ze' } })
      await waitFor(() => expect(endpointServicesApi.consumers).toHaveBeenCalledTimes(1))
      expect(vi.mocked(endpointServicesApi.consumers).mock.calls[0][1]).toEqual({ pageSize: 50, search: 'ze' })
      const firstSignal = vi.mocked(endpointServicesApi.consumers).mock.calls[0][2] as AbortSignal

      fireEvent.change(search, { target: { value: 'zed' } })
      await waitFor(() => expect(endpointServicesApi.consumers).toHaveBeenCalledTimes(2))
      expect(firstSignal.aborted).toBe(true)
    })

    it('lays full screen out in Columns with rounded step edges between node sides, and offers no layout choice', async () => {
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()

      const props = fullscreenProps()
      const xs = new Set(Object.entries(props.positions as Record<string, { x: number }>).filter(([id]) => id !== 'endpoint').map(([, position]) => position.x))
      // 12 Services share one level, so one column.
      expect(xs.size).toBe(1)
      expect(props.edges).toHaveLength(12)
      expect(props.edges[0]).toMatchObject({ target: 'endpoint', type: 'smoothstep', sourceHandle: 'left', targetHandle: 'right', pathOptions: { borderRadius: 16 } })
      // The inline graph keeps straight edges.
      expect(JSON.parse(screen.getAllByTestId('flow-props')[0].textContent!).edges[0].type).toBe('straight')

      fireEvent.click(screen.getByLabelText('Graph settings'))
      expect(await screen.findByText('Group by: Team')).toBeTruthy()
      expect(screen.queryByText(/^Layout:/)).toBeNull()
    })

    it('closes the full-screen dialog when the "more" node opens Linked services', async () => {
      renderGraph({ consumers: { ...makeConsumers(services(50)), count: 120 } })
      await openFullscreen()

      fireEvent.click(screen.getAllByText('node-more')[1])

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services' })
      await waitFor(() => expect(screen.getAllByTestId('react-flow')).toHaveLength(1))
    })
    it('exports the full-screen graph as an image named after the graph', async () => {
      vi.mocked(toSvg).mockResolvedValue('data:image')
      renderGraph({ consumers: makeConsumers(services(3)) })
      await openFullscreen()
      // Only the full-screen view offers an export.
      expect(screen.getAllByLabelText('Export')).toHaveLength(1)

      fireEvent.click(screen.getByLabelText('Export'))
      fireEvent.click(screen.getAllByRole('button', { name: 'Export' }).at(-1)!)

      await waitFor(() => expect(downloadDataUrl).toHaveBeenCalledWith('data:image', 'endpoint-consumers.svg'))
      // The exported element is the full-screen canvas, not the page.
      expect((vi.mocked(toSvg).mock.calls[0][0] as HTMLElement).className).toContain('compact-dependency-graph-canvas')
    })
  })

  describe('grouped full screen', () => {
    const services = (count: number, prefix = 'service', overrides: Partial<ReturnType<typeof makeServiceSummary>> = {}) =>
      Array.from({ length: count }, (_, index) => makeServiceSummary({ id: `${prefix}-${index}`, name: `${prefix}-${index}`, title: `${prefix} ${index}`, ...overrides }))
    const group = (id: string, name: string, count: number) => ({ id, name, count })

    function groupedResponse(groups: ReturnType<typeof group>[], plain: ReturnType<typeof services>) {
      return {
        ...makeConsumers(plain),
        count: groups.reduce((sum, item) => sum + item.count, 0) + plain.length,
        groups,
        servicesCount: plain.length,
      }
    }

    const BASE_GROUPS = [group('team-a', 'Team A', 6), group('team-b', 'Team B', 5)]
    const BASE_PLAIN = services(1, 'solo')
    /** Answers grouped, searched and per-group requests from three small tables. */
    function mockServer(options: { members?: Record<string, ReturnType<typeof services>>; memberTotals?: Record<string, number>; searched?: ReturnType<typeof groupedResponse> } = {}) {
      vi.mocked(endpointServicesApi.consumers).mockImplementation(async (_id, params) => {
        if (params?.groupId) {
          const members = options.members?.[params.groupId] ?? []
          return { ...makeConsumers(members), count: options.memberTotals?.[params.groupId] ?? members.length }
        }
        if (params?.search && options.searched) return options.searched
        return groupedResponse(BASE_GROUPS, BASE_PLAIN)
      })
    }

    async function openFullscreen() {
      fireEvent.click(screen.getByText('Full screen'))
      await waitFor(() => expect(screen.getAllByTestId('flow-props')).toHaveLength(2))
    }
    const fullscreenProps = () => JSON.parse(screen.getAllByTestId('flow-props')[1].textContent!)
    const callsWith = (key: string) => vi.mocked(endpointServicesApi.consumers).mock.calls.filter(([, params]) => Boolean((params as Record<string, unknown> | undefined)?.[key]))

    beforeEach(() => window.localStorage.removeItem('atlas.apis.graphGroupBy'))

    it('opens grouped by Team from 10 Services and ungrouped below, when nothing is stored', async () => {
      mockServer()
      renderGraph({ consumers: makeConsumers(services(9)) })
      await openFullscreen()
      expect(endpointServicesApi.consumers).not.toHaveBeenCalled()
      expect(fullscreenProps().nodes).toHaveLength(1 + 9)
      cleanup()

      renderGraph({ consumers: makeConsumers(services(10)) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toEqual(['group-team-a', 'group-team-b']))
      expect(vi.mocked(endpointServicesApi.consumers).mock.calls[0].slice(0, 2)).toEqual(['endpoint-1', { pageSize: 50, groupBy: 'team', search: '' }])
    })

    it('draws one node per group with its exact size, folds a lone Service into a plain node and draws no member', async () => {
      mockServer()
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()

      const props = fullscreenProps()
      expect(props.groups['group-team-a']).toMatchObject({ name: 'Team A', count: 6, expanded: false, dimmed: false })
      expect(props.groups['group-team-b']).toMatchObject({ count: 5 })
      expect(props.nodes).toEqual(['endpoint', 'group-team-a', 'group-team-b', 'solo-0'])
      expect(props.edges).toEqual(expect.arrayContaining([
        expect.objectContaining({ id: 'group-team-a-endpoint', source: 'group-team-a', target: 'endpoint', type: 'smoothstep', sourceHandle: 'left', targetHandle: 'right' }),
        expect.objectContaining({ id: 'solo-0-endpoint', source: 'solo-0', target: 'endpoint', type: 'smoothstep' }),
      ]))
    })

    it('keeps a Service without a system visible when grouping by System', async () => {
      mockServer()
      window.localStorage.setItem('atlas.apis.graphGroupBy', 'system')
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()

      await waitFor(() => expect(fullscreenProps().nodes).toContain('solo-0'))
      expect(vi.mocked(endpointServicesApi.consumers).mock.calls[0][1]).toMatchObject({ groupBy: 'system' })
    })

    it('remembers a chosen grouping, and an explicit None beats the default', async () => {
      mockServer()
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(Object.keys(fullscreenProps().groups)).toHaveLength(2))

      fireEvent.click(screen.getByLabelText('Graph settings'))
      fireEvent.click(await screen.findByText('Group by: System'))
      await waitFor(() => expect(window.localStorage.getItem('atlas.apis.graphGroupBy')).toBe('system'))
      await waitFor(() => expect(callsWith('groupBy').some(([, params]) => (params as { groupBy: string }).groupBy === 'system')).toBe(true))

      fireEvent.click(screen.getByLabelText('Graph settings'))
      fireEvent.click(await screen.findByText('No grouping'))
      await waitFor(() => expect(window.localStorage.getItem('atlas.apis.graphGroupBy')).toBe('none'))
      await waitFor(() => expect(fullscreenProps().nodes).toHaveLength(1 + 12))
      cleanup()

      renderGraph({ consumers: { ...makeConsumers(services(40)), count: 40 } })
      await openFullscreen()
      expect(fullscreenProps().groups).toEqual({})
    })

    it('expands a group in place from its own request, collapses it again and reuses the cached page', async () => {
      mockServer({ members: { 'team-a': services(6, 'a') } })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('a-5'))
      expect(callsWith('groupId')).toHaveLength(1)
      expect(callsWith('groupId')[0].slice(0, 2)).toEqual(['endpoint-1', { pageSize: 50, groupBy: 'team', groupId: 'team-a' }])
      let props = fullscreenProps()
      expect(props.groups['group-team-a'].expanded).toBe(true)
      // The other groups stay, and members hang off the group node.
      expect(props.nodes).toEqual(expect.arrayContaining(['group-team-b', 'solo-0']))
      expect(props.edges).toContainEqual(expect.objectContaining({ id: 'a-0-group-team-a', source: 'a-0', target: 'group-team-a', type: 'smoothstep', sourceHandle: 'left', targetHandle: 'right' }))

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).not.toContain('a-0'))
      expect(fullscreenProps().groups['group-team-a'].expanded).toBe(false)

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('a-0'))
      expect(callsWith('groupId')).toHaveLength(1)
      props = fullscreenProps()
      expect(props.nodes.filter((id: string) => id.startsWith('a-'))).toHaveLength(6)
    })

    it('opens several groups at once without any two nodes sharing a position', async () => {
      mockServer({ members: { 'team-a': services(6, 'a'), 'team-b': services(5, 'b') } })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('a-0'))
      fireEvent.click(screen.getByText('node-group-team-b'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('b-0'))

      const props = fullscreenProps()
      expect(props.nodes.filter((id: string) => /^[ab]-\d/.test(id))).toHaveLength(11)
      const positions = Object.values(props.positions as Record<string, { x: number; y: number }>).map((position) => `${position.x},${position.y}`)
      expect(new Set(positions).size).toBe(positions.length)
    })

    it('draws at most 50 Services across plain and expanded ones and ends a group\'s block with its own "+N more"', async () => {
      mockServer({ members: { 'team-a': services(50, 'a') }, memberTotals: { 'team-a': 70 } })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().moreCounts).toEqual({ 'more-group-team-a': 21 }))

      const props = fullscreenProps()
      // The one plain Service takes a slot, so 49 of the group's 50 loaded members fit.
      expect(props.nodes.filter((id: string) => id.startsWith('a-'))).toHaveLength(49)
      expect(props.edges.every((edge: { source: string; target: string }) => !edge.source.startsWith('more') && !edge.target.startsWith('more'))).toBe(true)
      // Group nodes are not counted: 2 groups + 50 Services + endpoint + more.
      expect(props.nodes).toHaveLength(1 + 2 + 50 + 1)

      fireEvent.click(screen.getByText('node-more-group-team-a'))
      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services&team=team-a' })
    })

    it('opens Linked Services with the system name as search from a system group\'s "+N more"', async () => {
      window.localStorage.setItem('atlas.apis.graphGroupBy', 'system')
      mockServer({ members: { 'team-a': services(50, 'a') }, memberTotals: { 'team-a': 70 } })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().moreCounts['more-group-team-a']).toBeDefined())
      fireEvent.click(screen.getByText('node-more-group-team-a'))

      expect(navigateSpy).toHaveBeenCalledWith({ search: '?tab=services&search=Team+A' })
    })

    it('searches with groups: counts "N of M", dims a group without a match, never expands, and clearing restores', async () => {
      const searched = groupedResponse([group('team-a', 'Team A', 2)], [])
      mockServer({ searched })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'pay' } })

      await waitFor(() => expect(fullscreenProps().groups['group-team-a'].total).toBe(6))
      let props = fullscreenProps()
      expect(props.groups['group-team-a']).toMatchObject({ count: 2, total: 6, expanded: false, dimmed: false })
      expect(props.groups['group-team-b']).toMatchObject({ count: 0, total: 5, dimmed: true })
      expect(props.classNames['group-team-b']).toBe('dependency-graph-node-dimmed')
      expect(props.classNames['group-team-a']).toBe('')
      expect(callsWith('groupId')).toHaveLength(0)
      expect(vi.mocked(endpointServicesApi.consumers).mock.calls.at(-1)![1]).toEqual({ pageSize: 50, groupBy: 'team', search: 'pay' })

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: '' } })
      await waitFor(() => expect(fullscreenProps().groups['group-team-a'].total).toBeUndefined())
      props = fullscreenProps()
      expect(props.groups['group-team-a'].count).toBe(6)
      expect(Object.values(props.classNames).every((value) => value === '')).toBe(true)
    })

    it('counts a single match from the plain list and highlights matches in an expanded group', async () => {
      const matching = makeServiceSummary({ id: 'a-1', name: 'pay-a', title: 'Pay A', teamId: 'team-a' })
      const searched = groupedResponse([], [matching])
      mockServer({ searched, members: { 'team-a': [makeServiceSummary({ id: 'a-0', name: 'misc', title: 'Misc' }), matching] } })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())
      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('a-1'))

      fireEvent.change(screen.getByPlaceholderText('Search services'), { target: { value: 'pay' } })

      // The search text change collapses the group; its one match is counted on the group, not drawn alone.
      await waitFor(() => expect(fullscreenProps().groups['group-team-a'].total).toBe(6))
      const props = fullscreenProps()
      expect(props.groups['group-team-a']).toMatchObject({ count: 1, total: 6, expanded: false, dimmed: false })
      expect(props.nodes).not.toContain('a-1')

      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('a-1'))
      expect(fullscreenProps().classNames['a-1']).toBe('dependency-graph-node-match')
      expect(fullscreenProps().classNames['a-0']).toBe('dependency-graph-node-dimmed')
      // The group's page came from the cache, requested without the search.
      expect(callsWith('groupId')).toHaveLength(1)
    })

    it('collapses every group when the grouping changes', async () => {
      mockServer({ members: { 'team-a': services(6, 'a') } })
      renderGraph({ consumers: makeConsumers(services(12)) })
      await openFullscreen()
      await waitFor(() => expect(fullscreenProps().groups['group-team-a']).toBeDefined())
      fireEvent.click(screen.getByText('node-group-team-a'))
      await waitFor(() => expect(fullscreenProps().nodes).toContain('a-0'))

      fireEvent.click(screen.getByLabelText('Graph settings'))
      fireEvent.click(await screen.findByText('Group by: System'))

      await waitFor(() => expect(fullscreenProps().nodes).not.toContain('a-0'))
      expect(fullscreenProps().groups['group-team-a'].expanded).toBe(false)
    })
  })
})
