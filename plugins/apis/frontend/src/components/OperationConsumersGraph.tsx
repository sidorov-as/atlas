// "Publishers & subscribers" graph on the Operation Overview tab — React Flow,
// read-only.
//
// Layout: publishers on the left arc and subscribers on the right arc around
// one central `ChannelNode`, each arc using as many concentric rings as it
// needs to avoid overlap (`ringsLayout`), so the two roles stay visually
// grouped (full screen is always two-sided Columns). The compact inline view draws at most `MAX_COMPACT_PARTICIPANTS`
// participants across both roles, publishers first, plus one "+N more" node
// per side that has undrawn participants.
//
// Edge direction reflects the data-flow direction implied by role: a
// publisher's edge points into the channel; the channel's edge points out to
// each subscriber.
//
// The surrounding chrome (loading/error/empty/ReactFlow wrapper/fullscreen)
// lives in `CompactDependencyGraph` — this file keeps the node data and node
// types, which differ from `EndpointConsumersGraph`'s.
import { useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Edge, Node, NodeMouseHandler, NodeTypes } from '@xyflow/react'
import { CompactDependencyGraph, groupKey, type FullscreenGraph, type GraphView, type GroupRef, type MoreGroup } from './CompactDependencyGraph'
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
import { GROUP_NODE_HEIGHT, GROUP_NODE_TYPE, GROUP_NODE_WIDTH, GroupNode, type GroupFlowNode } from './GroupNode'
import { MoreNode, type MoreFlowNode } from './MoreNode'
import { operationServicesApi } from '../lib/entities'
import { groupColorKey } from '../lib/graphGrouping'
import { sideEdge } from '../lib/graphEdges'
import { columnsItemsLayout, columnsLayout, ringsLayout, serviceMatchesQuery, type LayoutItem } from '../lib/graphLayouts'
import { allocateMembers, groupIdOf, resolveGroups, type ResolvedGroup } from '../lib/groupedGraph'
import type { ConsumerGroup, ConsumerGroupBy, OperationConsumerParticipant, OperationConsumers, OperationRole } from '../lib/types'

const NODE_TYPES: NodeTypes = { serviceRole: ServiceRoleNode, channel: ChannelNode, more: MoreNode, [GROUP_NODE_TYPE]: GroupNode }

const MAX_COMPACT_PARTICIPANTS = 6
const MAX_FULLSCREEN_PARTICIPANTS = 50
const NODE_SIZE = { width: SERVICE_ROLE_NODE_WIDTH, height: SERVICE_ROLE_NODE_HEIGHT }
const GROUP_SIZE = { width: GROUP_NODE_WIDTH, height: GROUP_NODE_HEIGHT }
const CHANNEL_SIZE = { width: CHANNEL_NODE_WIDTH, height: CHANNEL_NODE_HEIGHT }

// Disjoint arcs with a clear gap between them, so the ends of the two arcs
// never touch.
const ARCS: Record<OperationRole, [number, number]> = {
  publisher: [Math.PI * 0.7, Math.PI * 1.3],
  subscriber: [Math.PI * -0.3, Math.PI * 0.3],
}
// Columns keep the roles apart by growing to opposite sides of the channel.
const COLUMN_SIDES: Record<OperationRole, 'left' | 'right'> = { publisher: 'left', subscriber: 'right' }

/** A full-screen edge between an inner node (nearer the channel) and an outer one, on the sides facing each other. Data flows into the channel from publishers and out of it to subscribers. */
function roleEdge(role: OperationRole, id: string, outer: string, inner: string): Edge {
  return role === 'publisher' ? sideEdge(id, outer, 'right', inner, 'left') : sideEdge(id, inner, 'right', outer, 'left')
}

type OperationView = GraphView<OperationConsumers, OperationConsumers>

function nodeId(participant: OperationConsumerParticipant): string {
  return `${participant.role}-${participant.service.id}`
}

/** Nodes and edges for the channel at the center, the drawn participants of each role around it, and a "+N more" node per role that has undrawn participants. */
function toGraph(
  consumers: OperationConsumers,
  publishers: OperationConsumerParticipant[],
  subscribers: OperationConsumerParticipant[],
  moreByRole: Record<OperationRole, number>,
  fullscreen: boolean,
): { nodes: (ServiceRoleFlowNode | ChannelFlowNode | MoreFlowNode)[], edges: Edge[] } {
  const channelNode: ChannelFlowNode = {
    id: 'channel',
    type: 'channel',
    position: { x: -CHANNEL_NODE_WIDTH / 2, y: -CHANNEL_NODE_HEIGHT / 2 },
    data: { channelAddress: consumers.operation.channelAddress, channelProtocol: consumers.operation.channelProtocol },
    draggable: false,
    connectable: false,
    selectable: false,
  }

  function sideNodes(role: OperationRole, participants: OperationConsumerParticipant[]): (ServiceRoleFlowNode | MoreFlowNode)[] {
    const moreCount = moreByRole[role]
    const slots = participants.length + (moreCount > 0 ? 1 : 0)
    // Inline: two arcs with straight edges. Full screen: two-sided Columns with rounded step edges.
    const positions = fullscreen
      ? columnsLayout(slots, NODE_SIZE, CHANNEL_SIZE, COLUMN_SIDES[role])
      : ringsLayout(slots, NODE_SIZE, ARCS[role])
    const serviceNodes: ServiceRoleFlowNode[] = participants.map((participant, index) => ({
      id: nodeId(participant),
      type: 'serviceRole',
      position: positions[index],
      data: { service: participant.service, role: participant.role },
      draggable: false,
      connectable: false,
    }))
    if (moreCount <= 0) return serviceNodes
    return [...serviceNodes, {
      id: `more-${role}`,
      type: 'more',
      position: positions[participants.length],
      data: { count: moreCount, ...NODE_SIZE },
      draggable: false,
      connectable: false,
      selectable: false,
    }]
  }

  const edges: Edge[] = [
    ...publishers.map((participant) => (fullscreen
      ? roleEdge('publisher', `${nodeId(participant)}-edge`, nodeId(participant), 'channel')
      : { id: `${nodeId(participant)}-edge`, source: nodeId(participant), target: 'channel', type: 'straight' })),
    ...subscribers.map((participant) => (fullscreen
      ? roleEdge('subscriber', `${nodeId(participant)}-edge`, nodeId(participant), 'channel')
      : { id: `${nodeId(participant)}-edge`, source: 'channel', target: nodeId(participant), type: 'straight' })),
  ]

  return { nodes: [channelNode, ...sideNodes('publisher', publishers), ...sideNodes('subscriber', subscribers)], edges }
}

function splitByRole(participants: OperationConsumerParticipant[]) {
  return {
    publishers: participants.filter((participant) => participant.role === 'publisher'),
    subscribers: participants.filter((participant) => participant.role === 'subscriber'),
  }
}

// The budget is shared across roles and filled publishers first. The role
// totals come from the response, which counts participants beyond its page.
function buildInlineGraph(consumers: OperationConsumers) {
  const all = splitByRole(consumers.participants)
  const publishers = all.publishers.slice(0, MAX_COMPACT_PARTICIPANTS)
  const subscribers = all.subscribers.slice(0, MAX_COMPACT_PARTICIPANTS - publishers.length)
  return toGraph(consumers, publishers, subscribers, {
    publisher: consumers.publisherCount - publishers.length,
    subscriber: consumers.subscriberCount - subscribers.length,
  }, false)
}

/**
 * The full-screen graph: the loaded page, plus — while a search is active —
 * every participant the server matched, drawn first so a match beyond the page
 * is never cut off by the cap. At most `MAX_FULLSCREEN_PARTICIPANTS` are drawn
 * across both roles; each role's remainder is its "more" node.
 */
function buildFullscreenGraph(consumers: OperationConsumers, view: OperationView): FullscreenGraph {
  if (view.groupBy && view.grouped) return buildGroupedGraph(consumers, view.groupBy, view.grouped, view)
  const { query, result } = view
  const found = query && result ? result.participants : []
  const foundIds = new Set(found.map(nodeId))
  const drawn = [...found, ...consumers.participants.filter((participant) => !foundIds.has(nodeId(participant)))].slice(0, MAX_FULLSCREEN_PARTICIPANTS)
  const { publishers, subscribers } = splitByRole(drawn)

  // While a search is active the remainder is counted among the matches;
  // otherwise among every participant.
  const searching = Boolean(query && result)
  const counted = (list: OperationConsumerParticipant[]) => (searching ? list.filter((participant) => foundIds.has(nodeId(participant))).length : list.length)
  const totals = searching && result
    ? { publisher: result.publisherCount, subscriber: result.subscriberCount }
    : { publisher: consumers.publisherCount, subscriber: consumers.subscriberCount }

  const matchIds = new Set(
    query
      ? drawn.filter((participant) => foundIds.has(nodeId(participant)) || serviceMatchesQuery(participant.service, query)).map(nodeId)
      : [],
  )
  return {
    ...toGraph(consumers, publishers, subscribers, {
      publisher: totals.publisher - counted(publishers),
      subscriber: totals.subscriber - counted(subscribers),
    }, true),
    centerId: 'channel',
    matchIds,
    matchCount: searching && result ? result.count : null,
  }
}

const ROLES: OperationRole[] = ['publisher', 'subscriber']
const groupsOf = (response: OperationConsumers, role: OperationRole): ConsumerGroup[] =>
  (role === 'publisher' ? response.publisherGroups : response.subscriberGroups) ?? []
const roleCount = (response: OperationConsumers, role: OperationRole) =>
  (role === 'publisher' ? response.publisherCount : response.subscriberCount)

interface RoleSide {
  role: OperationRole
  groups: ResolvedGroup[]
  /** Participants of this role outside any group, before the cap. */
  plain: OperationConsumerParticipant[]
  /** Participants of this role outside any group that the page did not carry. */
  plainBeyondPage: number
}

/**
 * The grouped full-screen graph: per role, one node per team or system holding
 * at least two (matching) participants of that role, the participants outside
 * those groups, and the participants of the expanded groups. Publishers are on
 * the left and subscribers on the right, each expanded group's block opening
 * away from the channel. Plain and expanded-group participants share the
 * `MAX_FULLSCREEN_PARTICIPANTS` cap, publishers first; group nodes do not count.
 */
function buildGroupedGraph(
  consumers: OperationConsumers, groupBy: ConsumerGroupBy, base: OperationConsumers, view: OperationView,
): FullscreenGraph {
  const { query, groupedSearch, expanded, members } = view
  const searched = query && groupedSearch ? groupedSearch : null
  const source = searched ?? base

  const sides: RoleSide[] = ROLES.map((role) => {
    const baseList = base.participants.filter((participant) => participant.role === role)
    const searchedList = searched ? searched.participants.filter((participant) => participant.role === role) : null
    const resolved = resolveGroups(
      { groups: groupsOf(base, role), plain: baseList },
      searchedList ? { groups: groupsOf(searched!, role), plain: searchedList } : null,
      (participant) => groupIdOf(participant.service, groupBy),
    )
    // The role's participants outside groups = its total minus what the groups hold; the page carried `onPage` of them.
    const outsideGroups = roleCount(source, role) - groupsOf(source, role).reduce((sum, group) => sum + group.count, 0)
    const onPage = (searchedList ?? baseList).length
    return { role, groups: resolved.groups, plain: resolved.plain, plainBeyondPage: Math.max(0, outsideGroups - onPage) }
  })

  // Plain participants fill the budget publishers first, then expanded groups share what is left.
  let budget = MAX_FULLSCREEN_PARTICIPANTS
  const drawnPlain = sides.map((side) => {
    const drawn = side.plain.slice(0, budget)
    budget -= drawn.length
    return drawn
  })
  const expandedGroups = sides.flatMap((side) =>
    side.groups
      .filter((group) => expanded.has(groupKey({ groupId: group.id, role: side.role })) && members.has(groupKey({ groupId: group.id, role: side.role })))
      .map((group) => {
        const key = groupKey({ groupId: group.id, role: side.role })
        const page = members.get(key)!
        return { key, members: page.participants, total: page.count }
      }),
  )
  const allocation = allocateMembers(expandedGroups, budget)

  const nodes: (ServiceRoleFlowNode | ChannelFlowNode | MoreFlowNode | GroupFlowNode)[] = [{
    id: 'channel',
    type: 'channel',
    position: { x: -CHANNEL_NODE_WIDTH / 2, y: -CHANNEL_NODE_HEIGHT / 2 },
    data: { channelAddress: consumers.operation.channelAddress, channelProtocol: consumers.operation.channelProtocol },
    draggable: false,
    connectable: false,
    selectable: false,
  }]
  const edges: Edge[] = []
  const matchIds = new Set<string>()
  const participantNode = (participant: OperationConsumerParticipant, position: { x: number; y: number }): ServiceRoleFlowNode => ({
    id: nodeId(participant), type: 'serviceRole', position, data: { service: participant.service, role: participant.role }, draggable: false, connectable: false,
  })

  sides.forEach((side, sideIndex) => {
    const plain = drawnPlain[sideIndex]
    const plainMore = side.plainBeyondPage + side.plain.length - plain.length
    const items: LayoutItem[] = [
      ...side.groups.map((group) => {
        const share = allocation.get(groupKey({ groupId: group.id, role: side.role }))
        return { size: GROUP_SIZE, members: share ? share.drawn.length + (share.more > 0 ? 1 : 0) : 0 }
      }),
      ...plain.map(() => ({ size: NODE_SIZE })),
      ...(plainMore > 0 ? [{ size: NODE_SIZE }] : []),
    ]
    const placements = columnsItemsLayout(items, NODE_SIZE, CHANNEL_SIZE, COLUMN_SIDES[side.role])
    const edge = (id: string, outer: string, inner: string): Edge => roleEdge(side.role, id, outer, inner)

    side.groups.forEach((group, index) => {
      const key = groupKey({ groupId: group.id, role: side.role })
      const placement = placements[index]
      const id = `group-${side.role}-${group.id}`
      nodes.push({
        id,
        type: GROUP_NODE_TYPE,
        position: placement.position,
        data: {
          groupId: group.id,
          role: side.role,
          name: group.name,
          count: group.count,
          colorKey: groupColorKey(group.id),
          expanded: expanded.has(key),
          total: group.total,
          dimmed: group.dimmed,
        },
        draggable: false,
        connectable: false,
      })
      edges.push(edge(`${id}-edge`, id, 'channel'))
      const share = allocation.get(key)
      if (!share) return
      share.drawn.forEach((participant, memberIndex) => {
        nodes.push(participantNode(participant, placement.members[memberIndex]))
        edges.push(edge(`${nodeId(participant)}-${id}-edge`, nodeId(participant), id))
        if (query && serviceMatchesQuery(participant.service, query)) matchIds.add(nodeId(participant))
      })
      if (share.more > 0) {
        const more: MoreGroup = { groupBy, groupId: group.id, name: group.name }
        nodes.push({
          id: `more-${id}`,
          type: 'more',
          position: placement.members[share.drawn.length],
          data: { count: share.more, ...NODE_SIZE, group: more },
          draggable: false,
          connectable: false,
          selectable: false,
        })
      }
    })

    plain.forEach((participant, index) => {
      nodes.push(participantNode(participant, placements[side.groups.length + index].position))
      edges.push(edge(`${nodeId(participant)}-edge`, nodeId(participant), 'channel'))
      if (searched) matchIds.add(nodeId(participant))
    })
    if (plainMore > 0) {
      nodes.push({
        id: `more-${side.role}`,
        type: 'more',
        position: placements[items.length - 1].position,
        data: { count: plainMore, ...NODE_SIZE },
        draggable: false,
        connectable: false,
        selectable: false,
      })
    }
  })

  return { nodes, edges, centerId: 'channel', matchIds, matchCount: searched ? searched.count : null }
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

  const inlineGraph = useMemo(() => (consumers ? buildInlineGraph(consumers) : null), [consumers])

  const operationId = consumers?.operation.id
  const buildFullscreen = useCallback(
    (view: OperationView) => buildFullscreenGraph(consumers!, view),
    [consumers],
  )
  const searchConsumers = useCallback(
    (search: string, signal: AbortSignal) => operationServicesApi.consumers(operationId!, { pageSize: MAX_FULLSCREEN_PARTICIPANTS, search }, signal),
    [operationId],
  )

  const loadGrouped = useCallback(
    (groupBy: ConsumerGroupBy, search: string, signal: AbortSignal) =>
      operationServicesApi.consumers(operationId!, { pageSize: MAX_FULLSCREEN_PARTICIPANTS, groupBy, search }, signal),
    [operationId],
  )
  const loadGroupMembers = useCallback(
    (groupBy: ConsumerGroupBy, group: GroupRef, signal: AbortSignal) =>
      operationServicesApi.consumers(operationId!, { pageSize: MAX_FULLSCREEN_PARTICIPANTS, groupBy, groupId: group.groupId, role: group.role }, signal),
    [operationId],
  )

  const handleNodeClick: NodeMouseHandler<Node> = (_event, node) => {
    // Channel node click is a no-op, mirroring `EndpointConsumersGraph`'s endpoint-center node.
    if (node.type === 'serviceRole') {
      const data = node.data as ServiceRoleNodeData
      navigate(`/components/${data.service.id}`)
    }
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
      title="Publishers & subscribers"
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
      exportName="operation-participants"
      isLoading={isLoading}
      error={error}
      errorFallback="Failed to load the publishers/subscribers graph"
      onRetry={onRetry}
      emptyMessage="No services are linked to this channel yet"
      canLinkService={canLinkService}
      onLinkService={onLinkService}
      fillHeight
    />
  )
}
