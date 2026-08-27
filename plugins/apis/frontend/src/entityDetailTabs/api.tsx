// API's entity-detail tabs — split out of `frontend/plugins/core/entityDetailTabs/api`
import { Text } from '@gravity-ui/uikit'
import { entityDetailTab } from '@atlas/plugin-api'
import { DocumentationPreview } from 'frontend/components/DocumentationPreview'
import { HistoryTab } from 'frontend/components/HistoryTab'
import { RelationsTab } from 'frontend/components/RelationsTab'
import { architectureRelationshipsApi, apisApi } from 'frontend/lib/entities'
import type { ApiEntity, CatalogEntityUnion } from 'frontend/lib/types'
import { ApiDocumentationView, DownloadSpecButton, EndpointSyncFailedLabel, OperationSyncFailedLabel, StaleSpecLabel } from '../components/ApiSpecPanel'
import { EndpointsListTab } from '../components/EndpointsListTab'
import { OperationsListTab } from '../components/OperationsListTab'

const VIEWER_TYPES: ApiEntity['spec']['type'][] = ['openapi', 'asyncapi']

function isApi(entity: CatalogEntityUnion): entity is ApiEntity {
  return entity.kind === 'API'
}

function ApiOverviewTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isApi(entity)) return null
  return <DocumentationPreview value={entity.metadata.documentation} />
}

function ApiSpecificationTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isApi(entity)) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <DownloadSpecButton api={entity} />
        {entity.spec.specResolveFailed && <StaleSpecLabel />}
      </div>
      {VIEWER_TYPES.includes(entity.spec.type) ? (
        <ApiDocumentationView api={entity} />
      ) : (
        <Text color="secondary">No embedded viewer is available for {entity.spec.type.toUpperCase()} specifications. Download the specification to view it.</Text>
      )}
    </div>
  )
}

function ApiRelationsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isApi(entity)) return null
  return (
    <RelationsTab
      fetchRelations={() => apisApi.relations(entity.id)}
      fetchArchitectureRelationships={() => architectureRelationshipsApi.list(`api:${entity.metadata.name}`)}
      source={`api:${entity.metadata.name}`}
      canManageArchitectureRelationships={!entity.ingestedFrom}
    />
  )
}

// A new entityDetailTab,
// following the same convention as Overview/Specification/Relations above rather
// than editing `ApiDetailPage.tsx` directly.
function ApiEndpointsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isApi(entity)) return null
  // A synced (`openapi` type, non-empty resolved spec) API's *active* endpoints
  // are always spec-derived — any manually-authored one not matching a parsed
  // operation is soft-removed on the next sync, so a
  // single page-level note is accurate without a per-endpoint badge.
  const isSpecManaged = entity.spec.type === 'openapi' && entity.spec.specContent !== ''
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {entity.spec.endpointsSyncFailed && (
        <div style={{ display: 'flex' }}>
          <EndpointSyncFailedLabel />
        </div>
      )}
      {isSpecManaged && (
        <Text color="secondary">
          Endpoints below are imported from this API&rsquo;s spec and are updated automatically when the spec changes.
        </Text>
      )}
      <EndpointsListTab apiId={entity.id} />
    </div>
  )
}

// A new
// entityDetailTab, mirroring `ApiEndpointsTab` above exactly (grouped-by-channel
// list, not a direct `ApiDetailPage.tsx` edit).
function ApiOperationsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isApi(entity)) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {entity.spec.operationsSyncFailed && (
        <div style={{ display: 'flex' }}>
          <OperationSyncFailedLabel />
        </div>
      )}
      <OperationsListTab apiId={entity.id} />
    </div>
  )
}

function ApiHistoryTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isApi(entity)) return null
  return <HistoryTab fetchHistory={() => apisApi.history(entity.id)} />
}

export const apiEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.apis.api.overview', value: 'overview', label: 'Overview', when: isApi, component: ApiOverviewTab }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.apis.api.specification',
    value: 'specification',
    label: 'Specification',
    when: (entity) => isApi(entity) && entity.spec.specContent !== '',
    component: ApiSpecificationTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.apis.api.endpoints',
    value: 'endpoints',
    label: 'Operations',
    when: (entity) => isApi(entity) && entity.spec.type === 'openapi',
    component: ApiEndpointsTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.apis.api.operations',
    value: 'operations',
    label: 'Operations',
    when: (entity) => isApi(entity) && entity.spec.type === 'asyncapi',
    component: ApiOperationsTab,
  }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.apis.api.relations', value: 'relations', label: 'Relations', when: isApi, component: ApiRelationsTab }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.apis.api.history',
    value: 'history',
    label: 'History',
    when: isApi,
    component: ApiHistoryTab,
  }),
]
