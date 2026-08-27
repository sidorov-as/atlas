// Compact "Services using this endpoint" graph on the Endpoint Overview tab —
// React Flow, endpoint-center/
// service-ring layout, read-only. A fixed radial-position formula (angle =
// 2π * i / n, fixed radius) is computed once per render rather than run
// through a layout library — this graph's shape never varies:
// simpler and cheaper than any layout-engine pass for this specific
// bounded shape. The surrounding chrome (loading/error/empty/ReactFlow
// wrapper/fullscreen) lives in `CompactDependencyGraph`;
// this file
// keeps only the layout math and node types, which are genuinely different
// from `OperationConsumersGraph`'s.
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Edge, Node, NodeMouseHandler, NodeTypes } from '@xyflow/react'
import type { Relation } from 'frontend/lib/types'
import { CompactDependencyGraph } from './CompactDependencyGraph'
import { EndpointNode, ENDPOINT_NODE_HEIGHT, ENDPOINT_NODE_WIDTH, ServiceNode, SERVICE_NODE_HEIGHT, SERVICE_NODE_WIDTH, type EndpointFlowNode, type ServiceFlowNode } from './EndpointConsumerNodes'
import type { EndpointConsumers } from '../lib/types'

const NODE_TYPES: NodeTypes = { service: ServiceNode, endpoint: EndpointNode }

// Beyond this many linked Services, the compact inline graph shows the cap
// plus an overflow indicator rather than growing unbounded — the full-screen view shows every linked Service uncapped instead.
const MAX_GRAPH_SERVICES = 12
const RING_RADIUS = 220

function buildGraph(
  consumers: EndpointConsumers, providerRelation: Relation | null, limit?: number,
): { nodes: (ServiceFlowNode | EndpointFlowNode)[], edges: Edge[], overflowCount: number } {
  const visible = limit === undefined ? consumers.services : consumers.services.slice(0, limit)
  const overflowCount = consumers.services.length - visible.length

  const endpointNode: EndpointFlowNode = {
    id: 'endpoint',
    type: 'endpoint',
    position: { x: -ENDPOINT_NODE_WIDTH / 2, y: -ENDPOINT_NODE_HEIGHT / 2 },
    data: { endpoint: consumers.endpoint, provider: providerRelation },
    draggable: false,
    connectable: false,
    selectable: false,
  }

  const serviceNodes: ServiceFlowNode[] = visible.map((service, index) => {
    const angle = (2 * Math.PI * index) / visible.length
    return {
      id: service.id,
      type: 'service',
      position: {
        x: RING_RADIUS * Math.cos(angle) - SERVICE_NODE_WIDTH / 2,
        y: RING_RADIUS * Math.sin(angle) - SERVICE_NODE_HEIGHT / 2,
      },
      data: { service },
      draggable: false,
      connectable: false,
    }
  })

  // Service -> Endpoint direction reflects the dependency direction (spec's
  // "Edge direction reflects dependency direction" scenario), not the reverse.
  const edges: Edge[] = visible.map((service) => ({
    id: `${service.id}-endpoint`,
    source: service.id,
    target: 'endpoint',
    type: 'straight',
  }))

  return { nodes: [endpointNode, ...serviceNodes], edges, overflowCount }
}

export function EndpointConsumersGraph({
  consumers,
  isLoading,
  error,
  onRetry,
  canLinkService,
  onLinkService,
  providerRelation,
}: {
  consumers: EndpointConsumers | null
  isLoading: boolean
  error: Error | null
  onRetry: () => void
  canLinkService: boolean
  onLinkService: () => void
  /** The API's `apiProvidedBy` relation (which Service provides it), shown on the endpoint node — `null` if none is declared. */
  providerRelation: Relation | null
}) {
  const navigate = useNavigate()

  // Two builds over the same already-loaded `consumers` data: the capped
  // inline graph and the uncapped full-screen graph — no second fetch
  const inlineGraph = useMemo(
    () => (consumers ? buildGraph(consumers, providerRelation, MAX_GRAPH_SERVICES) : null),
    [consumers, providerRelation],
  )
  const fullscreenGraph = useMemo(
    () => (consumers ? buildGraph(consumers, providerRelation) : null),
    [consumers, providerRelation],
  )

  const handleNodeClick: NodeMouseHandler<Node> = (_event, node) => {
    // Endpoint node click is a no-op (spec's "Clicking the Endpoint node does not navigate away").
    if (node.type === 'service') navigate(`/components/${node.id}`)
  }

  return (
    <CompactDependencyGraph
      title="Services using this endpoint"
      nodes={inlineGraph?.nodes ?? []}
      edges={inlineGraph?.edges ?? []}
      fullscreenNodes={fullscreenGraph?.nodes ?? []}
      fullscreenEdges={fullscreenGraph?.edges ?? []}
      nodeTypes={NODE_TYPES}
      onNodeClick={handleNodeClick}
      isLoading={isLoading}
      error={error}
      errorFallback="Failed to load the consumers graph"
      onRetry={onRetry}
      emptyMessage="No services are linked to this endpoint yet"
      canLinkService={canLinkService}
      onLinkService={onLinkService}
      fillHeight
      overflowLabel={
        inlineGraph && inlineGraph.overflowCount > 0
          ? `${MAX_GRAPH_SERVICES} of ${consumers!.services.length} services shown`
          : undefined
      }
    />
  )
}
