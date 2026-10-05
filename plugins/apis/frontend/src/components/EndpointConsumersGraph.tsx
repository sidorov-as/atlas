// "Services using this endpoint" graph on the Endpoint Overview tab — React
// Flow, endpoint at the center. Inline: Services on concentric rings
// (`ringsLayout`) with straight edges, read-only. Full screen: draggable, Columns
// with rounded step edges, and Services can be grouped by team or system. The compact inline view draws
// at most `MAX_COMPACT_SERVICES` Services plus a "+N more" node that opens the
// full-screen view. The
// surrounding chrome (loading/error/empty/ReactFlow wrapper/fullscreen) lives
// in `CompactDependencyGraph`; this file keeps the node data and node types,
// which differ from `OperationConsumersGraph`'s.
import { useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Edge, Node, NodeMouseHandler, NodeTypes } from '@xyflow/react'
import type { Relation } from 'frontend/lib/types'
import { CompactDependencyGraph, groupKey, type FullscreenGraph, type GraphView, type GroupRef, type MoreGroup } from './CompactDependencyGraph'
import { EndpointNode, ENDPOINT_NODE_HEIGHT, ENDPOINT_NODE_WIDTH, ServiceNode, SERVICE_NODE_HEIGHT, SERVICE_NODE_WIDTH, type EndpointFlowNode, type ServiceFlowNode } from './EndpointConsumerNodes'
import { GROUP_NODE_HEIGHT, GROUP_NODE_TYPE, GROUP_NODE_WIDTH, GroupNode, type GroupFlowNode } from './GroupNode'
import { MoreNode, type MoreFlowNode } from './MoreNode'
import { endpointServicesApi } from '../lib/entities'
import { groupColorKey } from '../lib/graphGrouping'
import { sideEdge } from '../lib/graphEdges'
import { columnsItemsLayout, columnsLayout, ringsLayout, serviceMatchesQuery, type LayoutItem } from '../lib/graphLayouts'
import { allocateMembers, groupIdOf, resolveGroups } from '../lib/groupedGraph'
import type { ConsumerGroupBy, EndpointConsumers, ServiceSummary } from '../lib/types'

const NODE_TYPES: NodeTypes = { service: ServiceNode, endpoint: EndpointNode, more: MoreNode, [GROUP_NODE_TYPE]: GroupNode }

const MAX_COMPACT_SERVICES = 6
const MAX_FULLSCREEN_SERVICES = 50
const SERVICE_SIZE = { width: SERVICE_NODE_WIDTH, height: SERVICE_NODE_HEIGHT }
const ENDPOINT_SIZE = { width: ENDPOINT_NODE_WIDTH, height: ENDPOINT_NODE_HEIGHT }
const GROUP_SIZE = { width: GROUP_NODE_WIDTH, height: GROUP_NODE_HEIGHT }

type EndpointView = GraphView<EndpointConsumers, EndpointConsumers>

/** Nodes and edges for the Endpoint at the center, `services` around it and an optional "+N more" node after them. */
function toGraph(
  consumers: EndpointConsumers, providerRelation: Relation | null, services: ServiceSummary[], moreCount: number, fullscreen: boolean,
): { nodes: (ServiceFlowNode | EndpointFlowNode | MoreFlowNode)[], edges: Edge[] } {
  const endpointNode: EndpointFlowNode = {
    id: 'endpoint',
    type: 'endpoint',
    position: { x: -ENDPOINT_NODE_WIDTH / 2, y: -ENDPOINT_NODE_HEIGHT / 2 },
    data: { endpoint: consumers.endpoint, provider: providerRelation },
    draggable: false,
    connectable: false,
    selectable: false,
  }

  const slots = services.length + (moreCount > 0 ? 1 : 0)
  // Inline: Services on rings with straight edges. Full screen: Columns with rounded step edges.
  const positions = fullscreen
    ? columnsLayout(slots, SERVICE_SIZE, ENDPOINT_SIZE, 'right')
    : ringsLayout(slots, SERVICE_SIZE)

  const serviceNodes: ServiceFlowNode[] = services.map((service, index) => ({
    id: service.id,
    type: 'service',
    position: positions[index],
    data: { service },
    draggable: false,
    connectable: false,
  }))

  const moreNodes: MoreFlowNode[] = moreCount > 0
    ? [{
      id: 'more',
      type: 'more',
      position: positions[services.length],
      data: { count: moreCount, ...SERVICE_SIZE },
      draggable: false,
      connectable: false,
      selectable: false,
    }]
    : []

  // Service -> Endpoint direction reflects the dependency direction (spec's
  // "Edge direction reflects dependency direction" scenario), not the reverse.
  const edges: Edge[] = services.map((service) => (fullscreen
    ? sideEdge(`${service.id}-endpoint`, service.id, 'left', 'endpoint', 'right')
    : { id: `${service.id}-endpoint`, source: service.id, target: 'endpoint', type: 'straight' }))

  return { nodes: [endpointNode, ...serviceNodes, ...moreNodes], edges }
}

// `count` is the total across every page, so a "more" node also covers
// Services the response did not carry.
function buildInlineGraph(consumers: EndpointConsumers, providerRelation: Relation | null) {
  const services = consumers.services.slice(0, MAX_COMPACT_SERVICES)
  return toGraph(consumers, providerRelation, services, consumers.count - services.length, false)
}

/**
 * The full-screen graph: the loaded page, plus — while a search is active —
 * every Service the server matched, drawn first so a match beyond the page is
 * never cut off by the cap. At most `MAX_FULLSCREEN_SERVICES` Services are
 * drawn; the rest are the "more" node.
 */
function buildFullscreenGraph(
  consumers: EndpointConsumers, providerRelation: Relation | null, view: EndpointView,
): FullscreenGraph {
  if (view.groupBy && view.grouped) return buildGroupedGraph(consumers, providerRelation, view.groupBy, view.grouped, view)
  const { query, result } = view
  const found = query && result ? result.services : []
  const foundIds = new Set(found.map((service) => service.id))
  const services = [...found, ...consumers.services.filter((service) => !foundIds.has(service.id))].slice(0, MAX_FULLSCREEN_SERVICES)

  // While a search is active the remainder is counted among the matches;
  // otherwise among every linked Service.
  const drawnCounted = query && result ? services.filter((service) => foundIds.has(service.id)).length : services.length
  const moreCount = (query && result ? result.count : consumers.count) - drawnCounted

  const matchIds = new Set(
    query ? services.filter((service) => foundIds.has(service.id) || serviceMatchesQuery(service, query)).map((service) => service.id) : [],
  )
  return {
    ...toGraph(consumers, providerRelation, services, moreCount, true),
    centerId: 'endpoint',
    matchIds,
    matchCount: query && result ? result.count : null,
  }
}

function endpointCenterNode(consumers: EndpointConsumers, providerRelation: Relation | null): EndpointFlowNode {
  return {
    id: 'endpoint',
    type: 'endpoint',
    position: { x: -ENDPOINT_NODE_WIDTH / 2, y: -ENDPOINT_NODE_HEIGHT / 2 },
    data: { endpoint: consumers.endpoint, provider: providerRelation },
    draggable: false,
    connectable: false,
    selectable: false,
  }
}

/**
 * The grouped full-screen graph: one node per team or system holding at least
 * two (matching) Services, the Services outside those groups, and the Services
 * of the groups the user expanded. Group sizes come from the server. Plain and
 * expanded-group Services share the `MAX_FULLSCREEN_SERVICES` cap; group nodes
 * do not count towards it.
 */
function buildGroupedGraph(
  consumers: EndpointConsumers, providerRelation: Relation | null,
  groupBy: ConsumerGroupBy, base: EndpointConsumers, view: EndpointView,
): FullscreenGraph {
  const { query, groupedSearch, expanded, members } = view
  const searched = query && groupedSearch ? groupedSearch : null
  const resolved = resolveGroups(
    { groups: base.groups ?? [], plain: base.services },
    searched ? { groups: searched.groups ?? [], plain: searched.services } : null,
    (service) => groupIdOf(service, groupBy),
  )

  const source = searched ?? base
  const plain = resolved.plain.slice(0, MAX_FULLSCREEN_SERVICES)
  // Services of the remainder the page did not carry, plus those cut by the cap.
  const plainMore = Math.max(0, (source.servicesCount ?? source.services.length) - source.services.length) + resolved.plain.length - plain.length

  const expandedGroups = resolved.groups
    .filter((group) => expanded.has(groupKey({ groupId: group.id })) && members.has(groupKey({ groupId: group.id })))
    .map((group) => {
      const page = members.get(groupKey({ groupId: group.id }))!
      return { key: group.id, members: page.services, total: page.count }
    })
  const allocation = allocateMembers(expandedGroups, MAX_FULLSCREEN_SERVICES - plain.length)

  const items: LayoutItem[] = [
    ...resolved.groups.map((group) => {
      const share = allocation.get(group.id)
      return { size: GROUP_SIZE, members: share ? share.drawn.length + (share.more > 0 ? 1 : 0) : 0 }
    }),
    ...plain.map(() => ({ size: SERVICE_SIZE })),
    ...(plainMore > 0 ? [{ size: SERVICE_SIZE }] : []),
  ]
  const placements = columnsItemsLayout(items, SERVICE_SIZE, ENDPOINT_SIZE, 'right')

  const nodes: (ServiceFlowNode | EndpointFlowNode | MoreFlowNode | GroupFlowNode)[] = [endpointCenterNode(consumers, providerRelation)]
  const edges: Edge[] = []
  const matchIds = new Set<string>()
  const serviceNode = (service: ServiceSummary, position: { x: number; y: number }): ServiceFlowNode => ({
    id: service.id, type: 'service', position, data: { service }, draggable: false, connectable: false,
  })

  resolved.groups.forEach((group, index) => {
    const placement = placements[index]
    const id = `group-${group.id}`
    nodes.push({
      id,
      type: GROUP_NODE_TYPE,
      position: placement.position,
      data: {
        groupId: group.id,
        name: group.name,
        count: group.count,
        colorKey: groupColorKey(group.id),
        expanded: expanded.has(groupKey({ groupId: group.id })),
        total: group.total,
        dimmed: group.dimmed,
      },
      draggable: false,
      connectable: false,
    })
    edges.push(sideEdge(`${id}-endpoint`, id, 'left', 'endpoint', 'right'))
    const share = allocation.get(group.id)
    if (!share) return
    share.drawn.forEach((service, memberIndex) => {
      nodes.push(serviceNode(service, placement.members[memberIndex]))
      edges.push(sideEdge(`${service.id}-${id}`, service.id, 'left', id, 'right'))
      if (query && serviceMatchesQuery(service, query)) matchIds.add(service.id)
    })
    if (share.more > 0) {
      const more: MoreGroup = { groupBy, groupId: group.id, name: group.name }
      nodes.push({
        id: `more-${id}`,
        type: 'more',
        position: placement.members[share.drawn.length],
        data: { count: share.more, ...SERVICE_SIZE, group: more },
        draggable: false,
        connectable: false,
        selectable: false,
      })
    }
  })

  plain.forEach((service, index) => {
    nodes.push(serviceNode(service, placements[resolved.groups.length + index].position))
    edges.push(sideEdge(`${service.id}-endpoint`, service.id, 'left', 'endpoint', 'right'))
    if (searched) matchIds.add(service.id)
  })
  if (plainMore > 0) {
    nodes.push({
      id: 'more',
      type: 'more',
      position: placements[items.length - 1].position,
      data: { count: plainMore, ...SERVICE_SIZE },
      draggable: false,
      connectable: false,
      selectable: false,
    })
  }

  return { nodes, edges, centerId: 'endpoint', matchIds, matchCount: searched ? searched.count : null }
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

  const inlineGraph = useMemo(
    () => (consumers ? buildInlineGraph(consumers, providerRelation) : null),
    [consumers, providerRelation],
  )

  const endpointId = consumers?.endpoint.id
  const buildFullscreen = useCallback(
    (view: EndpointView) => buildFullscreenGraph(consumers!, providerRelation, view),
    [consumers, providerRelation],
  )
  const searchConsumers = useCallback(
    (search: string, signal: AbortSignal) => endpointServicesApi.consumers(endpointId!, { pageSize: MAX_FULLSCREEN_SERVICES, search }, signal),
    [endpointId],
  )

  const loadGrouped = useCallback(
    (groupBy: ConsumerGroupBy, search: string, signal: AbortSignal) =>
      endpointServicesApi.consumers(endpointId!, { pageSize: MAX_FULLSCREEN_SERVICES, groupBy, search }, signal),
    [endpointId],
  )
  const loadGroupMembers = useCallback(
    (groupBy: ConsumerGroupBy, group: GroupRef, signal: AbortSignal) =>
      endpointServicesApi.consumers(endpointId!, { pageSize: MAX_FULLSCREEN_SERVICES, groupBy, groupId: group.groupId }, signal),
    [endpointId],
  )

  const handleNodeClick: NodeMouseHandler<Node> = (_event, node) => {
    // Endpoint node click is a no-op (spec's "Clicking the Endpoint node does not navigate away").
    if (node.type === 'service') navigate(`/components/${node.id}`)
  }

  const openLinkedServices = (search: string, group?: MoreGroup) => {
    const params = new URLSearchParams({ tab: 'services' })
    if (group?.groupBy === 'team') {
      params.set('team', group.groupId)
      if (search) params.set('search', search)
    } else if (group) {
      // Linked Services has no system filter: the system's name stands in as the search text.
      params.set('search', group.name)
    } else if (search) {
      params.set('search', search)
    }
    navigate({ search: `?${params}` })
  }

  return (
    <CompactDependencyGraph
      title="Services using this endpoint"
      nodes={inlineGraph?.nodes ?? []}
      edges={inlineGraph?.edges ?? []}
      buildFullscreenGraph={buildFullscreen}
      searchConsumers={searchConsumers}
      loadGrouped={loadGrouped}
      loadGroupMembers={loadGroupMembers}
      totalCount={consumers?.count ?? 0}
      onOpenLinkedServices={openLinkedServices}
      nodeTypes={NODE_TYPES}
      onNodeClick={handleNodeClick}
      exportName="endpoint-consumers"
      isLoading={isLoading}
      error={error}
      errorFallback="Failed to load the consumers graph"
      onRetry={onRetry}
      emptyMessage="No services are linked to this endpoint yet"
      canLinkService={canLinkService}
      onLinkService={onLinkService}
      fillHeight
    />
  )
}
