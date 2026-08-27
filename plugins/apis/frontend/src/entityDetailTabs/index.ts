import type { EntityDetailTabContribution } from '@atlas/plugin-api'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { apiEntityDetailTabs } from './api'

export const apisEntityDetailTabs: EntityDetailTabContribution<CatalogEntityUnion>[] = [
  ...apiEntityDetailTabs,
]
