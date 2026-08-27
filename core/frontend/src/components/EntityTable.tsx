import type { ComponentType } from 'react'
import { Table, withTableActions, withTableSorting, type TableDataItem, type TableProps, type WithTableActionsProps, type WithTableSortingProps } from '@gravity-ui/uikit'

/** `Table` wrapped in the shared max-width frame — used by every table usage (catalog-web-ui spec). */
export function EntityTable<I extends TableDataItem>(props: TableProps<I> & WithTableSortingProps) {
  const SortableTable = withTableSorting(Table) as unknown as ComponentType<TableProps<I> & WithTableSortingProps>
  return (
    <div className="entity-table-frame">
      <SortableTable width="max" {...props} />
    </div>
  )
}

// `withTableActions` isn't generic-inference-friendly across call sites, so `Table` is
// instantiated once here and re-cast to the caller's `I` in `EntityActionsTable` below.
const TableWithActions = withTableSorting(withTableActions(Table)) as unknown as ComponentType<TableProps<TableDataItem> & WithTableActionsProps<TableDataItem> & WithTableSortingProps>

/** `EntityTable` variant with a row-actions menu — used by list pages with row-level Edit/Remove (catalog-web-ui spec). */
export function EntityActionsTable<I extends TableDataItem>(props: TableProps<I> & WithTableActionsProps<I> & WithTableSortingProps) {
  const Comp = TableWithActions as unknown as ComponentType<TableProps<I> & WithTableActionsProps<I> & WithTableSortingProps>
  return (
    <div className="entity-table-frame">
      <Comp width="max" {...props} />
    </div>
  )
}
