// Custom React Flow node components for the compact consumers graph
// `ServiceNode`/`EndpointNode` registered
// via `nodeTypes`. Each handle is centered and invisible (`CENTERED_HANDLE_STYLE`)
// so `type: 'straight'` edges draw true node-center-to-node-center lines
// regardless of a node's angle on the radial ring, without per-node
// direction bookkeeping.
import { memo } from 'react'
import { SideHandles } from './SideHandles'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Text } from '@gravity-ui/uikit'
import { RelationTargetLink } from 'frontend/components/RelationTargetLink'
import type { Relation } from 'frontend/lib/types'
import { MethodBadge } from './MethodBadge'
import type { EndpointConsumerSummary, ServiceSummary } from '../lib/types'

export const SERVICE_NODE_WIDTH = 180
export const SERVICE_NODE_HEIGHT = 52
export const ENDPOINT_NODE_WIDTH = 200
// Tall enough for the method badge, the path, and (when the API has a
// providing Service) a third "Provided by" line.
export const ENDPOINT_NODE_HEIGHT = 84

const CENTERED_HANDLE_STYLE = {
  opacity: 0,
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
} as const

export interface ServiceNodeData extends Record<string, unknown> {
  service: ServiceSummary
}

export type ServiceFlowNode = Node<ServiceNodeData, 'service'>

function ServiceNodeComponent({ data }: NodeProps<ServiceFlowNode>) {
  return (
    <div
      style={{
        boxSizing: 'border-box',
        width: SERVICE_NODE_WIDTH,
        height: SERVICE_NODE_HEIGHT,
        padding: '8px 12px',
        border: '1px solid var(--g-color-line-generic)',
        borderRadius: 8,
        background: 'var(--g-color-base-background)',
        boxShadow: '0 1px 4px rgba(0, 0, 0, 0.12)',
      }}
    >
      <Handle type="source" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <SideHandles />
      <Text variant="body-2" ellipsis style={{ display: 'block' }}>{data.service.title || data.service.name}</Text>
      {data.service.teamName && (
        <Text color="secondary" variant="caption-2" ellipsis style={{ display: 'block' }}>{data.service.teamName}</Text>
      )}
    </div>
  )
}

export const ServiceNode = memo(ServiceNodeComponent)

export interface EndpointNodeData extends Record<string, unknown> {
  endpoint: EndpointConsumerSummary
  /** The Component whose `providesAPI` covers this Endpoint's API (an `apiProvidedBy` relation on the API entity), or `null` if none is declared. */
  provider: Relation | null
}

export type EndpointFlowNode = Node<EndpointNodeData, 'endpoint'>

function EndpointNodeComponent({ data }: NodeProps<EndpointFlowNode>) {
  return (
    <div
      style={{
        boxSizing: 'border-box',
        width: ENDPOINT_NODE_WIDTH,
        height: ENDPOINT_NODE_HEIGHT,
        padding: '10px 14px',
        border: '2px solid var(--g-color-line-info)',
        borderRadius: 8,
        // Opaque (unlike `--g-color-base-generic`, a translucent black-alpha
        // token) so the incoming edges don't visibly bleed through the card.
        background: 'var(--g-color-base-float)',
        textAlign: 'center',
      }}
    >
      <Handle type="target" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <SideHandles />
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4 }}>
        <MethodBadge method={data.endpoint.method} />
      </div>
      <Text
        variant="body-2"
        ellipsis
        style={{ display: 'block', fontFamily: 'var(--g-text-code-font-family, monospace)' }}
      >
        {data.endpoint.path}
      </Text>
      {data.provider && (
        // Bubble-phase (not capture-phase) stopPropagation: it must run after
        // the link's own onClick (preventDefault + navigate), not before —
        // capture-phase would stop the event before it ever reaches the link.
        // This only keeps the click from also reaching React Flow's
        // `onNodeClick` (a no-op for the endpoint node either way).
        <div
          onClick={(event) => event.stopPropagation()}
          style={{ marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
        >
          <Text color="secondary" variant="caption-2">Provided by </Text>
          <Text variant="caption-2">
            <RelationTargetLink
              target={data.provider.target}
              targetKind={data.provider.targetKind}
              targetId={data.provider.targetId}
            />
          </Text>
        </div>
      )}
    </div>
  )
}

export const EndpointNode = memo(EndpointNodeComponent)
