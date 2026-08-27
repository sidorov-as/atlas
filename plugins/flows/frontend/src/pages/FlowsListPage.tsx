import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Loader, Pagination, Text, type TableColumnConfig, type TableSortState } from '@gravity-ui/uikit'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { EntityActionsTable } from 'frontend/components/EntityTable'
import { EntityPreviewPanel } from 'frontend/components/EntityListPage'
import { FilterBar, type SelectFilterConfig } from 'frontend/components/FilterBar'
import { flowsApi, groupsApi, systemsApi } from 'frontend/lib/entities'
import { entityRowActions } from 'frontend/lib/entityRowActions'
import { useSession } from 'frontend/lib/SessionContext'
import { flowRailFields } from 'frontend/lib/railFields'
import { refName, type FlowEntity } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { useEntityRowActivation } from 'frontend/lib/useEntityRowActivation'

const columns: TableColumnConfig<FlowEntity>[] = [
  { id: 'name', name: 'Name', meta: { sort: true }, template: (item) => item.name },
  { id: 'system', name: 'System', template: (item) => refName(item.system) },
  { id: 'steps', name: 'Steps', template: (item) => String(item.steps.length) },
  { id: 'description', name: 'Description', template: (item) => item.description || '—' },
]

/** List page for Flows: search + System + Team filters over `FilterBar`/`EntityTable` (flow-management spec). */
export function FlowsListPage() {
  const navigate = useNavigate()
  // flow-management spec's "Read-only session sees no Flow Add action" / "...no row actions
  // on the Flows list" — outside EntityListPage, so this list page gates itself.
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const [search, setSearch] = useState('')
  const [system, setSystem] = useState<string | null>(null)
  const [team, setTeam] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [sortState, setSortState] = useState<TableSortState>([{ column: 'name', order: 'asc' }])
  const { selectedId, setSelectedId, handleRowClick } = useEntityRowActivation<FlowEntity>(
    (item) => String(item.id),
    (item) => navigate(`/flows/${item.id}`),
  )
  const { confirm, dialogProps } = useConfirm()

  const filters = useMemo(
    () => ({ q: search || undefined, system: system || undefined, team: team || undefined, page, pageSize, sort: sortState[0]?.order === 'desc' ? '-name' as const : 'name' as const }),
    [search, system, team, page, pageSize, sortState],
  )

  const { data: systems } = useAsync(() => systemsApi.list({ pageSize: 100 }), [])
  const { data: groups } = useAsync(() => groupsApi.list({ pageSize: 100 }), [])
  const { data, error, isLoading, reload } = useAsync(() => flowsApi.list(filters), [JSON.stringify(filters)])

  async function handleRemove(item: FlowEntity) {
    if (!(await confirm({ title: 'Delete', message: `Delete "${item.name}"? This cannot be undone.`, preset: 'danger' }))) return
    await flowsApi.remove(item.id)
    reload()
  }

  const selectedItem = data?.page.objectList.find((item) => String(item.id) === selectedId)

  const systemOptions = (systems?.page.objectList ?? []).map((item) => ({
    value: `system:${item.metadata.name}`,
    content: item.metadata.title || item.metadata.name,
  }))
  const teamOptions = (groups?.page.objectList ?? []).map((item) => ({
    value: `group:${item.metadata.name}`,
    content: item.metadata.title || item.metadata.name,
  }))

  const filterConfigs: SelectFilterConfig[] = [
    { label: 'System', value: system, onChange: (value) => { setSystem(value); setPage(1) }, options: systemOptions },
    { label: 'Team', value: team, onChange: (value) => { setTeam(value); setPage(1) }, options: teamOptions },
  ]

  return (
    <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
      <div style={{ flex: 1, minWidth: 0, maxWidth: 'min(1440px, 100%)' }}>
        <Text variant="header-1">Flows</Text>
        <p>
          <Text color="secondary">Narrated, cross-system processes documented as step sequences</Text>
        </p>
        <FilterBar
          search={search}
          onSearchChange={(value) => { setSearch(value); setPage(1) }}
          filters={filterConfigs}
          addLabel={isReadOnly ? undefined : 'Add Flow'}
          onAdd={isReadOnly ? undefined : () => navigate('/flows/new')}
        />
        {error && <Alert theme="danger" message={error.message} />}
        {isLoading && !data ? (
          <Loader size="m" />
        ) : (
          <>
            <EntityActionsTable
              data={data?.page.objectList ?? []}
              columns={columns}
              getRowId={(item) => String(item.id)}
              onRowClick={handleRowClick}
              sortState={sortState}
              onSortStateChange={(nextSortState) => { setSortState(nextSortState); setPage(1) }}
              disableDataSorting
              getRowActions={(item) =>
                isReadOnly
                  ? []
                  : entityRowActions(() => navigate(`/flows/${item.id}/edit`), () => void handleRemove(item))
              }
              emptyMessage="No flows match these filters"
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
          </>
        )}
      </div>
      {selectedItem && (
        <EntityPreviewPanel
          item={selectedItem}
          title={selectedItem.name}
          description={selectedItem.description}
          railFields={flowRailFields}
          onClose={() => setSelectedId(null)}
          onOpen={() => navigate(`/flows/${selectedItem.id}`)}
        />
      )}
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}
