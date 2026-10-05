import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Icon, Label, Select, SegmentedRadioGroup, Skeleton, Text, TextInput } from '@gravity-ui/uikit'
import { TriangleExclamation } from '@gravity-ui/icons'
import { EntityTable } from 'frontend/components/EntityTable'
import { useAsync } from 'frontend/lib/useAsync'
import { DirectionBadge } from './DirectionBadge'
import { DEFAULT_PAGE_SIZE, ListPagination } from './ListPagination'
import { operationServicesApi, operationsApi } from '../lib/entities'
import type { Operation, OperationDirection, OperationStatus } from '../lib/types'

const DIRECTIONS: OperationDirection[] = ['send', 'receive']
const DIRECTION_OPTIONS = DIRECTIONS.map((value) => ({ value, content: value === 'send' ? 'Send' : 'Receive' }))
const STATUS_OPTIONS: { value: OperationStatus; content: string }[] = [
  { value: 'active', content: 'Active' },
  { value: 'removed', content: 'Removed operations' },
]

interface ChannelGroup {
  channelAddress: string
  channelProtocol: string
  operations: Operation[]
}

/** Groups a flat operation list by `channel_address` — the list endpoint itself returns a flat array, so grouping is a display concern applied here rather than on the server. */
function groupByChannel(operations: Operation[]): ChannelGroup[] {
  const groups = new Map<string, ChannelGroup>()
  for (const operation of operations) {
    const existing = groups.get(operation.channelAddress)
    if (existing) {
      existing.operations.push(operation)
      if (!existing.channelProtocol) existing.channelProtocol = operation.channelProtocol
    } else {
      groups.set(operation.channelAddress, {
        channelAddress: operation.channelAddress,
        channelProtocol: operation.channelProtocol,
        operations: [operation],
      })
    }
  }
  return Array.from(groups.values())
}

/** Operations tab on an API's detail page (grouped sections by `channel_address`, not a flat sortable table, so two operations about the same real-world channel never land far apart). */
export function OperationsListTab({ apiId }: { apiId: string }) {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [direction, setDirection] = useState<OperationDirection | null>(null)
  const [status, setStatus] = useState<OperationStatus>('active')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  const filters = useMemo(
    () => ({ search: search || undefined, direction: direction ?? undefined, status }),
    [search, direction, status],
  )

  const { data: operations, error, isLoading } = useAsync(
    () => operationsApi.list(apiId, filters),
    [apiId, JSON.stringify(filters)],
  )

  // The list endpoint isn't paginated, so slice client-side before grouping — a channel that straddles a page boundary appears on both pages.
  const total = operations?.length ?? 0
  const lastPage = Math.max(1, Math.ceil(total / pageSize))
  const currentPage = Math.min(page, lastPage)
  const groups = useMemo(
    () => groupByChannel((operations ?? []).slice((currentPage - 1) * pageSize, currentPage * pageSize)),
    [operations, currentPage, pageSize],
  )
  const groupKey = groups.map((group) => group.channelAddress).join('')

  // Publisher/subscriber counts per channel (spec's "Channel group shows a
  // publisher/subscriber summary") — one `/consumers` fetch per distinct
  // channel, since that endpoint already aggregates by `channel_address`
  // across every contributing Operation.
  const [roleCounts, setRoleCounts] = useState<Record<string, { publishers: number; subscribers: number }>>({})

  useEffect(() => {
    let cancelled = false
    Promise.all(
      groups.map(async (group) => {
        try {
          const consumers = await operationServicesApi.consumers(group.operations[0].id)
          // Role totals come from the response, not `participants.length`: the list is one page.
          const { publisherCount: publishers, subscriberCount: subscribers } = consumers
          return [group.channelAddress, { publishers, subscribers }] as const
        } catch {
          return [group.channelAddress, { publishers: 0, subscribers: 0 }] as const
        }
      }),
    ).then((entries) => {
      if (!cancelled) setRoleCounts(Object.fromEntries(entries))
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupKey])

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
        <TextInput
          placeholder="Search channel, summary, operation ID…"
          value={search}
          onUpdate={(value) => { setSearch(value); setPage(1) }}
          hasClear
          style={{ maxWidth: 280, flex: '1 1 220px' }}
        />
        <Select
          placeholder="Direction"
          value={direction ? [direction] : []}
          onUpdate={(value) => { setDirection((value[0] as OperationDirection) ?? null); setPage(1) }}
          options={DIRECTION_OPTIONS}
          hasClear
          width={140}
        />
        <SegmentedRadioGroup
          value={status}
          onUpdate={(value) => { setStatus(value as OperationStatus); setPage(1) }}
          options={STATUS_OPTIONS}
        />
      </div>

      {error && <Alert theme="danger" message={error.message} />}

      {isLoading && !operations ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Skeleton style={{ height: 36 }} />
          <Skeleton style={{ height: 36 }} />
          <Skeleton style={{ height: 36 }} />
        </div>
      ) : groups.length === 0 ? (
        <Text color="secondary">{status === 'removed' ? 'No removed operations' : 'No operations'}</Text>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {groups.map((group) => {
            const counts = roleCounts[group.channelAddress]
            return (
              <section
                key={group.channelAddress}
                style={{ border: '1px solid var(--g-color-line-generic)', borderRadius: 8, padding: 16 }}
              >
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                  <Text variant="subheader-2" style={{ fontFamily: 'var(--g-text-code-font-family, monospace)' }}>
                    {group.channelAddress}
                  </Text>
                  {group.channelProtocol && <Label>{group.channelProtocol}</Label>}
                  {counts && (
                    <Text color="secondary">
                      {counts.publishers} publisher{counts.publishers === 1 ? '' : 's'}, {counts.subscribers} subscriber{counts.subscribers === 1 ? '' : 's'}
                    </Text>
                  )}
                </div>
                <EntityTable
                  data={group.operations}
                  columns={[
                    { id: 'direction', name: 'Direction', template: (item: Operation) => <DirectionBadge direction={item.direction} /> },
                    { id: 'summary', name: 'Summary', template: (item: Operation) => item.summary || item.operationId || '—' },
                    {
                      id: 'status',
                      name: '',
                      template: (item: Operation) =>
                        item.status === 'removed' ? (
                          <Label theme="danger" icon={<Icon data={TriangleExclamation} size={12} />}>
                            Removed
                          </Label>
                        ) : null,
                    },
                  ]}
                  getRowId={(item: Operation) => item.id}
                  onRowClick={(item: Operation) => navigate(`/apis/${apiId}/operations/${item.id}`)}
                />
              </section>
            )
          })}
        </div>
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
