// APIs frontend plugin — API's routes, nav items, and entity-detail
// tabs, moved out of the in-tree "core" plugin module (`frontend/src/plugins/core/`) into
// this independent package boundary, matching `@atlas/plugin-standard-catalog`.
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { apisEntityDetailTabs } from './entityDetailTabs'
import { apisNavItems } from './navItems'
import { apisRoutes } from './routes'

export const apisPlugin = defineFrontendPlugin({
  id: 'atlas.apis',
  contributions: [...apisRoutes, ...apisNavItems, ...apisEntityDetailTabs],
})
