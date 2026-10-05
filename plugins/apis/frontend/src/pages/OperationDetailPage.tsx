import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Alert, Breadcrumbs, Icon, Label, Link, Skeleton, Tab, TabList, TabPanel, TabProvider, Text } from '@gravity-ui/uikit'
import { TriangleExclamation } from '@gravity-ui/icons'
import { ApiError } from 'frontend/lib/api'
import { apisApi } from 'frontend/lib/entities'
import { useAsync } from 'frontend/lib/useAsync'
import { DirectionBadge } from '../components/DirectionBadge'
import { OperationOverviewTab } from '../components/OperationOverviewTab'
import { OperationMessageTab } from '../components/OperationMessageTab'
import { OperationLinkedServicesTab } from '../components/OperationLinkedServicesTab'
import { operationServicesApi, operationsApi } from '../lib/entities'

/** `/apis/:apiId/operations/:operationId` — Overview/Message/Linked services tabs, mirroring `EndpointDetailPage`'s conventions without going through `EntityDetailShell` (`Operation` isn't a `CatalogEntity` either). */
export function OperationDetailPage() {
  const { apiId, operationId } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') ?? 'overview'

  const { data: api } = useAsync(() => apisApi.get(apiId as string), [apiId])
  const { data: operation, error, isLoading } = useAsync(
    () => operationsApi.get(apiId as string, operationId as string),
    [apiId, operationId],
  )
  // Only the total of this Operation's own `ServiceOperationUsage` links is
  // needed here (removed-operation banner, "Linked services" tab counter); the
  // tab does its own paginated fetch and the Link dialog checks exact
  // already-linked pairs itself.
  const { data: linkedServicesPage, reload: reloadLinkedServices } = useAsync(
    () => (operationId ? operationServicesApi.list(operationId, { pageSize: 1 }) : Promise.resolve(null)),
    [operationId],
  )
  // Channel-scoped aggregation feeding the compact
  // publishers/subscribers graph on the Overview tab — deliberately a
  // separate fetch from `linkedServicesPage` above, since it can include
  // participants from other API documents sharing this Operation's channel.
  const { data: consumers, error: consumersError, isLoading: consumersLoading, reload: reloadConsumers } = useAsync(
    () => (operationId ? operationServicesApi.consumers(operationId) : Promise.resolve(null)),
    [operationId],
  )

  function handleServicesChanged() {
    reloadLinkedServices()
    reloadConsumers()
  }

  function setTab(value: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      next.set('tab', value)
      return next
    })
  }

  if (error) {
    // Distinguished from a general documentation-load failure (spec's "Operation not found is distinguished from other failures").
    if (error instanceof ApiError && error.status === 404) {
      return (
        <div>
          <Alert theme="warning" title="Operation not found" message="This operation doesn't exist." />
          <div style={{ marginTop: 12 }}>
            <Link href={`/apis/${apiId}`} onClick={(event) => { event.preventDefault(); navigate(`/apis/${apiId}`) }}>
              Back to API
            </Link>
          </div>
        </div>
      )
    }
    return <Alert theme="danger" message={error.message} />
  }

  if (isLoading && !operation) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Skeleton style={{ height: 20, width: 240 }} />
        <Skeleton style={{ height: 32, width: 400 }} />
        <Skeleton style={{ height: 200 }} />
      </div>
    )
  }

  if (!operation) return null

  const linkedCount = linkedServicesPage?.count ?? 0

  return (
    <div>
      <Breadcrumbs>
        <Breadcrumbs.Item href="/apis" onClick={(event) => { event.preventDefault(); navigate('/apis') }}>
          APIs
        </Breadcrumbs.Item>
        <Breadcrumbs.Item
          href={`/apis/${apiId}`}
          onClick={(event) => { event.preventDefault(); navigate(`/apis/${apiId}`) }}
        >
          {api?.metadata.title || api?.metadata.name || '…'}
        </Breadcrumbs.Item>
        <Breadcrumbs.Item>{operation.channelAddress}</Breadcrumbs.Item>
      </Breadcrumbs>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '12px 0 4px' }}>
        <DirectionBadge direction={operation.direction} />
        <Text variant="header-1" style={{ fontFamily: 'var(--g-text-code-font-family, monospace)' }}>{operation.channelAddress}</Text>
        {operation.channelProtocol && <Label>{operation.channelProtocol}</Label>}
        {operation.deprecated && (
          <Label theme="warning" icon={<Icon data={TriangleExclamation} size={12} />}>Deprecated</Label>
        )}
      </div>
      {operation.summary && <Text color="secondary">{operation.summary}</Text>}

      {operation.status === 'removed' && (
        <div style={{ margin: '16px 0' }}>
          <Alert
            theme="danger"
            title="This operation was removed from the API"
            message={
              linkedCount > 0
                ? `${linkedCount} service${linkedCount === 1 ? '' : 's'} still declare${linkedCount === 1 ? 's' : ''} a dependency on it.`
                : 'No services currently declare a dependency on it.'
            }
          />
        </div>
      )}

      <TabProvider value={activeTab} onUpdate={setTab}>
        <TabList>
          <Tab value="overview">Overview</Tab>
          <Tab value="message">Message</Tab>
          <Tab value="services" counter={linkedCount}>Linked services</Tab>
        </TabList>
        <div style={{ paddingTop: 16 }}>
          <TabPanel value="overview">
            <OperationOverviewTab
              operation={operation}
              api={api ?? undefined}
              consumers={consumers ?? null}
              consumersLoading={consumersLoading}
              consumersError={consumersError}
              onRetryConsumers={reloadConsumers}
              onViewLinkedServices={() => setTab('services')}
              linkedServicesTotal={linkedCount}
            />
          </TabPanel>
          <TabPanel value="message">
            <OperationMessageTab operation={operation} />
          </TabPanel>
          <TabPanel value="services">
            <OperationLinkedServicesTab
              operation={operation}
              onServicesChanged={handleServicesChanged}
            />
          </TabPanel>
        </div>
      </TabProvider>
    </div>
  )
}
