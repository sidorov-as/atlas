import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Icon, Label, Select, SegmentedRadioGroup, Skeleton, TextInput } from '@gravity-ui/uikit'
import { TriangleExclamation } from '@gravity-ui/icons'
import { EntityTable } from 'frontend/components/EntityTable'
import { useAsync } from 'frontend/lib/useAsync'
import { DEFAULT_PAGE_SIZE, ListPagination } from './ListPagination'
import { MethodBadge } from './MethodBadge'
import { endpointsApi } from '../lib/entities'
import type { Endpoint, EndpointMethod, EndpointStatus } from '../lib/types'

const METHODS: EndpointMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const METHOD_OPTIONS = METHODS.map((value) => ({ value, content: value }))
const DEPRECATED_OPTIONS = [
  { value: 'true', content: 'Deprecated only' },
  { value: 'false', content: 'Not deprecated' },
]
const STATUS_OPTIONS: { value: EndpointStatus; content: string }[] = [
  { value: 'active', content: 'Active' },
  { value: 'removed', content: 'Removed endpoints' },
]

/** Endpoints tab on an API's detail page (a new `entityDetailTab`, not a direct `ApiDetailPage.tsx` edit, matching the existing Overview/Specification/Relations tabs' pattern). */
export function EndpointsListTab({ apiId }: { apiId: string }) {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [method, setMethod] = useState<EndpointMethod | null>(null)
  const [deprecated, setDeprecated] = useState<'true' | 'false' | null>(null)
  const [status, setStatus] = useState<EndpointStatus>('active')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  const filters = useMemo(
    () => ({
      search: search || undefined,
      method: method ?? undefined,
      deprecated: deprecated === null ? undefined : deprecated === 'true',
      status,
    }),
    [search, method, deprecated, status],
  )

  const { data: endpoints, error, isLoading } = useAsync(
    () => endpointsApi.list(apiId, filters),
    [apiId, JSON.stringify(filters)],
  )

  // The list endpoint isn't paginated, so slice client-side after the server-side filters.
  const total = endpoints?.length ?? 0
  const lastPage = Math.max(1, Math.ceil(total / pageSize))
  const currentPage = Math.min(page, lastPage)
  const pageItems = (endpoints ?? []).slice((currentPage - 1) * pageSize, currentPage * pageSize)

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
        <TextInput placeholder="Search path, summary, operation ID…" value={search} onUpdate={(value) => { setSearch(value); setPage(1) }} hasClear style={{ maxWidth: 280, flex: '1 1 220px' }} />
        <Select
          placeholder="Method"
          value={method ? [method] : []}
          onUpdate={(value) => { setMethod((value[0] as EndpointMethod) ?? null); setPage(1) }}
          options={METHOD_OPTIONS}
          hasClear
          width={140}
        />
        <Select
          placeholder="Deprecated"
          value={deprecated ? [deprecated] : []}
          onUpdate={(value) => { setDeprecated((value[0] as 'true' | 'false') ?? null); setPage(1) }}
          options={DEPRECATED_OPTIONS}
          hasClear
          width={170}
        />
        <SegmentedRadioGroup
          value={status}
          onUpdate={(value) => { setStatus(value as EndpointStatus); setPage(1) }}
          options={STATUS_OPTIONS}
        />
      </div>

      {error && <Alert theme="danger" message={error.message} />}

      {isLoading && !endpoints ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Skeleton style={{ height: 36 }} />
          <Skeleton style={{ height: 36 }} />
          <Skeleton style={{ height: 36 }} />
        </div>
      ) : (
        <EntityTable
          data={pageItems}
          columns={[
            { id: 'method', name: 'Method', template: (item: Endpoint) => <MethodBadge method={item.method} /> },
            { id: 'path', name: 'Path', template: (item: Endpoint) => <code>{item.path}</code> },
            { id: 'summary', name: 'Summary', template: (item: Endpoint) => item.summary || item.operationId || '—' },
            {
              id: 'deprecated',
              name: '',
              template: (item: Endpoint) =>
                item.deprecated ? (
                  <Label theme="warning" icon={<Icon data={TriangleExclamation} size={12} />}>
                    Deprecated
                  </Label>
                ) : null,
            },
          ]}
          getRowId={(item: Endpoint) => item.id}
          onRowClick={(item: Endpoint) => navigate(`/apis/${apiId}/endpoints/${item.id}`)}
          emptyMessage={status === 'removed' ? 'No removed endpoints' : 'No endpoints'}
        />
      )}
      <ListPagination
        page={currentPage}
        pageSize={pageSize}
        total={total}
        onUpdate={(nextPage, nextPageSize) => {
          setPage(nextPage)
          setPageSize(nextPageSize)
        }}
      />
    </div>
  )
}
