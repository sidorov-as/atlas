// Autolayout for the ER Diagram graph (elkjs, for autolayout
// — already a proven dependency in this codebase via
// `frontend/src/lib/flowLayout.ts`'s `useElk`/`@gravity-ui/graph` layout,
// used here directly against React Flow node/edge shapes instead). Runs only
// on demand (initial render, or an explicit autolayout button press),
// never on every render, so manual dragging in between calls is never
// overwritten.
import ELK from 'elkjs/lib/elk.bundled.js'
import type { ElkNode } from 'elkjs'
import type { ParsedSchemaRelation, ParsedSchemaTable } from './databaseSchemaApi'

const elk = new ELK()

export interface ErDiagramNodeSize {
  width: number
  height: number
}

export type ErDiagramPositions = Record<string, { x: number, y: number }>

/** Lays out `tables` (as ELK nodes sized by `sizeOf`) with one edge per
 * table-to-table relation — table-level, not column-level, since ELK only
 * needs the graph shape to place tables, not the exact handle a relation
 * connects to. */
export async function layoutErDiagramTables(
  tables: ParsedSchemaTable[],
  relations: ParsedSchemaRelation[],
  sizeOf: (table: ParsedSchemaTable) => ErDiagramNodeSize,
): Promise<ErDiagramPositions> {
  const tableNames = new Set(tables.map((table) => table.name))
  const graph: ElkNode = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.layered.spacing.nodeNodeBetweenLayers': '80',
      'elk.spacing.nodeNode': '40',
    },
    children: tables.map((table) => ({ id: table.name, ...sizeOf(table) })),
    edges: relations
      .filter((relation) => tableNames.has(relation.table) && tableNames.has(relation.parent_table))
      .map((relation, index) => ({
        id: `${relation.table}->${relation.parent_table}-${index}`,
        sources: [relation.table],
        targets: [relation.parent_table],
      })),
  }

  const result = await elk.layout(graph)
  const positions: ErDiagramPositions = {}
  for (const child of result.children ?? []) {
    positions[child.id] = { x: child.x ?? 0, y: child.y ?? 0 }
  }
  return positions
}
