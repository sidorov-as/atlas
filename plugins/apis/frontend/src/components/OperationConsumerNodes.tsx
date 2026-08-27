// Custom React Flow node components for the channel-scoped publishers/
// subscribers graph — a single
// `ServiceRoleNode` parameterized by role (rather than separate
// Publisher/Subscriber components) plus a `ChannelNode` standing in for the
// aggregated channel (not a single Operation row). Each handle
// is centered and invisible (`CENTERED_HANDLE_STYLE`) so `type: 'straight'`
// edges draw true node-center-to-node-center lines regardless of a node's
// angle on the ring, without per-node direction bookkeeping.
import { memo } from 'react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Text, Tooltip } from '@gravity-ui/uikit'
import { RoleBadge } from './RoleBadge'
import type { OperationRole, ServiceSummary } from '../lib/types'

export const SERVICE_ROLE_NODE_WIDTH = 180
// Tall enough for the role badge plus two lines of text (service name +
// team name) at Gravity UI's body-2/caption-2 line heights, without either
// line spilling past the node's bottom border.
export const SERVICE_ROLE_NODE_HEIGHT = 80
export const CHANNEL_NODE_WIDTH = 200
export const CHANNEL_NODE_HEIGHT = 64

const CENTERED_HANDLE_STYLE = {
  opacity: 0,
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
} as const

export interface ServiceRoleNodeData extends Record<string, unknown> {
  service: ServiceSummary
  role: OperationRole
}

export type ServiceRoleFlowNode = Node<ServiceRoleNodeData, 'serviceRole'>

function ServiceRoleNodeComponent({ data }: NodeProps<ServiceRoleFlowNode>) {
  return (
    <div
      style={{
        boxSizing: 'border-box',
        width: SERVICE_ROLE_NODE_WIDTH,
        height: SERVICE_ROLE_NODE_HEIGHT,
        padding: '8px 12px',
        border: '1px solid var(--g-color-line-generic)',
        borderRadius: 8,
        background: 'var(--g-color-base-background)',
        boxShadow: '0 1px 4px rgba(0, 0, 0, 0.12)',
      }}
    >
      <Handle type="source" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <Handle type="target" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      {/* Role is a label, not color alone (spec's "Publisher and subscriber nodes are visually distinguished by a label, not by color alone"). */}
      <div style={{ marginBottom: 4 }}>
        <RoleBadge role={data.role} />
      </div>
      <Tooltip content={data.service.title || data.service.name} placement="top">
        <Text variant="body-2" ellipsis style={{ display: 'block' }}>{data.service.title || data.service.name}</Text>
      </Tooltip>
      {data.service.teamName && (
        <Tooltip content={data.service.teamName} placement="bottom">
          <Text color="secondary" variant="caption-2" ellipsis style={{ display: 'block' }}>{data.service.teamName}</Text>
        </Tooltip>
      )}
    </div>
  )
}

export const ServiceRoleNode = memo(ServiceRoleNodeComponent)

export interface ChannelNodeData extends Record<string, unknown> {
  channelAddress: string
  channelProtocol: string
}

export type ChannelFlowNode = Node<ChannelNodeData, 'channel'>

function ChannelNodeComponent({ data }: NodeProps<ChannelFlowNode>) {
  return (
    <div
      style={{
        boxSizing: 'border-box',
        width: CHANNEL_NODE_WIDTH,
        height: CHANNEL_NODE_HEIGHT,
        padding: '10px 14px',
        border: '2px solid var(--g-color-line-info)',
        borderRadius: 8,
        // Opaque so incoming/outgoing edges don't visibly bleed through the card.
        background: 'var(--g-color-base-float)',
        textAlign: 'center',
      }}
    >
      <Handle type="source" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <Handle type="target" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <Tooltip content={data.channelAddress} placement="top">
        <Text
          variant="body-2"
          ellipsis
          style={{ display: 'block', fontFamily: 'var(--g-text-code-font-family, monospace)' }}
        >
          {data.channelAddress}
        </Text>
      </Tooltip>
      {data.channelProtocol && (
        <Text color="secondary" variant="caption-2" style={{ display: 'block' }}>{data.channelProtocol}</Text>
      )}
    </div>
  )
}

export const ChannelNode = memo(ChannelNodeComponent)
