// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NodeProps } from '@xyflow/react'
import { ChannelNode, ServiceRoleNode, type ChannelFlowNode, type ServiceRoleFlowNode } from './OperationConsumerNodes'
import { makeServiceSummary } from '../testFixtures'

afterEach(() => cleanup())

// `Handle` needs no real behavior here — these tests only exercise each
// node's own rendered content, not React Flow's edge-anchoring.
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return { ...actual, Handle: () => null }
})

function serviceRoleNodeProps(data: ServiceRoleFlowNode['data']): NodeProps<ServiceRoleFlowNode> {
  return { id: 'serviceRole-1', type: 'serviceRole', data } as unknown as NodeProps<ServiceRoleFlowNode>
}

function channelNodeProps(data: ChannelFlowNode['data']): NodeProps<ChannelFlowNode> {
  return { id: 'channel', type: 'channel', data } as unknown as NodeProps<ChannelFlowNode>
}

describe('ServiceRoleNode', () => {
  it('shows a "Publisher" role label, not color alone, for a publisher participant', () => {
    render(
      <ThemeProvider theme="light">
        <ServiceRoleNode {...serviceRoleNodeProps({ service: makeServiceSummary({ title: 'Booking Service', teamName: 'Booking Team' }), role: 'publisher' })} />
      </ThemeProvider>,
    )

    expect(screen.getByText('Publisher')).toBeDefined()
    expect(screen.getByText('Booking Service')).toBeDefined()
    expect(screen.getByText('Booking Team')).toBeDefined()
  })

  it('shows a "Subscriber" role label for a subscriber participant, using different vocabulary than direction', () => {
    render(
      <ThemeProvider theme="light">
        <ServiceRoleNode {...serviceRoleNodeProps({ service: makeServiceSummary(), role: 'subscriber' })} />
      </ThemeProvider>,
    )

    expect(screen.getByText('Subscriber')).toBeDefined()
    expect(screen.queryByText('Send')).toBeNull()
    expect(screen.queryByText('Receive')).toBeNull()
  })

  it("falls back to the service's name when it has no title", () => {
    render(
      <ThemeProvider theme="light">
        <ServiceRoleNode {...serviceRoleNodeProps({ service: makeServiceSummary({ title: '', name: 'billing-service' }), role: 'publisher' })} />
      </ThemeProvider>,
    )

    expect(screen.getByText('billing-service')).toBeDefined()
  })
})

describe('ChannelNode', () => {
  it('shows the channel address and protocol', () => {
    render(
      <ThemeProvider theme="light">
        <ChannelNode {...channelNodeProps({ channelAddress: 'booking.created', channelProtocol: 'kafka' })} />
      </ThemeProvider>,
    )

    expect(screen.getByText('booking.created')).toBeDefined()
    expect(screen.getByText('kafka')).toBeDefined()
  })

  it('omits the protocol line when unresolved', () => {
    render(
      <ThemeProvider theme="light">
        <ChannelNode {...channelNodeProps({ channelAddress: 'booking.created', channelProtocol: '' })} />
      </ThemeProvider>,
    )

    expect(screen.getByText('booking.created')).toBeDefined()
  })
})
