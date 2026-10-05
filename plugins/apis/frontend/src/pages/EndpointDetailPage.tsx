import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Alert, Breadcrumbs, Icon, Label, Link, Skeleton, Tab, TabList, TabPanel, TabProvider, Text } from '@gravity-ui/uikit'
import { TriangleExclamation } from '@gravity-ui/icons'
import { ApiError } from 'frontend/lib/api'
import { apisApi } from 'frontend/lib/entities'
import { useAsync } from 'frontend/lib/useAsync'
import { MethodBadge } from '../components/MethodBadge'
import { EndpointOverviewTab } from '../components/EndpointOverviewTab'
import { EndpointRequestTab } from '../components/EndpointRequestTab'
import { EndpointResponseTab } from '../components/EndpointResponseTab'
import { EndpointLinkedServicesTab } from '../components/EndpointLinkedServicesTab'
import { endpointServicesApi, endpointsApi } from '../lib/entities'

/** `/apis/:apiId/endpoints/:endpointId` — Overview/Request/Response/Linked services tabs, mirroring `EntityDetailShell`'s conventions without going through it (`Endpoint` isn't a `CatalogEntity`). */
export function EndpointDetailPage() {
  const { apiId, endpointId } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') ?? 'overview'

  const { data: api } = useAsync(() => apisApi.get(apiId as string), [apiId])
  // Which Component `providesAPI` this endpoint's API — shown on the consumers
  // graph's endpoint node, not part of the consumers-graph API contract itself.
  const { data: apiRelations } = useAsync(() => apisApi.relations(apiId as string), [apiId])
  const providerRelation = apiRelations?.find((relation) => relation.predicate === 'apiProvidedBy') ?? null
  const { data: endpoint, error, isLoading } = useAsync(
    () => endpointsApi.get(apiId as string, endpointId as string),
    [apiId, endpointId],
  )
  // Single shared fetch: the graph, the Overview
  // preview list, the removed-endpoint banner's count, and the "Linked
  // services" tab counter all read from this one unpaginated request, so a
  // link/unlink anywhere reloads all four at once via `reloadConsumers`.
  const { data: consumers, error: consumersError, isLoading: consumersLoading, reload: reloadConsumers } = useAsync(
    () => (endpointId ? endpointServicesApi.consumers(endpointId) : Promise.resolve(null)),
    [endpointId],
  )

  function setTab(value: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      next.set('tab', value)
      return next
    })
  }

  if (error) {
    // Distinguished from a general documentation-load failure (spec's "Endpoint not found is distinguished from other failures").
    if (error instanceof ApiError && error.status === 404) {
      return (
        <div>
          <Alert theme="warning" title="Endpoint not found" message="This endpoint doesn't exist." />
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

  if (isLoading && !endpoint) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Skeleton style={{ height: 20, width: 240 }} />
        <Skeleton style={{ height: 32, width: 400 }} />
        <Skeleton style={{ height: 200 }} />
      </div>
    )
  }

  if (!endpoint) return null

  const linkedCount = consumers?.count ?? 0

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
        <Breadcrumbs.Item>{endpoint.method} {endpoint.path}</Breadcrumbs.Item>
      </Breadcrumbs>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '12px 0 4px' }}>
        <MethodBadge method={endpoint.method} />
        <Text variant="header-1" style={{ fontFamily: 'var(--g-text-code-font-family, monospace)' }}>{endpoint.path}</Text>
        {endpoint.deprecated && (
          <Label theme="warning" icon={<Icon data={TriangleExclamation} size={12} />}>Deprecated</Label>
        )}
      </div>
      {endpoint.summary && <Text color="secondary">{endpoint.summary}</Text>}

      {endpoint.status === 'removed' && (
        <div style={{ margin: '16px 0' }}>
          <Alert
            theme="danger"
            title="This endpoint was removed from the API"
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
          <Tab value="request">Request</Tab>
          <Tab value="response">Response</Tab>
          <Tab value="services" counter={linkedCount}>Linked services</Tab>
        </TabList>
        <div style={{ paddingTop: 16 }}>
          <TabPanel value="overview">
            <EndpointOverviewTab
              endpoint={endpoint}
              api={api ?? undefined}
              consumers={consumers ?? null}
              consumersLoading={consumersLoading}
              consumersError={consumersError}
              onRetryConsumers={reloadConsumers}
              onViewLinkedServices={() => setTab('services')}
              providerRelation={providerRelation}
            />
          </TabPanel>
          <TabPanel value="request">
            <EndpointRequestTab endpoint={endpoint} />
          </TabPanel>
          <TabPanel value="response">
            <EndpointResponseTab endpoint={endpoint} />
          </TabPanel>
          <TabPanel value="services">
            <EndpointLinkedServicesTab
              endpoint={endpoint}
              api={api ?? undefined}
              onServicesChanged={reloadConsumers}
            />
          </TabPanel>
        </div>
      </TabProvider>
    </div>
  )
}
