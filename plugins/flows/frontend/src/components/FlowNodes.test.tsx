// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NodeProps } from '@xyflow/react'
import { CallNode, EntityFlowNode, EventNode, ExternalNode, FlowRefNode, LinkNode, StepNode } from './FlowNodes'
import { componentTypeColors, apiTypeColors, resourceTypeColors, FLOW_NODE_PALETTE, NEUTRAL_COLORS } from '../lib/flowNodePalette'
import { apiTypeIcon, componentTypeIcon, resourceTypeIcon, EXTERNAL_KIND_HELP_TEXT, FLOW_NODE_KIND_ICONS, FLOW_NODE_KIND_LABELS, type FlowNodeKind } from '../lib/flowNodeKind'
import type { FlowNode, FlowNodeData } from '../lib/flowLayout'
import type { FlowStep, FlowStepRefStatus } from 'frontend/lib/types'

const { componentsApiList, apisApiList, resourcesApiList, flowsApiGet } = vi.hoisted(() => ({
  componentsApiList: vi.fn(),
  apisApiList: vi.fn(),
  resourcesApiList: vi.fn(),
  flowsApiGet: vi.fn(),
}))
vi.mock('frontend/lib/entities', () => ({
  componentsApi: { list: componentsApiList },
  apisApi: { list: apisApiList },
  resourcesApi: { list: resourcesApiList },
  flowsApi: { get: flowsApiGet },
}))

/** Wraps a single search-result item the way `componentsApi.list`/`apisApi.list` shape their response (`Paginated<T>`), for `entitySubtype.ts`'s `q`-search resolution. */
function searchResult(name: string, type: string) {
  return { page: { objectList: [{ metadata: { name }, spec: { type } }] } }
}

afterEach(() => cleanup())

// `Handle` needs no real behavior here — these tests only exercise each
// node's own rendered content, not React Flow's edge-anchoring (mirrors
// EndpointConsumerNodes.test.tsx's approach for the same reason).
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return { ...actual, Handle: () => null }
})

// `Icon` renders inline SVG with no attribute identifying which
// `@gravity-ui/icons` component it was given, so identity is captured here
// instead — `data.name` is the icon component's own function name (e.g.
// `Bell`, `Flag`), which is exactly what `stepIcon`/`FLOW_NODE_KIND_ICONS`
// resolve to.
vi.mock('@gravity-ui/uikit', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@gravity-ui/uikit')>()
  return {
    ...actual,
    Icon: ({ data }: { data: { name?: string } }) => <span data-testid="chip-icon" data-icon-name={data.name} />,
  }
})

function nodeProps(step: FlowStep, type: FlowNodeKind, refStatus?: FlowStepRefStatus): NodeProps<FlowNode> {
  return { id: step.id, type, data: { step, refStatus } as FlowNodeData } as unknown as NodeProps<FlowNode>
}

function renderNode(Component: typeof EntityFlowNode, step: FlowStep, type: FlowNodeKind, refStatus?: FlowStepRefStatus) {
  return render(
    <ThemeProvider theme="light">
      {/* Always present, not just for FlowRefNode's navigate-control tests below — harmless for
        every other kind, and a Flow node's navigate control (react-router-dom's `Link`) needs a
        Router context to render at all. */}
      <MemoryRouter>
        <Component {...nodeProps(step, type, refStatus)} />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

// Component/API/Data are excluded here — their real per-subtype icon/color
// is covered separately below, not a fixed
// `FLOW_NODE_PALETTE` entry.
const FIXED_KINDS: Exclude<FlowNodeKind, 'step' | 'call' | 'event' | 'component' | 'api' | 'data'>[] = ['actor', 'team', 'system', 'external']

describe('fixed-kind node border and chip color', () => {
  it.each(FIXED_KINDS)('renders %s with its palette color on both border and chip', (kind) => {
    const Component = kind === 'external' ? ExternalNode : EntityFlowNode
    const { container } = renderNode(Component, { id: 'n1', title: 'Node title' }, kind)

    const card = container.querySelector('div')
    expect(card?.getAttribute('style')).toContain(FLOW_NODE_PALETTE[kind].border)

    const chip = screen.getByText(FLOW_NODE_KIND_LABELS[kind])
    expect(chip.closest('[class*="label_theme_"]')?.className).toContain(`label_theme_${FLOW_NODE_PALETTE[kind].theme}`)
    expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(FLOW_NODE_KIND_ICONS[kind].name)
  })
})

describe('Component/API/Data node real-subtype icon and color', () => {
  it('renders a Component with no entity_ref with the neutral fallback (unresolved)', () => {
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title' }, 'component')

    expect(container.querySelector('div')?.getAttribute('style')).toContain(NEUTRAL_COLORS.border)
    expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(componentTypeIcon(undefined).name)
  })

  it('renders a website-typed Component with Website\'s icon/color, not Service\'s', async () => {
    componentsApiList.mockResolvedValueOnce(searchResult('website-svc', 'website'))
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title', entity_ref: 'component:website-svc' }, 'component')

    await waitFor(() => expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(componentTypeIcon('website').name))

    expect(componentsApiList).toHaveBeenCalledWith({ q: 'website-svc', pageSize: 100 })
    expect(container.querySelector('div')?.getAttribute('style')).toContain(componentTypeColors('website').border)
    expect(container.querySelector('div')?.getAttribute('style')).not.toContain(componentTypeColors('service').border)
  })

  it('renders a worker-typed Component with Worker\'s icon/color, not Service\'s', async () => {
    componentsApiList.mockResolvedValueOnce(searchResult('worker-svc', 'worker'))
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title', entity_ref: 'component:worker-svc' }, 'component')

    await waitFor(() => expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(componentTypeIcon('worker').name))

    expect(container.querySelector('div')?.getAttribute('style')).toContain(componentTypeColors('worker').border)
    expect(container.querySelector('div')?.getAttribute('style')).not.toContain(componentTypeColors('service').border)
  })

  it('renders a grpc-typed API with gRPC\'s icon/color, not a generic API color', async () => {
    apisApiList.mockResolvedValueOnce(searchResult('grpc-api', 'grpc'))
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title', entity_ref: 'api:grpc-api' }, 'api')

    await waitFor(() => expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(apiTypeIcon('grpc').name))

    expect(apisApiList).toHaveBeenCalledWith({ q: 'grpc-api', pageSize: 100 })
    expect(container.querySelector('div')?.getAttribute('style')).toContain(apiTypeColors('grpc').border)
    expect(container.querySelector('div')?.getAttribute('style')).not.toContain(FLOW_NODE_PALETTE.api.border)
  })

  it('falls back to the neutral color when the q-search returns no exact name match', async () => {
    componentsApiList.mockResolvedValueOnce(searchResult('some-other-component', 'service'))
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title', entity_ref: 'component:missing-svc' }, 'component')

    await waitFor(() => expect(componentsApiList).toHaveBeenCalled())
    expect(container.querySelector('div')?.getAttribute('style')).toContain(NEUTRAL_COLORS.border)
  })

  it('renders a Data node with no entity_ref with the neutral fallback (unresolved)', () => {
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title' }, 'data')

    expect(container.querySelector('div')?.getAttribute('style')).toContain(NEUTRAL_COLORS.border)
    expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(resourceTypeIcon(undefined).name)
  })

  it('renders a bucket-typed Data node with Bucket\'s icon/color, not Database\'s', async () => {
    resourcesApiList.mockResolvedValueOnce(searchResult('my-bucket', 'bucket'))
    const { container } = renderNode(EntityFlowNode, { id: 'n1', title: 'Node title', entity_ref: 'resource:my-bucket' }, 'data')

    await waitFor(() => expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(resourceTypeIcon('bucket').name))

    expect(resourcesApiList).toHaveBeenCalledWith({ q: 'my-bucket', pageSize: 100 })
    expect(container.querySelector('div')?.getAttribute('style')).toContain(resourceTypeColors('bucket').border)
    expect(container.querySelector('div')?.getAttribute('style')).not.toContain(resourceTypeColors('database').border)
  })
})

describe('CallNode/EventNode chip text', () => {
  it('renders a POST API Call node\'s chip with the method itself, not the generic "API Call" label', () => {
    const step: FlowStep = { id: 'n1', title: 'Node title', query_ref: { api: 'a', endpoint: 'e', method: 'POST', path: '/foo' } }
    renderNode(CallNode, step, 'call')

    expect(screen.getByText('POST')).toBeTruthy()
    expect(screen.queryByText(FLOW_NODE_KIND_LABELS.call)).toBeNull()
  })

  it('falls back to the generic "API Call" label when query_ref is unresolved', () => {
    const step: FlowStep = { id: 'n1', title: 'Node title' }
    renderNode(CallNode, step, 'call')

    expect(screen.getByText(FLOW_NODE_KIND_LABELS.call)).toBeTruthy()
  })

  it('renders a send Event node\'s chip title-cased as "Send", not the generic "Event" label', () => {
    const step: FlowStep = { id: 'n1', title: 'Node title', event_ref: { api: 'a', operation: 'o', direction: 'send', channel: 'ch' } }
    renderNode(EventNode, step, 'event')

    expect(screen.getByText('Send')).toBeTruthy()
    expect(screen.queryByText(FLOW_NODE_KIND_LABELS.event)).toBeNull()
  })

  it('falls back to the generic "Event" label when event_ref is unresolved', () => {
    const step: FlowStep = { id: 'n1', title: 'Node title' }
    renderNode(EventNode, step, 'event')

    expect(screen.getByText(FLOW_NODE_KIND_LABELS.event)).toBeTruthy()
  })
})

describe('entity-backed node title/subtitle render the live catalog data, never the step\'s own fields', () => {
  it('renders the live title/description from refStatus, not any value stored on the step', () => {
    const step: FlowStep = { id: 'n1', entity_ref: 'resource:booking-db' }
    renderNode(EntityFlowNode, step, 'data', { status: 'active', deprecated: false, title: 'Booking Database', description: 'Stores booking records.' })

    expect(screen.getByText('Booking Database')).toBeTruthy()
    expect(screen.getByText('Stores booking records.')).toBeTruthy()
  })

  it('falls back to the referenced entity\'s raw name when the live title is blank', () => {
    const step: FlowStep = { id: 'n1', entity_ref: 'resource:booking-db' }
    renderNode(EntityFlowNode, step, 'data', { status: 'active', deprecated: false, title: '', description: '' })

    expect(screen.getByText('booking-db')).toBeTruthy()
  })

  it('falls back to the raw ref name (parsed from entity_ref, no fetch needed) when the reference no longer resolves at all (no refStatus entry)', () => {
    const step: FlowStep = { id: 'n1', entity_ref: 'resource:does-not-exist' }
    renderNode(EntityFlowNode, step, 'data')

    expect(screen.getByText('does-not-exist')).toBeTruthy()
  })

  it('falls back to the step id when there is no entity_ref at all', () => {
    const step: FlowStep = { id: 'n1' }
    renderNode(EntityFlowNode, step, 'data')

    expect(screen.getByText('n1')).toBeTruthy()
  })

  it('shows no subtitle when the live description is blank', () => {
    renderNode(
      EntityFlowNode,
      { id: 'n1', entity_ref: 'resource:booking-db' },
      'data',
      { status: 'active', deprecated: false, title: 'Booking Database', description: '' },
    )

    expect(screen.queryByText('booking-db')).toBeNull()
  })

  it('falls back to a client-side fetch of the entity\'s title/description when there is no refStatus entry yet — e.g. a step just added in the current edit session, before any save', async () => {
    componentsApiList.mockResolvedValueOnce({
      page: { objectList: [{ metadata: { name: 'search-service', title: 'Search Service', description: 'Executes guest listing queries.' } }] },
    })
    const step: FlowStep = { id: 'n1', entity_ref: 'component:search-service' }
    renderNode(EntityFlowNode, step, 'component')

    await waitFor(() => expect(screen.getByText('Search Service')).toBeTruthy())
    expect(screen.getByText('Executes guest listing queries.')).toBeTruthy()
  })

  it('prefers the server-resolved refStatus over the client-side fetch once refStatus is present, and skips the fetch entirely', () => {
    // A non-subtyped kind (unlike Component/API) so `useEntitySubtype` itself never fetches —
    // isolates this assertion to the title/subtitle fallback's own gating.
    const callsBefore = componentsApiList.mock.calls.length
    const step: FlowStep = { id: 'n1', entity_ref: 'resource:booking-db' }
    renderNode(EntityFlowNode, step, 'data', { status: 'active', deprecated: false, title: 'Booking DB', description: 'Stores reservation state.' })

    expect(screen.getByText('Booking DB')).toBeTruthy()
    expect(componentsApiList.mock.calls.length).toBe(callsBefore)
  })
})

describe('Call/Event title and subtitle are always derived from the ref snapshot itself, never author-typed text', () => {
  it('renders a Call node\'s title as method+path and subtitle as the owning API\'s raw name when the picked Endpoint has no summary', () => {
    const step: FlowStep = { id: 'n1', query_ref: { api: 'api:payment-service', endpoint: 'e', method: 'POST', path: '/bookings' } }
    renderNode(CallNode, step, 'call')

    expect(screen.getByText('POST /bookings')).toBeTruthy()
    expect(screen.getByText('payment-service')).toBeTruthy()
  })

  it('renders an Event node\'s title as channel+direction and subtitle as the owning API\'s raw name when the picked Operation has no summary', () => {
    const step: FlowStep = { id: 'n1', event_ref: { api: 'api:booking-events', operation: 'o', direction: 'send', channel: 'orders.created' } }
    renderNode(EventNode, step, 'event')

    expect(screen.getByText('orders.created (send)')).toBeTruthy()
    expect(screen.getByText('booking-events')).toBeTruthy()
  })

  it('prefers the picked Endpoint\'s own summary as a Call node\'s subtitle over the owning API\'s raw name', () => {
    const step: FlowStep = { id: 'n1', query_ref: { api: 'api:payment-service', endpoint: 'e', method: 'POST', path: '/bookings', summary: 'Create a booking' } }
    renderNode(CallNode, step, 'call')

    expect(screen.getByText('Create a booking')).toBeTruthy()
    expect(screen.queryByText('payment-service')).toBeNull()
  })

  it('prefers the picked Operation\'s own summary as an Event node\'s subtitle over the owning API\'s raw name', () => {
    const step: FlowStep = { id: 'n1', event_ref: { api: 'api:booking-events', operation: 'o', direction: 'send', channel: 'orders.created', summary: 'Emitted when an order is created' } }
    renderNode(EventNode, step, 'event')

    expect(screen.getByText('Emitted when an order is created')).toBeTruthy()
    expect(screen.queryByText('booking-events')).toBeNull()
  })

  it('falls back to the step id and no subtitle for a Call node with no query_ref yet (in-progress add)', () => {
    const step: FlowStep = { id: 'n1' }
    renderNode(CallNode, step, 'call')

    expect(screen.getByText('n1')).toBeTruthy()
  })

  it('falls back to the step id and no subtitle for an Event node with no event_ref yet (in-progress add)', () => {
    const step: FlowStep = { id: 'n1' }
    renderNode(EventNode, step, 'event')

    expect(screen.getByText('n1')).toBeTruthy()
  })
})

describe('stale-reference warning icon', () => {
  const callStep: FlowStep = { id: 'n1', title: 'Node title', query_ref: { api: 'a', endpoint: 'e', method: 'POST', path: '/foo' } }
  const eventStep: FlowStep = { id: 'n1', title: 'Node title', event_ref: { api: 'a', operation: 'o', direction: 'send', channel: 'ch' } }

  it('shows no warning on a Call node with no refStatus', () => {
    renderNode(CallNode, callStep, 'call')

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })

  it('shows a warning with an explanatory tooltip on a Call node whose Endpoint was removed', () => {
    renderNode(CallNode, callStep, 'call', { status: 'removed' })

    expect(screen.getAllByTestId('chip-icon')).toHaveLength(2)
    expect(screen.getByLabelText(/removed from the API/)).toBeTruthy()
  })

  it('renders the warning icon inline beside the chip, not absolutely positioned over it', () => {
    renderNode(CallNode, callStep, 'call', { status: 'removed' })

    const warning = screen.getByLabelText(/removed from the API/)
    expect(warning.getAttribute('style')).not.toContain('position: absolute')
    // Same row as the chip (POST), not a separate corner overlay.
    expect(warning.parentElement?.textContent).toContain('POST')
  })

  it('shows a warning with an explanatory tooltip on a Call node whose Endpoint is deprecated', () => {
    renderNode(CallNode, callStep, 'call', { status: 'active', deprecated: true })

    expect(screen.getAllByTestId('chip-icon')).toHaveLength(2)
    expect(screen.getByLabelText(/deprecated/)).toBeTruthy()
  })

  it('shows no warning on a Call node whose Endpoint is active and not deprecated', () => {
    renderNode(CallNode, callStep, 'call', { status: 'active', deprecated: false })

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })

  it('shows a warning with an explanatory tooltip on an Event node whose Operation was removed', () => {
    renderNode(EventNode, eventStep, 'event', { status: 'removed' })

    expect(screen.getAllByTestId('chip-icon')).toHaveLength(2)
    expect(screen.getByLabelText(/removed from the API/)).toBeTruthy()
  })

  it('shows no warning on an Event node with no refStatus', () => {
    renderNode(EventNode, eventStep, 'event')

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })

  const entityStep: FlowStep = { id: 'n1', title: 'Node title', entity_ref: 'component:checkout' }

  it('shows no warning on an entity node with no refStatus', () => {
    renderNode(EntityFlowNode, entityStep, 'component')

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })

  it('shows a warning with an explanatory tooltip on an entity node whose target was removed', () => {
    renderNode(EntityFlowNode, entityStep, 'component', { status: 'removed' })

    expect(screen.getAllByTestId('chip-icon')).toHaveLength(2)
    expect(screen.getByLabelText(/removed from the catalog/)).toBeTruthy()
  })

  it('shows a warning with an explanatory tooltip on an entity node whose target is deprecated', () => {
    renderNode(EntityFlowNode, entityStep, 'component', { status: 'active', deprecated: true })

    expect(screen.getAllByTestId('chip-icon')).toHaveLength(2)
    expect(screen.getByLabelText(/deprecated/)).toBeTruthy()
  })

  it('shows no warning on an entity node whose target is active and not deprecated', () => {
    renderNode(EntityFlowNode, entityStep, 'component', { status: 'active', deprecated: false })

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })

  it('distinguishes the removed-entity and deprecated-entity tooltips from the API-sourced ones', () => {
    renderNode(EntityFlowNode, entityStep, 'system', { status: 'removed' })

    expect(screen.getByLabelText(/removed from the catalog/)).toBeTruthy()
    expect(screen.queryByLabelText(/removed from the API/)).toBeNull()
  })
})

describe('event direction/channel drift warning + refresh control', () => {
  const eventStep: FlowStep = { id: 'n1', title: 'Node title', event_ref: { api: 'a', operation: 'o', direction: 'send', channel: 'orders.created' } }

  it('shows a drift line even when the Operation is active and not deprecated', () => {
    renderNode(EventNode, eventStep, 'event', { status: 'active', deprecated: false, live: { direction: 'receive', channel_address: 'orders.events' } })

    expect(screen.getByLabelText(/Live operation is now receive orders\.events/)).toBeTruthy()
  })

  it('stacks the removed line and the drift line together, not one replacing the other', () => {
    renderNode(EventNode, eventStep, 'event', { status: 'removed', live: { direction: 'receive', channel_address: 'orders.events' } })

    const warning = screen.getByLabelText(/removed from the API/)
    expect(warning.getAttribute('aria-label')).toContain('removed from the API')
    expect(warning.getAttribute('aria-label')).toContain('Live operation is now receive orders.events')
  })

  it('shows no refresh control when there is no drift', () => {
    renderNode(EventNode, eventStep, 'event', { status: 'active', deprecated: false })

    expect(screen.queryByLabelText('Refresh from live operation')).toBeNull()
  })

  it('shows no refresh control on a Call node when there is no summary drift', () => {
    const callStep: FlowStep = { id: 'n1', title: 'Node title', query_ref: { api: 'a', endpoint: 'e', method: 'GET', path: '/foo' } }
    renderNode(CallNode, callStep, 'call', { status: 'active', deprecated: false })

    expect(screen.queryByLabelText('Refresh from live endpoint')).toBeNull()
    expect(screen.queryByLabelText('Refresh from live operation')).toBeNull()
  })

  it('renders the refresh control next to the warning when drift is present, and clicking it calls onRefresh with the step id', () => {
    const onRefresh = vi.fn()
    render(
      <ThemeProvider theme="light">
        <EventNode
          {...nodeProps(eventStep, 'event', { status: 'active', deprecated: false, live: { direction: 'receive', channel_address: 'orders.events' } })}
          data={{ step: eventStep, onRefresh, refStatus: { status: 'active', deprecated: false, live: { direction: 'receive', channel_address: 'orders.events' } } } as never}
        />
      </ThemeProvider>,
    )

    const refreshButton = screen.getByLabelText('Refresh from live operation')
    fireEvent.click(refreshButton)

    expect(onRefresh).toHaveBeenCalledWith('n1')
  })
})

describe('query_ref/event_ref summary drift warning + refresh control', () => {
  const eventStep: FlowStep = { id: 'n1', event_ref: { api: 'a', operation: 'o', direction: 'send', channel: 'orders.created', summary: 'Old summary' } }
  const callStep: FlowStep = { id: 'n1', query_ref: { api: 'a', endpoint: 'e', method: 'GET', path: '/foo', summary: 'Old summary' } }

  it('shows an Event node\'s summary drift line, independent of any direction/channel drift', () => {
    renderNode(EventNode, eventStep, 'event', { status: 'active', deprecated: false, live: { summary: 'New summary' } })

    expect(screen.getByLabelText(/Live operation summary is now "New summary"/)).toBeTruthy()
  })

  it('shows a Call node\'s summary drift line and a refresh control, clicking which calls onRefresh with the step id', () => {
    const onRefresh = vi.fn()
    render(
      <ThemeProvider theme="light">
        <CallNode
          {...nodeProps(callStep, 'call', { status: 'active', deprecated: false, live: { summary: 'New summary' } })}
          data={{ step: callStep, onRefresh, refStatus: { status: 'active', deprecated: false, live: { summary: 'New summary' } } } as never}
        />
      </ThemeProvider>,
    )

    expect(screen.getByLabelText(/Live endpoint summary is now "New summary"/)).toBeTruthy()
    const refreshButton = screen.getByLabelText('Refresh from live endpoint')
    fireEvent.click(refreshButton)

    expect(onRefresh).toHaveBeenCalledWith('n1')
  })

  it('shows no Call refresh control for a status-only warning (removed), since summary has not drifted', () => {
    renderNode(CallNode, callStep, 'call', { status: 'removed' })

    expect(screen.getByLabelText(/removed from the API/)).toBeTruthy()
    expect(screen.queryByLabelText('Refresh from live endpoint')).toBeNull()
  })
})

describe('External node clarifying tooltip', () => {
  it('carries the External/catalog-tag clarification as an aria-label on its chip', () => {
    const step: FlowStep = { id: 'n1', title: 'Node title', external_label: 'Payment Gateway' }
    renderNode(ExternalNode, step, 'external')

    expect(screen.getByLabelText(EXTERNAL_KIND_HELP_TEXT)).toBeTruthy()
  })
})

describe('card content top-anchoring', () => {
  it('top-anchors chip/title (not block-centered) on a Step with a subtitle', () => {
    const step: FlowStep = { id: 'step-1', title: 'Retry payment', summary: 'Retries the failed charge' }
    const { container } = renderNode(StepNode, step, 'step')

    expect(container.querySelector('div')?.getAttribute('style')).toContain('justify-content: flex-start')
  })

  it('top-anchors chip/title the same way on a Step with no subtitle, instead of re-centering the shrunk content', () => {
    const step: FlowStep = { id: 'step-1', title: 'Retry payment' }
    const { container } = renderNode(StepNode, step, 'step')

    const style = container.querySelector('div')?.getAttribute('style')
    expect(style).toContain('justify-content: flex-start')
    expect(style).not.toContain('justify-content: center')
  })
})

describe('StepNode', () => {
  it('renders a chosen color and icon on both its border and its chip', () => {
    const step: FlowStep = { id: 'step-1', title: 'Retry payment', color: 'danger', icon: 'Bell' }
    const { container } = renderNode(StepNode, step, 'step')

    const card = container.querySelector('div')
    expect(card?.getAttribute('style')).toContain('var(--g-color-line-danger)')

    const chip = screen.getByText(FLOW_NODE_KIND_LABELS.step)
    expect(chip.closest('[class*="label_theme_"]')?.className).toContain('label_theme_danger')
    expect(screen.getByTestId('chip-icon').dataset.iconName).toBe('Bell')
  })

  it('falls back to a legacy label_theme with no chosen color (migration fallback)', () => {
    const step: FlowStep = { id: 'step-1', title: 'Legacy step', label_theme: 'success' }
    const { container } = renderNode(StepNode, step, 'step')

    const card = container.querySelector('div')
    expect(card?.getAttribute('style')).toContain('var(--g-color-line-positive)')

    const chip = screen.getByText(FLOW_NODE_KIND_LABELS.step)
    expect(chip.closest('[class*="label_theme_"]')?.className).toContain('label_theme_success')
    // No icon chosen either — falls back to Step's default icon.
    expect(screen.getByTestId('chip-icon').dataset.iconName).toBe(FLOW_NODE_KIND_ICONS.step.name)
  })

  it('prefers a chosen color over a stale label_theme once both are present', () => {
    const step: FlowStep = { id: 'step-1', title: 'Migrated step', color: 'info', label_theme: 'danger' }
    const { container } = renderNode(StepNode, step, 'step')

    expect(container.querySelector('div')?.getAttribute('style')).toContain('var(--g-color-line-info)')
  })

  it('renders a custom type_label on its chip when set', () => {
    const step: FlowStep = { id: 'step-1', title: 'Retry payment', type_label: 'Retry' }
    renderNode(StepNode, step, 'step')

    expect(screen.getByText('Retry')).toBeTruthy()
    expect(screen.queryByText(FLOW_NODE_KIND_LABELS.step)).toBeNull()
  })

  it('renders "Step" on its chip when type_label is unset', () => {
    const step: FlowStep = { id: 'step-1', title: 'Plain step' }
    renderNode(StepNode, step, 'step')

    expect(screen.getByText(FLOW_NODE_KIND_LABELS.step)).toBeTruthy()
  })
})

describe('FlowRefNode title/subtitle (mirrors entity-backed fallback chain)', () => {
  it('renders the live name/description from refStatus, not any value stored on the step', () => {
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    renderNode(FlowRefNode, step, 'flow', { name: 'Checkout', description: 'Cart to payment' })

    expect(screen.getByText('Checkout')).toBeTruthy()
    expect(screen.getByText('Cart to payment')).toBeTruthy()
  })

  it('falls back to a client-side fetch of the target Flow\'s name/description when there is no refStatus entry yet', async () => {
    flowsApiGet.mockResolvedValueOnce({ id: 5, name: 'Checkout', description: 'Cart to payment' })
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    renderNode(FlowRefNode, step, 'flow')

    await waitFor(() => expect(screen.getByText('Checkout')).toBeTruthy())
    expect(flowsApiGet).toHaveBeenCalledWith(5)
    expect(screen.getByText('Cart to payment')).toBeTruthy()
  })

  it('falls back to the step id when neither refStatus nor the client fetch resolves', async () => {
    flowsApiGet.mockRejectedValueOnce(new Error('not found'))
    const step: FlowStep = { id: 'n1', flow_ref: 999 }
    renderNode(FlowRefNode, step, 'flow')

    await waitFor(() => expect(flowsApiGet).toHaveBeenCalledWith(999))
    expect(screen.getByText('n1')).toBeTruthy()
  })

  it('prefers the server-resolved refStatus over the client-side fetch, and skips the fetch entirely', () => {
    const callsBefore = flowsApiGet.mock.calls.length
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    renderNode(FlowRefNode, step, 'flow', { name: 'Checkout', description: 'Cart to payment' })

    expect(screen.getByText('Checkout')).toBeTruthy()
    expect(flowsApiGet.mock.calls.length).toBe(callsBefore)
  })
})

describe('FlowRefNode stale-reference warning', () => {
  it('shows no warning while unresolved but not yet confirmed (no refStatus, client fetch still pending)', () => {
    flowsApiGet.mockReturnValueOnce(new Promise(() => {}))
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    renderNode(FlowRefNode, step, 'flow')

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })

  it('shows a warning once the client fetch settles and confirms the target no longer exists', async () => {
    flowsApiGet.mockRejectedValueOnce(new Error('not found'))
    const step: FlowStep = { id: 'n1', flow_ref: 999 }
    renderNode(FlowRefNode, step, 'flow')

    await waitFor(() => expect(screen.getAllByTestId('chip-icon')).toHaveLength(2))
    expect(screen.getByLabelText(/no longer exists/)).toBeTruthy()
  })

  it('shows no warning when refStatus confirms the target resolves', () => {
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    renderNode(FlowRefNode, step, 'flow', { name: 'Checkout', description: '' })

    expect(screen.queryAllByTestId('chip-icon')).toHaveLength(1)
  })
})

describe('FlowRefNode/LinkNode navigate control', () => {
  it('renders no navigate link on a Flow node when showNavigate is unset (editable canvas)', () => {
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    renderNode(FlowRefNode, step, 'flow', { name: 'Checkout', description: '' })

    expect(screen.queryByLabelText('Open this Flow')).toBeNull()
  })

  it('renders a link to /flows/:id when showNavigate is set and the target resolves', () => {
    const step: FlowStep = { id: 'n1', flow_ref: 5 }
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <FlowRefNode {...nodeProps(step, 'flow', { name: 'Checkout', description: '' })} data={{ step, refStatus: { name: 'Checkout', description: '' }, showNavigate: true } as never} />
        </MemoryRouter>
      </ThemeProvider>,
    )

    const link = screen.getByLabelText('Open this Flow')
    expect(link.getAttribute('href')).toBe('/flows/5?tab=flow')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noopener noreferrer')
  })

  it('renders no navigate link for a Flow node whose target does not resolve, even with showNavigate set', async () => {
    flowsApiGet.mockRejectedValueOnce(new Error('not found'))
    const step: FlowStep = { id: 'n1', flow_ref: 999 }
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <FlowRefNode {...nodeProps(step, 'flow')} data={{ step, showNavigate: true } as never} />
        </MemoryRouter>
      </ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByLabelText(/no longer exists/)).toBeTruthy())
    expect(screen.queryByLabelText('Open this Flow')).toBeNull()
  })

  it('renders a Link node\'s navigate control pointing at link_url when showNavigate is set', () => {
    const step: FlowStep = { id: 'n1', link_url: 'https://example.com/runbook' }
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <LinkNode {...nodeProps(step, 'link')} data={{ step, showNavigate: true } as never} />
        </MemoryRouter>
      </ThemeProvider>,
    )

    const link = screen.getByLabelText('Open this link')
    expect(link.getAttribute('href')).toBe('https://example.com/runbook')
    expect(link.getAttribute('target')).toBe('_blank')
  })

  it('renders no navigate control for a Link node when showNavigate is unset', () => {
    const step: FlowStep = { id: 'n1', link_url: 'https://example.com' }
    renderNode(LinkNode, step, 'link')

    expect(screen.queryByLabelText('Open this link')).toBeNull()
  })
})

describe('LinkNode title/subtitle', () => {
  it('renders the author-typed title, with the URL always shown as subtitle', () => {
    const step: FlowStep = { id: 'n1', link_url: 'https://example.com/runbook', title: 'Runbook' }
    renderNode(LinkNode, step, 'link')

    expect(screen.getByText('Runbook')).toBeTruthy()
    expect(screen.getByText('https://example.com/runbook')).toBeTruthy()
  })

  it('falls back to the URL itself as the title when unset — never the step\'s opaque id', () => {
    const step: FlowStep = { id: 'step-7', link_url: 'https://example.com/runbook' }
    renderNode(LinkNode, step, 'link')

    // Title and subtitle both render the URL text (two separate elements) since there's no
    // author-typed title to distinguish them; the opaque step id never appears at all.
    expect(screen.getAllByText('https://example.com/runbook')).toHaveLength(2)
    expect(screen.queryByText('step-7')).toBeNull()
  })

  it('falls back to the step id only when there is neither a title nor a link_url (in-progress add)', () => {
    const step: FlowStep = { id: 'n1' }
    renderNode(LinkNode, step, 'link')

    expect(screen.getByText('n1')).toBeTruthy()
  })
})
