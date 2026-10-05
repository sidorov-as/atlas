// Group node shared by both dependency graphs: stands in for the Services of
// one team or system. It shows the group's name, a color mark, the number of
// Services and a chevron for its expanded state. Activating it (handled by the
// graph shell) expands or collapses the group in place. It has a source and a
// target handle, both centered, so it can connect to the center node and take
// the edges of its own expanded Services.
import { memo } from 'react'
import { SideHandles } from './SideHandles'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { ChevronDown, ChevronRight } from '@gravity-ui/icons'
import { Icon, Text } from '@gravity-ui/uikit'

// Not 'group': React Flow ships a built-in node type of that name with its own
// border, padding and background, which would frame every card.
export const GROUP_NODE_TYPE = 'consumerGroup'

export const GROUP_NODE_WIDTH = 180
export const GROUP_NODE_HEIGHT = 64

const CENTERED_HANDLE_STYLE = {
  opacity: 0,
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
} as const

export interface GroupNodeData extends Record<string, unknown> {
  groupId: string
  name: string
  /** Services in the group (exact, over every linked Service — or over the search matches while searching). */
  count: number
  /** Tag-palette key the color mark is taken from; stable per group id. */
  colorKey: string
  expanded: boolean
  /** While a search is active: the group's size without the search, so the label reads "N of M matches". */
  total?: number
  /** A search is active and no Service of the group matches. */
  dimmed?: boolean
}

export type GroupFlowNode = Node<GroupNodeData, typeof GROUP_NODE_TYPE>

/** "12 services", or "2 of 5 matches" while a search is active. */
export function groupCaption(data: Pick<GroupNodeData, 'count' | 'total'>): string {
  if (data.total !== undefined) return `${data.count} of ${data.total} matches`
  return `${data.count} ${data.count === 1 ? 'service' : 'services'}`
}

function GroupNodeComponent({ data }: NodeProps<GroupFlowNode>) {
  return (
    <div
      role="button"
      aria-expanded={data.expanded}
      aria-label={`${data.name}, ${groupCaption(data)}`}
      className={`tag-preset-${data.colorKey}`}
      style={{
        boxSizing: 'border-box',
        width: GROUP_NODE_WIDTH,
        height: GROUP_NODE_HEIGHT,
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        border: '1px solid var(--g-color-line-generic)',
        borderRadius: 8,
        background: 'var(--g-color-base-background)',
        boxShadow: '0 1px 4px rgba(0, 0, 0, 0.12)',
        cursor: 'pointer',
      }}
    >
      <Handle type="source" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <Handle type="target" position={Position.Top} style={CENTERED_HANDLE_STYLE} />
      <SideHandles />
      <span
        aria-hidden
        style={{ flex: '0 0 auto', width: 10, height: 10, borderRadius: '50%', background: 'var(--tag-fg)' }}
      />
      <div style={{ flex: '1 1 auto', minWidth: 0 }}>
        <Text variant="body-2" ellipsis style={{ display: 'block' }}>{data.name}</Text>
        <Text color="secondary" variant="caption-2" ellipsis style={{ display: 'block' }}>{groupCaption(data)}</Text>
      </div>
      <Icon data={data.expanded ? ChevronDown : ChevronRight} size={16} />
    </div>
  )
}

export const GroupNode = memo(GroupNodeComponent)
