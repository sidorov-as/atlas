// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NodeProps } from '@xyflow/react'
import { EndpointNode, ServiceNode, type EndpointFlowNode, type ServiceFlowNode } from './EndpointConsumerNodes'
import { makeServiceSummary } from '../testFixtures'
import type { Relation } from 'frontend/lib/types'

const navigateSpy = vi.fn()

afterEach(() => {
  cleanup()
  navigateSpy.mockClear()
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateSpy }
})

vi.mock('frontend/lib/entities', () => ({
  kindToPath: { system: '/systems', component: '/components', group: '/teams', api: '/apis' },
}))

// `Handle` needs no real behavior here — these tests only exercise each
// node's own rendered content, not React Flow's edge-anchoring.
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return { ...actual, Handle: () => null }
})

function endpointNodeProps(data: EndpointFlowNode['data']): NodeProps<EndpointFlowNode> {
  return { id: 'endpoint', type: 'endpoint', data } as unknown as NodeProps<EndpointFlowNode>
}

function serviceNodeProps(data: ServiceFlowNode['data']): NodeProps<ServiceFlowNode> {
  return { id: 'service-1', type: 'service', data } as unknown as NodeProps<ServiceFlowNode>
}

function renderEndpointNode(provider: Relation | null) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EndpointNode {...endpointNodeProps({ endpoint: { id: 'endpoint-1', method: 'GET', path: '/bookings/{id}', status: 'active' }, provider })} />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EndpointNode', () => {
  it('has an opaque background so incoming edges do not show through the card', () => {
    const { container } = renderEndpointNode(null)

    const card = container.querySelector('div')
    expect(card?.style.background).toContain('--g-color-base-float')
  })

  it('shows no "Provided by" line when no provider relation is known', () => {
    renderEndpointNode(null)

    expect(screen.queryByText(/Provided by/)).toBeNull()
  })

  it('shows the providing Service\'s name below the path when a provider relation is known', () => {
    renderEndpointNode({ predicate: 'apiProvidedBy', target: 'component:booking-service', targetKind: 'component', targetId: 'component-1' })

    expect(screen.getByText('Provided by')).toBeDefined()
    expect(screen.getByText('booking-service')).toBeDefined()
  })

  it('navigates to the providing Service when its name is clicked', () => {
    renderEndpointNode({ predicate: 'apiProvidedBy', target: 'component:booking-service', targetKind: 'component', targetId: 'component-1' })

    fireEvent.click(screen.getByText('booking-service'))

    expect(navigateSpy).toHaveBeenCalledWith('/components/component-1')
  })
})

describe('ServiceNode', () => {
  it('shows the service title (falling back to name) and its team', () => {
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <ServiceNode {...serviceNodeProps({ service: makeServiceSummary({ title: 'Booking Service', teamName: 'Booking Team' }) })} />
        </MemoryRouter>
      </ThemeProvider>,
    )

    expect(screen.getByText('Booking Service')).toBeDefined()
    expect(screen.getByText('Booking Team')).toBeDefined()
  })
})
