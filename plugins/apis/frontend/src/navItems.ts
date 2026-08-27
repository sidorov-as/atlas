// Split out of `frontend/plugins/core/navItems.ts`.
import { PlugConnection } from '@gravity-ui/icons'
import { navItem, routeRef } from '@atlas/plugin-api'

export const apisNavItems = [
  navItem({ id: 'atlas.apis.nav.apis', title: 'APIs', icon: PlugConnection, route: routeRef('atlas.apis.apis.list') }),
]
