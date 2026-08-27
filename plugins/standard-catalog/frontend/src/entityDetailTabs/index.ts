import type { EntityDetailTabContribution } from '@atlas/plugin-api'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { componentEntityDetailTabs } from './component'
import { resourceEntityDetailTabs } from './resource'
import { systemEntityDetailTabs } from './system'
import { teamEntityDetailTabs } from './team'

export const standardCatalogEntityDetailTabs: EntityDetailTabContribution<CatalogEntityUnion>[] = [
  ...resourceEntityDetailTabs,
  ...componentEntityDetailTabs,
  ...systemEntityDetailTabs,
  ...teamEntityDetailTabs,
]
