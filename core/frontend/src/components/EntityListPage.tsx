import { useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Checkbox, Icon, Label, Loader, Pagination, Text, type TableColumnConfig, type TableSortState } from '@gravity-ui/uikit'
import { ArrowUpRightFromSquare, Xmark } from '@gravity-ui/icons'
import { ConfirmDialog } from './ConfirmDialog'
import { EntityActionsTable } from './EntityTable'
import { FilterBar, type FilterConfig, type SelectFilterConfig } from './FilterBar'
import type { RailField } from './EntityDetailShell'
import { groupsApi, type ListFilters } from '../lib/entities'
import { entityRowActions } from '../lib/entityRowActions'
import { OwnerIcon } from '../lib/icons'
import { refName, type EntityStatus, type Metadata, type Paginated } from '../lib/types'
import { tagsApi } from '../lib/entities'
import { useAsync } from '../lib/useAsync'
import { useConfirm } from '../lib/useConfirm'
import { useEntityRowActivation } from '../lib/useEntityRowActivation'
import { useSession } from '../lib/SessionContext'

interface EntityListPageProps<T extends { id: string; metadata: Metadata; ingestedFrom: string | null; status?: EntityStatus }> {
  title: string
  description: string
  addLabel: string
  onAdd: () => void
  fetchList: (filters: ListFilters) => Promise<Paginated<T>>
  columns: TableColumnConfig<T>[]
  rowTo: (item: T) => string
  /** Trimmed summary fields shown in the row-click preview panel (catalog-web-ui spec). */
  railFields: (item: T) => RailField[]
  /** Soft-removes the entity by id, for the row-actions "Remove" action (entity-removal-lifecycle
   * spec) — Revive/Purge for an already-removed entity live on its own detail page, not here. */
  remove: (id: string) => Promise<unknown>
  renderPreviewSection?: (item: T) => ReactNode
  /** Extra Select filters beyond the always-present Owner + search (e.g. Lifecycle, Type). */
  extraFilters?: (setFilter: (key: string, value: string | null) => void, values: Record<string, string | null>) => SelectFilterConfig[]
}

/** Filterable/searchable list page shared by Systems/Components/Resources/APIs (catalog-web-ui spec). */
/** Percent widths for the common columns; with `table-layout: fixed`, columns without one split the remainder. */
const DEFAULT_COLUMN_WIDTHS: Record<string, string> = { name: '24%', description: '32%', owner: '16%', tags: '24%' }

export function EntityListPage<T extends { id: string; metadata: Metadata; ingestedFrom: string | null; status?: EntityStatus }>({
  title,
  description,
  addLabel,
  onAdd,
  fetchList,
  columns,
  rowTo,
  railFields,
  remove,
  renderPreviewSection,
  extraFilters,
}: EntityListPageProps<T>) {
  const navigate = useNavigate()
  // catalog-web-ui spec's "Read-only session sees no Add action" / "...no row-level actions
  // control" — hides the write affordances this shared page renders for every kind that uses it.
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const [search, setSearch] = useState('')
  const [owner, setOwner] = useState<string | null>(null)
  const [extraValues, setExtraValues] = useState<Record<string, string | null>>({})
  const [tags, setTags] = useState<string[]>([])
  // entity-catalog spec's "List filtering and search": removed entities are hidden by
  // default; this is the explicit, ungated "show removed" opt-in (entity-removal-lifecycle
  // spec) — open to any authenticated viewer, not scoped to the owning Group.
  const [showRemoved, setShowRemoved] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [sortState, setSortState] = useState<TableSortState>([{ column: 'name', order: 'asc' }])
  const { selectedId, setSelectedId, handleRowClick } = useEntityRowActivation<T>(
    (item) => String(item.id),
    (item) => navigate(rowTo(item)),
  )
  const { confirm, dialogProps } = useConfirm()

  const setExtra = (key: string, value: string | null) => {
    setPage(1)
    setExtraValues((prev) => ({ ...prev, [key]: value }))
  }

  const filters: ListFilters = useMemo(
    () => ({
      q: search || undefined,
      owner: owner || undefined,
      tags: tags.length ? tags : undefined,
      status: showRemoved ? 'all' : undefined,
      sort: sortState[0]?.order === 'desc' ? '-name' : 'name',
      ...extraValues,
    }),
    [search, owner, tags, showRemoved, extraValues, sortState],
  )

  const { data: groups } = useAsync(() => groupsApi.list(), [])
  const { data: availableTags } = useAsync(() => tagsApi.list(), [])
  const { data, error, isLoading, reload } = useAsync(
    () => fetchList({ ...filters, page, pageSize }),
    [JSON.stringify(filters), page, pageSize],
  )

  async function handleRemove(item: T) {
    const name = item.metadata.title || item.metadata.name
    if (!(await confirm({ title: 'Remove', message: `Remove "${name}"? It can be revived later.`, preset: 'default' }))) return
    await remove(item.id)
    reload()
  }

  const ownerOptions = (groups?.page.objectList ?? []).map((group) => ({
    value: group.metadata.name,
    content: group.metadata.title || group.metadata.name,
  }))

  const filterConfigs: FilterConfig[] = [
    {
      label: 'Owner',
      value: owner,
      onChange: (value: string | null) => { setOwner(value); setPage(1) },
      options: ownerOptions,
    },
    {
      label: 'Tags',
      value: tags,
      onChange: (values: string[]) => { setTags(values); setPage(1) },
      options: (availableTags ?? []).map((tag) => ({ value: tag.name, content: tag.name })),
    },
    ...(extraFilters ? extraFilters(setExtra, extraValues) : []),
  ]

  const selectedItem = data?.page.objectList.find((item) => String(item.id) === selectedId)

  const statusColumn: TableColumnConfig<T> = {
    id: 'status',
    name: 'Status',
    template: (item) => (item.status === 'removed' ? <Label theme="warning">Removed</Label> : null),
  }

  return (
    <div>
      <Text variant="header-1">{title}</Text>
      <p>
        <Text color="secondary">{description}</Text>
      </p>
      <div style={{ maxWidth: 'min(1440px, 100%)' }}>
        <FilterBar
          search={search}
          onSearchChange={(value) => { setSearch(value); setPage(1) }}
          filters={filterConfigs}
          addLabel={isReadOnly ? undefined : addLabel}
          onAdd={isReadOnly ? undefined : onAdd}
          extra={
            <Checkbox
              checked={showRemoved}
              onUpdate={(checked) => { setShowRemoved(checked); setPage(1) }}
            >
              Show removed
            </Checkbox>
          }
        />
        {error && <Alert theme="danger" message={error.message} />}
      </div>
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0, maxWidth: 'min(1440px, 100%)' }}>
          {isLoading && !data ? (
            <Loader size="m" />
          ) : (
            <>
              <EntityActionsTable
                className="entity-list-table"
                data={data?.page.objectList ?? []}
                columns={[
                  ...columns.map((column) => {
                    const sized = { ...column, width: column.width ?? DEFAULT_COLUMN_WIDTHS[column.id] }
                    return column.id === 'name' ? { ...sized, meta: { ...column.meta, sort: true } } : sized
                  }),
                  ...(showRemoved ? [statusColumn] : []),
                ]}
                getRowId={(item) => String(item.id)}
                onRowClick={handleRowClick}
                sortState={sortState}
                onSortStateChange={(nextSortState) => { setSortState(nextSortState); setPage(1) }}
                disableDataSorting
                getRowActions={(item) =>
                  item.ingestedFrom || item.status === 'removed' || isReadOnly
                    ? []
                    : entityRowActions(() => navigate(`${rowTo(item)}/edit`), () => void handleRemove(item))
                }
                emptyMessage="No entities match these filters"
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
            title={selectedItem.metadata.title || selectedItem.metadata.name}
            description={selectedItem.metadata.description}
            railFields={railFields}
            onClose={() => setSelectedId(null)}
            onOpen={() => navigate(rowTo(selectedItem))}
            previewSection={renderPreviewSection?.(selectedItem)}
          />
        )}
      </div>
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}

/**
 * Right-side rail shown on row click, shared by every entity list page (catalog-web-ui spec).
 * Takes `title`/`description` directly rather than assuming a `metadata` shape on `T`, since
 * `FlowEntity` carries those fields at its top level instead of under `metadata`.
 */
export function EntityPreviewPanel<T>({
  item,
  title,
  description,
  railFields,
  onClose,
  onOpen,
  previewSection,
}: {
  item: T
  title: string
  description: string
  railFields: (item: T) => RailField[]
  onClose: () => void
  onOpen: () => void
  previewSection?: ReactNode
}) {
  return (
    <aside
      style={{
        width: 320,
        flexShrink: 0,
        border: '1px solid var(--g-color-line-generic)',
        borderRadius: 8,
        padding: 20,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <Text variant="header-2">{title}</Text>
        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
          <Button view="flat" size="s" onClick={onOpen} aria-label="Open full details">
            <Icon data={ArrowUpRightFromSquare} size={16} />
          </Button>
          <Button view="flat" size="s" onClick={onClose} aria-label="Close preview">
            <Icon data={Xmark} size={16} />
          </Button>
        </div>
      </div>

      <Text variant="subheader-2" style={{ display: 'block', marginTop: 20, marginBottom: 12 }}>
        About
      </Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {railFields(item).map((field) => (
          <div key={field.label}>
            <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>
              {field.label}
            </Text>
            <div>{field.value}</div>
          </div>
        ))}
      </div>

      <Text variant="subheader-2" style={{ display: 'block', marginTop: 20, marginBottom: 8 }}>
        Description
      </Text>
      <Text color="secondary">{description || 'No description'}</Text>
      {previewSection}
    </aside>
  )
}

/** `owner:group ref` -> icon + display name, for table cells. */
export function ownerCell<T extends { spec: { owner: string } }>(item: T) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <Icon data={OwnerIcon} size={16} />
      {refName(item.spec.owner)}
    </div>
  )
}
