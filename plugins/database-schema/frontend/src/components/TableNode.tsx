// React Flow custom node for a single table: name header, columns
// with PK/FK markers. One target + one source `Handle` per column
// so relation edges land on the specific referencing/referenced column
// rather than the table as a whole, ChartDB-style. Handles stay in the DOM
// (edges anchor to them by id) but are visually hidden and non-interactive —
// the diagram is read-only, so there's nothing to drag a connection from.
import { Fragment, memo } from 'react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Icon, Text } from '@gravity-ui/uikit'
import { Key, Link } from '@gravity-ui/icons'
import type { ParsedSchemaColumn, ParsedSchemaTable } from '../lib/databaseSchemaApi'
import { TABLE_NODE_HEADER_HEIGHT, TABLE_NODE_ROW_HEIGHT, TABLE_NODE_WIDTH, columnHandleTop } from '../lib/tableNodeGeometry'

export interface TableNodeData extends Record<string, unknown> {
  table: ParsedSchemaTable
  primaryKeyColumns: Set<string>
  foreignKeyColumns: Set<string>
}

export type TableFlowNode = Node<TableNodeData, 'table'>

// React Flow anchors an edge to a handle's outer edge (the side facing away
// from the node), not its center, so a visible handle dot doesn't get drawn
// over by the line. At the default 6px handle size that puts the anchor
// ~3px outside the table border — invisible when the dot filled that gap,
// but a visible gap once the dot itself is hidden. Zeroing the handle's box
// collapses outer-edge and center onto the border, closing the gap.
const HIDDEN_HANDLE_STYLE = {
  opacity: 0,
  pointerEvents: 'none' as const,
  width: 0,
  height: 0,
  minWidth: 0,
  minHeight: 0,
  border: 'none',
}

function ColumnRow({ column, isPrimaryKey, isForeignKey }: { column: ParsedSchemaColumn, isPrimaryKey: boolean, isForeignKey: boolean }) {
  return (
    <div style={{ height: TABLE_NODE_ROW_HEIGHT, display: 'flex', alignItems: 'center', gap: 6, padding: '0 10px', borderTop: '1px solid var(--g-color-line-generic)' }}>
      <div style={{ width: 14, flexShrink: 0, display: 'flex' }}>
        {isPrimaryKey && <Icon data={Key} size={12} />}
      </div>
      <Text variant="body-2" ellipsis style={{ flexShrink: 0, maxWidth: 110, fontFamily: 'var(--g-font-family-monospace, ui-monospace, monospace)' }}>
        {column.name}
      </Text>
      <Text color="secondary" variant="caption-2" ellipsis style={{ minWidth: 0, fontFamily: 'var(--g-font-family-monospace, ui-monospace, monospace)' }}>
        {column.type}
        {!column.nullable && ' NOT NULL'}
      </Text>
      <div style={{ marginLeft: 'auto', width: 14, flexShrink: 0, display: 'flex' }}>
        {isForeignKey && <Icon data={Link} size={12} />}
      </div>
    </div>
  )
}

function TableNodeComponent({ data }: NodeProps<TableFlowNode>) {
  const { table, primaryKeyColumns, foreignKeyColumns } = data
  return (
    <div style={{ width: TABLE_NODE_WIDTH, border: '1px solid var(--g-color-line-generic)', borderRadius: 8, overflow: 'hidden', background: 'var(--g-color-base-background)', boxShadow: '0 1px 4px rgba(0, 0, 0, 0.12)' }}>
      <div style={{ height: TABLE_NODE_HEADER_HEIGHT, display: 'flex', alignItems: 'center', padding: '0 10px', background: 'var(--g-color-base-generic)' }}>
        <Text variant="subheader-1" ellipsis>{table.name}</Text>
      </div>
      {table.columns.map((column, index) => (
        <Fragment key={column.name}>
          <ColumnRow
            column={column}
            isPrimaryKey={primaryKeyColumns.has(column.name)}
            isForeignKey={foreignKeyColumns.has(column.name)}
          />
          <Handle type="target" position={Position.Left} id={`${column.name}-target`} style={{ ...HIDDEN_HANDLE_STYLE, top: columnHandleTop(index) }} />
          <Handle type="source" position={Position.Right} id={`${column.name}-source`} style={{ ...HIDDEN_HANDLE_STYLE, top: columnHandleTop(index) }} />
        </Fragment>
      ))}
    </div>
  )
}

export const TableNode = memo(TableNodeComponent)
