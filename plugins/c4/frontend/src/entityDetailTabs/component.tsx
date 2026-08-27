import { entityDetailTab, entitySupports } from '@atlas/plugin-api'
import type { CatalogEntityUnion, ComponentEntity } from 'frontend/lib/types'
import { DiagramTab } from '../components/DiagramTab'

const supportsSubjectDiagrams = entitySupports('architecture.subject.v1')

// See system.tsx for why a kind check still selects the specific view alongside the
// capability gate — System and Component share `architecture.subject.v1` but render
// different diagram types.
function isComponent(entity: CatalogEntityUnion): entity is ComponentEntity {
  return entity.kind === 'Component'
}

function isComponentDiagramCapable(entity: CatalogEntityUnion): boolean {
  return supportsSubjectDiagrams(entity) && isComponent(entity)
}

function ComponentDiagramTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isComponent(entity)) return null
  return <DiagramTab kind="component" id={entity.id} view="component" />
}

export const componentEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.c4.component.diagram',
    value: 'diagram',
    label: 'C4 Diagram',
    fullWidth: true,
    when: isComponentDiagramCapable,
    component: ComponentDiagramTab,
  }),
]
