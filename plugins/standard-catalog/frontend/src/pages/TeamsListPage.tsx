import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Loader, Pagination, Text, type TableColumnConfig, type TableSortState } from '@gravity-ui/uikit'
import { EntityTable } from 'frontend/components/EntityTable'
import { EntityPreviewPanel } from 'frontend/components/EntityListPage'
import type { GroupEntity } from 'frontend/lib/types'
import { groupsApi } from 'frontend/lib/entities'
import { teamRailFields } from 'frontend/lib/railFields'
import { useAsync } from 'frontend/lib/useAsync'
import { useEntityRowActivation } from 'frontend/lib/useEntityRowActivation'

const columns: TableColumnConfig<GroupEntity>[] = [
  { id: 'name', name: 'Name', meta: { sort: true }, template: (item) => item.metadata.title || item.metadata.name },
  { id: 'type', name: 'Type', template: (item) => item.spec.type },
  { id: 'members', name: 'Members', template: (item) => String(item.spec.members.length) },
]

/**
 * No row actions here: Groups have no edit/create/delete API or route in this app — they're
 * managed entirely via Django admin (see the empty-state message below), so there's nothing
 * for an "Edit"/"Remove" row action to call. Row activation (click-to-preview,
 * double-click-to-navigate) doesn't depend on that and is wired up like every other list page.
 */
export function TeamsListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [sortState, setSortState] = useState<TableSortState>([{ column: 'name', order: 'asc' }])
  const { data, error, isLoading } = useAsync(
    () => groupsApi.list({ page, pageSize, sort: sortState[0]?.order === 'desc' ? '-name' : 'name' }),
    [page, pageSize, sortState],
  )
  const { selectedId, setSelectedId, handleRowClick } = useEntityRowActivation<GroupEntity>(
    (item) => String(item.id),
    (item) => navigate(`/teams/${item.id}`),
  )

  const selectedItem = data?.page.objectList.find((item) => String(item.id) === selectedId)

  return (
    <div>
      <Text variant="header-1">Teams</Text>
      <p>
        <Text color="secondary">Every Group and the entities it owns</Text>
      </p>
      {error && <Alert theme="danger" message={error.message} />}
      {isLoading && !data ? (
        <Loader size="m" />
      ) : (
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0, maxWidth: 'min(1440px, 100%)' }}>
            <EntityTable
              data={data?.page.objectList ?? []}
              columns={columns}
              getRowId={(item) => String(item.id)}
              onRowClick={handleRowClick}
              sortState={sortState}
              onSortStateChange={(nextSortState) => { setSortState(nextSortState); setPage(1) }}
              disableDataSorting
              emptyMessage="No teams yet — create one in Django admin"
            />
            {data && (
              <div style={{ marginTop: 16 }}>
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={data.count}
                  pageSizeOptions={[15, 30, 50, 100]}
                  showInput
                  onUpdate={(nextPage, nextPageSize) => {
                    setPage(nextPageSize === pageSize ? nextPage : 1)
                    setPageSize(nextPageSize)
                  }}
                />
              </div>
            )}
          </div>
          {selectedItem && (
            <EntityPreviewPanel
              item={selectedItem}
              title={selectedItem.metadata.title || selectedItem.metadata.name}
              description={selectedItem.metadata.description}
              railFields={teamRailFields}
              onClose={() => setSelectedId(null)}
              onOpen={() => navigate(`/teams/${selectedItem.id}`)}
            />
          )}
        </div>
      )}
    </div>
  )
}
