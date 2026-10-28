import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Pencil, TrashBin } from '@gravity-ui/icons'
import { Alert, Icon, Loader, Pagination, type TableAction, type TableColumnConfig, type TableSortState } from '@gravity-ui/uikit'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { EntityActionsTable } from 'frontend/components/EntityTable'
import { FilterBar } from 'frontend/components/FilterBar'
import { errorMessage } from 'frontend/lib/api'
import { useSession } from 'frontend/lib/SessionContext'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { NEW_VIEW_PATH, VIEWS_TAB, viewEditPath, viewPath } from '../lib/customView'
import { viewsApi, type SavedView } from '../lib/customViewApi'

const columns: TableColumnConfig<SavedView>[] = [
  { id: 'name', name: 'Name', meta: { sort: true }, template: (item) => item.name },
  { id: 'description', name: 'Description', template: (item) => item.description || '—' },
]

function rowActions(onEdit: () => void, onDelete: () => void): TableAction<SavedView>[] {
  return [
    { text: 'Edit', icon: <Icon data={Pencil} size={16} />, theme: 'normal', handler: onEdit },
    { text: 'Delete', icon: <Icon data={TrashBin} size={16} />, theme: 'danger', handler: onDelete },
  ]
}

const PAGE_SIZE_OPTIONS = [15, 30, 50, 100]

/** The Views tab of System Map: saved custom views, paginated and searchable by name. */
export function ViewsList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const [search, setSearch] = useState('')
  const [pageSize, setPageSize] = useState(15)
  const [sortState, setSortState] = useState<TableSortState>([{ column: 'name', order: 'asc' }])
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const { confirm, dialogProps } = useConfirm()

  const setPage = (next: number) => setSearchParams(next > 1 ? { tab: VIEWS_TAB, page: String(next) } : { tab: VIEWS_TAB })
  const filters = useMemo(
    () => ({ q: search || undefined, page, pageSize, sort: sortState[0]?.order === 'desc' ? ('-name' as const) : ('name' as const) }),
    [search, page, pageSize, sortState],
  )
  const { data, error, isLoading, reload } = useAsync(() => viewsApi.list(filters), [JSON.stringify(filters)])

  async function handleRemove(item: SavedView) {
    if (!(await confirm({ title: 'Delete view', message: `Delete "${item.name}"? This cannot be undone.`, confirmText: 'Delete', preset: 'danger' }))) return
    try {
      await viewsApi.remove(item.id)
      setDeleteError(null)
      reload()
    } catch (err) {
      setDeleteError(errorMessage(err, 'The view could not be deleted'))
    }
  }

  return (
    <div style={{ paddingTop: 16, maxWidth: 'min(1440px, 100%)' }}>
      <FilterBar
        search={search}
        onSearchChange={(value) => { setSearch(value); setPage(1) }}
        addLabel={isReadOnly ? undefined : 'Create view'}
        onAdd={isReadOnly ? undefined : () => navigate(NEW_VIEW_PATH)}
      />
      {error && <Alert theme="danger" message={error.message} />}
      {deleteError && <Alert theme="danger" message={deleteError} />}
      {isLoading && !data ? (
        <Loader size="m" />
      ) : (
        <>
          <EntityActionsTable
            data={data?.page.objectList ?? []}
            columns={columns}
            getRowId={(item) => item.id}
            onRowClick={(item) => navigate(viewPath(item.id))}
            sortState={sortState}
            onSortStateChange={(next) => { setSortState(next); setPage(1) }}
            disableDataSorting
            getRowActions={(item) => (isReadOnly ? [] : rowActions(() => navigate(viewEditPath(item.id)), () => void handleRemove(item)))}
            emptyMessage={search ? 'No views match this search' : isReadOnly ? 'No views yet' : 'No views yet. Create a view to save a slice of the architecture.'}
          />
          {data && (
            <div style={{ marginTop: 16 }}>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={data.count}
                pageSizeOptions={PAGE_SIZE_OPTIONS}
                showInput
                onUpdate={(nextPage, nextPageSize) => {
                  setPage(nextPageSize === pageSize ? nextPage : 1)
                  setPageSize(nextPageSize)
                }}
              />
            </div>
          )}
        </>
      )}
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}
