import { entityDetailTab, entitySupports } from '@atlas/plugin-api'
import type { CatalogEntityUnion, SystemEntity } from 'frontend/lib/types'
import { DiagramTab } from '../components/DiagramTab'

const supportsSubjectDiagrams = entitySupports('architecture.subject.v1')

// `architecture.subject.v1` alone doesn't distinguish which specific C4 views a kind
// gets — System and Component both declare it but render entirely different diagram
// types (System Context/Architecture vs. an internal Component Diagram), the same way
// `architecture.actor.v1` covers two distinct rendering roles.
// The kind check here is view *selection* given an already-capability-gated entity, not
// a reintroduction of the hard-coded eligibility list `entitySupports` replaced.
function isSystem(entity: CatalogEntityUnion): entity is SystemEntity {
  return entity.kind === 'System'
}

function isSystemDiagramCapable(entity: CatalogEntityUnion): boolean {
  return supportsSubjectDiagrams(entity) && isSystem(entity)
}

function SystemContextTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return <DiagramTab kind="system" id={entity.id} view="context" />
}

function SystemArchitectureTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return <DiagramTab kind="system" id={entity.id} view="architecture" />
}

export const systemEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.c4.system.context', value: 'context', label: 'System Context', fullWidth: true, when: isSystemDiagramCapable, component: SystemContextTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.c4.system.architecture', value: 'architecture', label: 'System Architecture', fullWidth: true, when: isSystemDiagramCapable, component: SystemArchitectureTab }),
]
