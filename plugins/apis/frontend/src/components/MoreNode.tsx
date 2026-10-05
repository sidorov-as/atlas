// "+N more" node shared by both dependency graphs: stands in for linked
// Services that are not drawn. It has no handles and no edge — it is not a
// Service, so it never connects to the center node or navigates to a Service.
import { memo } from 'react'
import type { Node, NodeProps } from '@xyflow/react'
import { Text } from '@gravity-ui/uikit'

export interface MoreNodeData extends Record<string, unknown> {
  /** How many linked Services are not drawn. */
  count: number
  /** Same box as the Service nodes it sits among, so the layout can treat it as one of them. */
  width: number
  height: number
  /** Set on the "+N more" node that ends an expanded group's block: which group it stands in for. */
  group?: { groupBy: 'team' | 'system'; groupId: string; name: string }
}

export type MoreFlowNode = Node<MoreNodeData, 'more'>

function MoreNodeComponent({ data }: NodeProps<MoreFlowNode>) {
  return (
    <div
      role="button"
      style={{
        boxSizing: 'border-box',
        width: data.width,
        height: data.height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px dashed var(--g-color-line-brand)',
        borderRadius: 8,
        background: 'var(--g-color-base-background)',
        cursor: 'pointer',
      }}
    >
      <Text variant="body-2" color="secondary">+{data.count} more</Text>
    </div>
  )
}

export const MoreNode = memo(MoreNodeComponent)
