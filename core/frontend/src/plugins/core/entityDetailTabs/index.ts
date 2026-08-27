import type { EntityDetailTabContribution } from '@atlas/plugin-api'
import type { CatalogEntityUnion } from '../../../lib/types'

// System/Component/Resource/Team's tabs moved to `@atlas/plugin-standard-catalog`
// API's to `@atlas/plugin-apis` —
// core itself contributes no entity-detail tabs of its own.
export const coreEntityDetailTabs: EntityDetailTabContribution<CatalogEntityUnion>[] = []
