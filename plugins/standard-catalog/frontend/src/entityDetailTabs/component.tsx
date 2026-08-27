import { Label, Text } from '@gravity-ui/uikit'
import { entityDetailTab } from '@atlas/plugin-api'
import { DocumentationPreview } from 'frontend/components/DocumentationPreview'
import { HistoryTab } from 'frontend/components/HistoryTab'
import { LifecycleWarning, RelationsTab } from 'frontend/components/RelationsTab'
import { RelationTargetLink } from 'frontend/components/RelationTargetLink'
import { architectureRelationshipsApi, componentsApi } from 'frontend/lib/entities'
import { type CatalogEntityUnion, type ComponentEntity, type Relation } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'

function isComponent(entity: CatalogEntityUnion): entity is ComponentEntity {
  return entity.kind === 'Component'
}

/** Relations by predicate, each entry's target warning-flagged from the relation's own
 * `status`/`deprecated` — covers `providesAPI`/`consumesAPI`/
 * `dependsOn` alike, so a target that's `removed` or `deprecated` is visibly flagged here too,
 * not just on the dedicated Relations tab. */
function ApiRelationList({ relations, predicate }: { relations: Relation[]; predicate: string }) {
  const entries = relations.filter((relation) => relation.predicate === predicate)
  if (entries.length === 0) return <Text color="secondary">None</Text>
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {entries.map((relation) => (
        <Label key={relation.target}>
          <RelationTargetLink target={relation.target} targetKind={relation.targetKind} targetId={relation.targetId} />
          <LifecycleWarning status={relation.status} deprecated={relation.deprecated} />
        </Label>
      ))}
    </div>
  )
}

function ComponentOverviewTab({ entity }: { entity: CatalogEntityUnion }) {
  // useAsync must run unconditionally (rules-of-hooks); the id it depends on is only
  // meaningful once `entity` narrows to a Component, so the fetcher branches internally.
  const component = isComponent(entity) ? entity : null
  const { data: relations } = useAsync(
    () => (component ? componentsApi.relations(component.id) : Promise.resolve([])),
    [component?.id],
  )
  if (!component) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <DocumentationPreview value={component.metadata.documentation} />
      <div>
        <Text variant="subheader-1" style={{ display: 'block', marginBottom: 4 }}>
          Provides APIs
        </Text>
        <ApiRelationList relations={relations ?? []} predicate="providesAPI" />
      </div>
      <div>
        <Text variant="subheader-1" style={{ display: 'block', marginBottom: 4 }}>
          Consumes APIs
        </Text>
        <ApiRelationList relations={relations ?? []} predicate="consumesAPI" />
      </div>
      <div>
        <Text variant="subheader-1" style={{ display: 'block', marginBottom: 4 }}>
          Depends on
        </Text>
        <ApiRelationList relations={relations ?? []} predicate="dependsOn" />
      </div>
    </div>
  )
}

function ComponentRelationsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isComponent(entity)) return null
  return (
    <RelationsTab
      fetchRelations={() => componentsApi.relations(entity.id)}
      fetchArchitectureRelationships={() => architectureRelationshipsApi.list(`component:${entity.metadata.name}`)}
      source={`component:${entity.metadata.name}`}
      canManageArchitectureRelationships={!entity.ingestedFrom}
    />
  )
}

function ComponentHistoryTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isComponent(entity)) return null
  return <HistoryTab fetchHistory={() => componentsApi.history(entity.id)} />
}

export const componentEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.standard-catalog.component.overview',
    value: 'overview',
    label: 'Overview',
    when: isComponent,
    component: ComponentOverviewTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.standard-catalog.component.relations',
    value: 'relations',
    label: 'Relations',
    when: isComponent,
    component: ComponentRelationsTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.standard-catalog.component.history',
    value: 'history',
    label: 'History',
    when: isComponent,
    component: ComponentHistoryTab,
  }),
]
