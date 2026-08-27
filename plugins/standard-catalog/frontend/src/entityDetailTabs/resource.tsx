import { entityDetailTab } from '@atlas/plugin-api'
import { DocumentationPreview } from 'frontend/components/DocumentationPreview'
import { HistoryTab } from 'frontend/components/HistoryTab'
import { RelationsTab } from 'frontend/components/RelationsTab'
import { architectureRelationshipsApi, resourcesApi } from 'frontend/lib/entities'
import type { CatalogEntityUnion, ResourceEntity } from 'frontend/lib/types'

function isResource(entity: CatalogEntityUnion): entity is ResourceEntity {
  return entity.kind === 'Resource'
}

function ResourceOverviewTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isResource(entity)) return null
  return <DocumentationPreview value={entity.metadata.documentation} />
}

function ResourceRelationsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isResource(entity)) return null
  return (
    <RelationsTab
      fetchRelations={() => resourcesApi.relations(entity.id)}
      fetchArchitectureRelationships={() => architectureRelationshipsApi.list(`resource:${entity.metadata.name}`)}
      source={`resource:${entity.metadata.name}`}
      canManageArchitectureRelationships={!entity.ingestedFrom}
    />
  )
}

function ResourceHistoryTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isResource(entity)) return null
  return <HistoryTab fetchHistory={() => resourcesApi.history(entity.id)} />
}

export const resourceEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.standard-catalog.resource.overview',
    value: 'overview',
    label: 'Overview',
    when: isResource,
    component: ResourceOverviewTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.standard-catalog.resource.relations',
    value: 'relations',
    label: 'Relations',
    when: isResource,
    component: ResourceRelationsTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.standard-catalog.resource.history',
    value: 'history',
    label: 'History',
    when: isResource,
    component: ResourceHistoryTab,
  }),
]
