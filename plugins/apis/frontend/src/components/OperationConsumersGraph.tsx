// Compact "Publishers & subscribers" graph on the Operation Overview tab
// React Flow, read-only.
//
// Layout (decided and documented here): a single ring split by
// role, not a second concentric ring — publishers occupy the left arc
// (~108°-252°) and subscribers occupy the right arc (~-72°-72°) around one
// central `ChannelNode`, so the two roles stay visually grouped without the
// extra complexity of a two-ring layout. A fixed formula (angle interpolated
// across each arc) is computed once per render rather than run through a
// layout library — this graph's shape never varies, same rationale as
// `EndpointConsumersGraph`'s single ring.
//
// Edge direction reflects the data-flow direction implied by role: a
// publisher's edge points into the channel; the channel's edge points out to
// each subscriber.
//
// The surrounding chrome (loading/error/empty/ReactFlow wrapper/fullscreen)
// lives in `CompactDependencyGraph` — this file keeps only the layout math and node
// types, which are genuinely different from `EndpointConsumersGraph`'s.
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Edge, Node, NodeMouseHandler, NodeTypes } from '@xyflow/react'
import { CompactDependencyGraph } from './CompactDependencyGraph'
import {
  ChannelNode,
  CHANNEL_NODE_HEIGHT,
  CHANNEL_NODE_WIDTH,
  ServiceRoleNode,
  SERVICE_ROLE_NODE_HEIGHT,
  SERVICE_ROLE_NODE_WIDTH,
  type ChannelFlowNode,
  type ServiceRoleFlowNode,
  type ServiceRoleNodeData,
} from './OperationConsumerNodes'
import type { OperationConsumerParticipant, OperationConsumers } from '../lib/types'

const NODE_TYPES: NodeTypes = { serviceRole: ServiceRoleNode, channel: ChannelNode }

// Beyond this many aggregated participants, the compact inline graph shows
// the cap plus an overflow indicator rather than growing unbounded (spec's
// "Large participant counts are capped on the compact graph") — the
// full-screen view shows every
// aggregated participant uncapped instead.
const MAX_GRAPH_PARTICIPANTS = 12
const RING_RADIUS = 220

const PUBLISHER_ARC: [number, number] = [Math.PI * 0.6, Math.PI * 1.4]
const SUBSCRIBER_ARC: [number, number] = [Math.PI * -0.4, Math.PI * 0.4]

function arcNodes(participants: OperationConsumerParticipant[], [startAngle, endAngle]: [number, number]): ServiceRoleFlowNode[] {
  return participants.map((participant, index) => {
    const angle = participants.length === 1
      ? (startAngle + endAngle) / 2
      : startAngle + ((endAngle - startAngle) * index) / (participants.length - 1)
    return {
      id: `${participant.role}-${participant.service.id}`,
      type: 'serviceRole',
      position: {
        x: RING_RADIUS * Math.cos(angle) - SERVICE_ROLE_NODE_WIDTH / 2,
        y: RING_RADIUS * Math.sin(angle) - SERVICE_ROLE_NODE_HEIGHT / 2,
      },
      data: { service: participant.service, role: participant.role },
      draggable: false,
      connectable: false,
    }
  })
}

function buildGraph(
  consumers: OperationConsumers, limit?: number,
): { nodes: (ServiceRoleFlowNode | ChannelFlowNode)[], edges: Edge[], overflowCount: number } {
  const visible = limit === undefined ? consumers.participants : consumers.participants.slice(0, limit)
  const overflowCount = consumers.participants.length - visible.length

  const channelNode: ChannelFlowNode = {
    id: 'channel',
    type: 'channel',
    position: { x: -CHANNEL_NODE_WIDTH / 2, y: -CHANNEL_NODE_HEIGHT / 2 },
    data: { channelAddress: consumers.operation.channelAddress, channelProtocol: consumers.operation.channelProtocol },
    draggable: false,
    connectable: false,
    selectable: false,
  }

  const publishers = visible.filter((participant) => participant.role === 'publisher')
  const subscribers = visible.filter((participant) => participant.role === 'subscriber')
  const publisherNodes = arcNodes(publishers, PUBLISHER_ARC)
  const subscriberNodes = arcNodes(subscribers, SUBSCRIBER_ARC)

  const edges: Edge[] = [
    ...publishers.map((participant) => ({
      id: `${participant.role}-${participant.service.id}-edge`,
      source: `${participant.role}-${participant.service.id}`,
      target: 'channel',
      type: 'straight',
    })),
    ...subscribers.map((participant) => ({
      id: `${participant.role}-${participant.service.id}-edge`,
      source: 'channel',
      target: `${participant.role}-${participant.service.id}`,
      type: 'straight',
    })),
  ]

  return { nodes: [channelNode, ...publisherNodes, ...subscriberNodes], edges, overflowCount }
}

export function OperationConsumersGraph({
  consumers,
  isLoading,
  error,
  onRetry,
  canLinkService,
  onLinkService,
}: {
  consumers: OperationConsumers | null
  isLoading: boolean
  error: Error | null
  onRetry: () => void
  canLinkService: boolean
  onLinkService: () => void
}) {
  const navigate = useNavigate()

  // Two builds over the same already-loaded `consumers` data: the capped
  // inline graph and the uncapped full-screen graph — no second fetch
  const inlineGraph = useMemo(() => (consumers ? buildGraph(consumers, MAX_GRAPH_PARTICIPANTS) : null), [consumers])
  const fullscreenGraph = useMemo(() => (consumers ? buildGraph(consumers) : null), [consumers])

  const handleNodeClick: NodeMouseHandler<Node> = (_event, node) => {
    // Channel node click is a no-op, mirroring `EndpointConsumersGraph`'s endpoint-center node.
    if (node.type === 'serviceRole') {
      const data = node.data as ServiceRoleNodeData
      navigate(`/components/${data.service.id}`)
    }
  }

  return (
    <CompactDependencyGraph
      title="Publishers & subscribers"
      nodes={inlineGraph?.nodes ?? []}
      edges={inlineGraph?.edges ?? []}
      fullscreenNodes={fullscreenGraph?.nodes ?? []}
      fullscreenEdges={fullscreenGraph?.edges ?? []}
      nodeTypes={NODE_TYPES}
      onNodeClick={handleNodeClick}
      isLoading={isLoading}
      error={error}
      errorFallback="Failed to load the publishers/subscribers graph"
      onRetry={onRetry}
      emptyMessage="No services are linked to this channel yet"
      canLinkService={canLinkService}
      onLinkService={onLinkService}
      fillHeight
      overflowLabel={
        inlineGraph && inlineGraph.overflowCount > 0
          ? `${MAX_GRAPH_PARTICIPANTS} of ${consumers!.participants.length} participants shown`
          : undefined
      }
    />
  )
}
