// Resource's Schema editor and ER Diagram tab contributions —
// gated by `entitySupports('schema.host.v1')`, not a
// hard-coded `kind === 'Resource'` check, so the mechanism generalizes to any
// future kind that declares the capability.
import { entityDetailTab, entitySupports } from '@atlas/plugin-api'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { ErDiagramTab } from '../components/ErDiagramTab'
import { SchemaEditorTab } from '../components/SchemaEditorTab'

const supportsSchemaHost = entitySupports('schema.host.v1')

export const resourceEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.database-schema.resource.schema',
    value: 'schema',
    label: 'Schema',
    when: supportsSchemaHost,
    component: SchemaEditorTab,
  }),
  entityDetailTab<CatalogEntityUnion>({
    id: 'atlas.database-schema.resource.er-diagram',
    value: 'er-diagram',
    label: 'ER Diagram',
    fullWidth: true,
    when: supportsSchemaHost,
    component: ErDiagramTab,
  }),
]
