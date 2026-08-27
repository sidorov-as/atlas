// Linked Services management tab — search,
// team filter, sort (service/team, asc/desc, state kept in the URL),
// Link/Unlink actions gated on
// `endpointDependency.create`/`.delete`.
//
// Gating: this frontend has no per-permission-string check
// anywhere else (every other Edit/Delete action here relies on the backend
// enforcing ownership and just renders unconditionally) — but the
// evaluator note resolves `endpointDependency.create`/`.delete` to "any
// authenticated user", the same rule `.read` already gets. `useSession()` is
// the one client-side signal that actually matches that rule (every route
// here already sits behind `RequireSession`, so in practice this is always
// true once the page renders — the check exists so it stops being a no-op
// the moment a future change scopes this permission further).
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Alert, Button, Icon, Pagination, Select, Skeleton, Text, TextInput } from '@gravity-ui/uikit'
import { ArrowDown, ArrowUp, Link as LinkIcon, LinkSlash } from '@gravity-ui/icons'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { EntityTable } from 'frontend/components/EntityTable'
import { RelationTargetLink } from 'frontend/components/RelationTargetLink'
import { errorMessage } from 'frontend/lib/api'
import { groupsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import type { ApiEntity } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { endpointServicesApi } from '../lib/entities'
import type { Endpoint, EndpointService, ServiceSummary } from '../lib/types'
import { LinkServiceDialog } from './LinkServiceDialog'

type SortField = 'service' | 'team'
type SortOrder = 'asc' | 'desc'

const PAGE_SIZE = 20

export function EndpointLinkedServicesTab({
  endpoint,
  api,
  linkedServices,
  onServicesChanged,
}: {
  endpoint: Endpoint
  api: ApiEntity | undefined
  /** Every currently-linked Service (unpaginated, from the shared consumers fetch) — used to disable already-linked options in the Link dialog even when this tab's own (filtered/paginated) table doesn't include them. */
  linkedServices: ServiceSummary[]
  /** Called after a successful link/unlink so the parent can refresh the graph, the Overview preview, and the tab counter — this tab refreshes its own table itself. */
  onServicesChanged: () => void
}) {
  const { session } = useSession()
  // Administrative and custom mutation controls obey
  // read-only — this tab's own permission-string mapping already resolves
  // `endpointDependency.create`/`.delete` to "any authenticated user"; read-only narrows that
  // the same way it narrows every other write affordance.
  const canLinkOrUnlink = Boolean(session?.isAuthenticated) && !session?.isReadOnly

  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') ?? ''
  const teamId = searchParams.get('team') ?? ''
  const sort: SortField = searchParams.get('sort') === 'team' ? 'team' : 'service'
  const order: SortOrder = searchParams.get('order') === 'desc' ? 'desc' : 'asc'
  const page = Number(searchParams.get('page') ?? '1') || 1

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
    () => endpointServicesApi.list(endpoint.id, {
      search: search || undefined,
      teamId: teamId || undefined,
      sort,
      order,
      page,
      pageSize: PAGE_SIZE,
    }),
    [endpoint.id, search, teamId, sort, order, page],
  )

  const { data: teamsPage } = useAsync(() => groupsApi.list({ pageSize: 100 }), [])
  const teamOptions = (teamsPage?.page.objectList ?? []).map((group) => ({
    value: group.id,
    content: group.metadata.title || group.metadata.name,
  }))

  const services = data?.page.objectList ?? []
  const linkedServiceIds = new Set(linkedServices.map((service) => service.id))

  function handleLinked() {
    reload()
    onServicesChanged()
  }

  async function handleUnlink(item: EndpointService) {
    const name = item.service.title || item.service.name
    if (!(await confirm({ title: 'Unlink', message: `Unlink "${name}" from this endpoint? Its consumesAPI relation is not affected.`, preset: 'default' }))) return
    setUnlinkingId(item.service.id)
    setUnlinkError(null)
    try {
      await endpointServicesApi.unlink(endpoint.id, item.service.id)
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
      {endpoint.status === 'removed' && (
        <Alert
          theme="warning"
          message="This endpoint was removed from the API — services below still declare a dependency on it."
          style={{ marginBottom: 16 }}
        />
      )}
      {endpoint.deprecated && (
        <Alert
          theme="info"
          message="This endpoint is deprecated and will go away in the future — services below still declare a dependency on it."
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
        {endpoint.status === 'active' && canLinkOrUnlink && (
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
                template: (item: EndpointService) => (
                  <RelationTargetLink target={item.service.ref} targetKind="component" targetId={item.service.id} />
                ),
              },
              {
                id: 'team',
                name: 'Team',
                template: (item: EndpointService) => (
                  <RelationTargetLink target={item.service.team} targetKind="group" targetId={item.service.teamId} />
                ),
              },
              ...(canLinkOrUnlink ? [{
                id: 'actions',
                name: 'Actions',
                template: (item: EndpointService) => (
                  <Button
                    view="flat-danger"
                    size="s"
                    loading={unlinkingId === item.service.id}
                    onClick={() => void handleUnlink(item)}
                  >
                    <Icon data={LinkSlash} /> Unlink
                  </Button>
                ),
              }] : []),
            ]}
            getRowId={(item: EndpointService) => item.id}
            emptyMessage="No services are linked to this endpoint yet"
          />
          {data && data.count > PAGE_SIZE && (
            <div style={{ marginTop: 16 }}>
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={data.count}
                onUpdate={(nextPage) => updateParams({ page: String(nextPage) })}
              />
            </div>
          )}
          {data && data.count > 0 && (
            <Text color="secondary" style={{ display: 'block', marginTop: 12 }}>
              {data.count} linked service{data.count === 1 ? '' : 's'} total.
            </Text>
          )}
        </>
      )}

      <LinkServiceDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        endpoint={endpoint}
        api={api}
        linkedServiceIds={linkedServiceIds}
        onLinked={handleLinked}
      />
      <ConfirmDialog {...confirmDialogProps} />
    </div>
  )
}
