// Flows frontend plugin — Flow's routes, nav items, pages, canvas
// components, and lib utilities, moved out of the in-tree "core" plugin module
// (`frontend/src/plugins/core/`) into this independent, optional package boundary,
// matching `@atlas/plugin-apis`/`@atlas/plugin-c4`.
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { flowsNavItems } from './navItems'
import { flowsRoutes } from './routes'

export const flowsPlugin = defineFrontendPlugin({
  id: 'atlas.flows',
  contributions: [...flowsRoutes, ...flowsNavItems],
})
