// Standard Catalog frontend plugin — System, Component,
// Resource, and Team's routes, nav items, and entity-detail tabs, moved out of the in-tree
// "core" plugin module (`frontend/src/plugins/core/`) into this independent package boundary.
// Actor gets no frontend contributions of its own (admin-managed only, same as today).
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { standardCatalogEntityDetailTabs } from './entityDetailTabs'
import { standardCatalogNavItems } from './navItems'
import { standardCatalogRoutes } from './routes'

export const standardCatalogPlugin = defineFrontendPlugin({
  id: 'atlas.standard-catalog',
  contributions: [...standardCatalogRoutes, ...standardCatalogNavItems, ...standardCatalogEntityDetailTabs],
})
