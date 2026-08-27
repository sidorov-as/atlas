// The single in-tree "core" plugin: wraps
// every existing route, nav item, and entity-detail tab as contributions, proving the
// composition mechanism without yet splitting any code into separately built packages.
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { coreEntityDetailTabs } from './entityDetailTabs'
import { coreNavItems } from './navItems'
import { coreRoutes } from './routes'

export const corePlugin = defineFrontendPlugin({
  id: 'atlas.core',
  contributions: [...coreRoutes, ...coreNavItems, ...coreEntityDetailTabs],
})
