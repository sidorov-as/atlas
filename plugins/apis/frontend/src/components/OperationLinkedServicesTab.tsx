// Linked Services management tab —
// search, team filter, role filter, sort (service/team, asc/desc, state kept
// in the URL), Link/Unlink actions
// gated on `operationDependency.create`/`.delete`.
//
// Gating: mirrors `EndpointLinkedServicesTab`'s note — this
// frontend has no per-permission-string check anywhere else, but
// the evaluator resolves `operationDependency.create`/`.delete` to "any
// authenticated user", the same rule `.read` already gets. `useSession()` is
// the one client-side signal that actually matches that rule.
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Alert, Button, Icon, Select, Skeleton, Text, TextInput } from '@gravity-ui/uikit'
import { ArrowDown, ArrowUp, Link as LinkIcon, LinkSlash } from '@gravity-ui/icons'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { EntityTable } from 'frontend/components/EntityTable'
import { RelationTargetLink } from 'frontend/components/RelationTargetLink'
import { errorMessage } from 'frontend/lib/api'
import { groupsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { RoleBadge } from './RoleBadge'
import { LinkOperationServiceDialog } from './LinkOperationServiceDialog'
import { DEFAULT_PAGE_SIZE, ListPagination, PAGE_SIZE_OPTIONS } from './ListPagination'
import { operationServicesApi } from '../lib/entities'
import type { Operation, OperationRole, OperationService } from '../lib/types'

type SortField = 'service' | 'team'
type SortOrder = 'asc' | 'desc'


const ROLE_FILTER_OPTIONS = [
  { value: 'publisher', content: 'Publisher' },
  { value: 'subscriber', content: 'Subscriber' },
]

export function OperationLinkedServicesTab({
  operation,
  onServicesChanged,
}: {
  operation: Operation
  /** Called after a successful link/unlink so the parent can refresh the graph, the Overview preview, and the tab counter — this tab refreshes its own table itself. */
  onServicesChanged: () => void
}) {
  const { session } = useSession()
  // Administrative and custom mutation controls obey
  // read-only — this tab's own permission-string mapping already resolves
  // `operationDependency.create`/`.delete` to "any authenticated user"; read-only narrows that
  // the same way it narrows every other write affordance.
  const canLinkOrUnlink = Boolean(session?.isAuthenticated) && !session?.isReadOnly

  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') ?? ''
  const teamId = searchParams.get('team') ?? ''
  const role = (searchParams.get('role') as OperationRole | null) ?? undefined
  const sort: SortField = searchParams.get('sort') === 'team' ? 'team' : 'service'
  const order: SortOrder = searchParams.get('order') === 'desc' ? 'desc' : 'asc'
  const page = Number(searchParams.get('page') ?? '1') || 1
  const requestedSize = Number(searchParams.get('page_size'))
  const pageSize = PAGE_SIZE_OPTIONS.includes(requestedSize) ? requestedSize : DEFAULT_PAGE_SIZE

  const [dialogOpen, setDialogOpen] = useState(false)
  const [unlinkingId, setUnlinkingId] = useState<string | null>(null)
  const [unlinkError, setUnlinkError] = useState<string | null>(null)
  const { confirm, dialogProps: confirmDialogProps } = useConfirm()

  function updateParams(next: Record<string, string | null>) {
    setSearchParams((previous) => {
      const params = new URLSearchParams(previous)
      for (const [key, value] of Object.entries(next)) {
        if (value === null || value === '') params.delete(key)
        else params.set(key, value)
      }
      return params
    })
  }

  const { data, error, isLoading, reload } = useAsync(
    () => operationServicesApi.list(operation.id, {
      search: search || undefined,
      teamId: teamId || undefined,
      role,
      sort,
      order,
      page,
      pageSize,
    }),
    [operation.id, search, teamId, role, sort, order, page, pageSize],
  )

  const { data: teamsPage } = useAsync(() => groupsApi.list({ pageSize: 100 }), [])
  const teamOptions = (teamsPage?.page.objectList ?? []).map((group) => ({
    value: group.id,
    content: group.metadata.title || group.metadata.name,
  }))

  const services = data?.page.objectList ?? []

  function handleLinked() {
    reload()
    onServicesChanged()
  }

  async function handleUnlink(item: OperationService) {
    const name = item.service.title || item.service.name
    if (!(await confirm({ title: 'Unlink', message: `Unlink "${name}" (${item.role}) from this operation?`, preset: 'default' }))) return
    setUnlinkingId(item.id)
    setUnlinkError(null)
    try {
      await operationServicesApi.unlink(operation.id, item.service.id, item.role)
      reload()
      onServicesChanged()
    } catch (err) {
      setUnlinkError(errorMessage(err, 'Failed to unlink service'))
    } finally {
      setUnlinkingId(null)
    }
  }

  return (
    <div>
      {operation.status === 'removed' && (
        <Alert
          theme="warning"
          message="This operation was removed from the API — services below still declare a dependency on it."
          style={{ marginBottom: 16 }}
        />
      )}
      {operation.deprecated && (
        <Alert
          theme="info"
          message="This operation is deprecated and will go away in the future — services below still declare a dependency on it."
          style={{ marginBottom: 16 }}
        />
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <TextInput
          placeholder="Search services…"
          value={search}
          onUpdate={(value) => updateParams({ search: value || null, page: null })}
          hasClear
          style={{ minWidth: 200, maxWidth: 320, flex: '1 1 240px' }}
        />
        <Select
          placeholder="Role"
          value={role ? [role] : []}
          onUpdate={(next) => updateParams({ role: next[0] ?? null, page: null })}
          options={ROLE_FILTER_OPTIONS}
          hasClear
          width={160}
        />
        <Select
          placeholder="Team"
          value={teamId ? [teamId] : []}
          onUpdate={(next) => updateParams({ team: next[0] ?? null, page: null })}
          options={teamOptions}
          hasClear
          width={180}
        />
        <Select
          placeholder="Sort by"
          value={[sort]}
          onUpdate={(next) => updateParams({ sort: next[0] ?? null, page: null })}
          options={[{ value: 'service', content: 'Service' }, { value: 'team', content: 'Team' }]}
          width={140}
        />
        <Button
          view="outlined"
          onClick={() => updateParams({ order: order === 'asc' ? 'desc' : 'asc', page: null })}
          aria-label={order === 'asc' ? 'Sort ascending' : 'Sort descending'}
        >
          <Icon data={order === 'asc' ? ArrowUp : ArrowDown} />
        </Button>
        {operation.status === 'active' && canLinkOrUnlink && (
          <Button view="action" onClick={() => setDialogOpen(true)} style={{ marginLeft: 'auto' }}>
            <Icon data={LinkIcon} /> Link service
          </Button>
        )}
      </div>

      {error && <Alert theme="danger" message={errorMessage(error)} style={{ marginBottom: 16 }} />}
      {unlinkError && <Alert theme="danger" message={unlinkError} style={{ marginBottom: 16 }} />}

      {isLoading && !data ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Skeleton style={{ height: 36 }} />
          <Skeleton style={{ height: 36 }} />
        </div>
      ) : (
        <>
          <EntityTable
            data={services}
            columns={[
              {
                id: 'service',
                name: 'Service',
                template: (item: OperationService) => (
                  <RelationTargetLink target={item.service.ref} targetKind="component" targetId={item.service.id} />
                ),
              },
              { id: 'role', name: 'Role', template: (item: OperationService) => <RoleBadge role={item.role} /> },
              {
                id: 'team',
                name: 'Team',
                template: (item: OperationService) =>
                  item.service.team && item.service.teamId ? (
                    <RelationTargetLink target={item.service.team} targetKind="group" targetId={item.service.teamId} />
                  ) : (
                    '—'
                  ),
              },
              ...(canLinkOrUnlink ? [{
                id: 'actions',
                name: 'Actions',
                template: (item: OperationService) => (
                  <Button
                    view="flat-danger"
                    size="s"
                    loading={unlinkingId === item.id}
                    onClick={() => void handleUnlink(item)}
                  >
                    <Icon data={LinkSlash} /> Unlink
                  </Button>
                ),
              }] : []),
            ]}
            getRowId={(item: OperationService) => item.id}
            emptyMessage="No services are linked to this operation yet"
          />
          {data && (
            <ListPagination
              page={page}
              pageSize={pageSize}
              total={data.count}
              onUpdate={(nextPage, nextPageSize) =>
                updateParams({
                  page: nextPage === 1 ? null : String(nextPage),
                  page_size: nextPageSize === DEFAULT_PAGE_SIZE ? null : String(nextPageSize),
                })
              }
            />
          )}
          {data && data.count > 0 && (
            <Text color="secondary" style={{ display: 'block', marginTop: 12 }}>
              {data.count} linked service{data.count === 1 ? '' : 's'} total.
            </Text>
          )}
        </>
      )}

      <LinkOperationServiceDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        operation={operation}
        onLinked={handleLinked}
      />
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  )
}
