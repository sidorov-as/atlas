// Geometry shared between `TableNode` (rendering, including per-column
// `Handle` placement) and `erDiagramLayout`'s ELK sizing — kept out of
// `TableNode.tsx` itself so that file only exports the component (React
// Fast Refresh needs a component-only module to hot-reload cleanly).
import type { ParsedSchemaTable } from './databaseSchemaApi'

export const TABLE_NODE_WIDTH = 260
export const TABLE_NODE_HEADER_HEIGHT = 36
export const TABLE_NODE_ROW_HEIGHT = 28

export function tableNodeSize(table: ParsedSchemaTable): { width: number, height: number } {
  return { width: TABLE_NODE_WIDTH, height: TABLE_NODE_HEADER_HEIGHT + table.columns.length * TABLE_NODE_ROW_HEIGHT }
}

export function columnHandleTop(index: number): number {
  return TABLE_NODE_HEADER_HEIGHT + index * TABLE_NODE_ROW_HEIGHT + TABLE_NODE_ROW_HEIGHT / 2
}
