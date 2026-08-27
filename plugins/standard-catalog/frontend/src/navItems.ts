// Split out of `frontend/src/plugins/core/navItems.ts`.
import { Cube, Database, Layers, Persons } from '@gravity-ui/icons'
import { navItem, routeRef } from '@atlas/plugin-api'

export const standardCatalogNavItems = [
  navItem({ id: 'atlas.standard-catalog.nav.systems', title: 'Systems', icon: Layers, route: routeRef('atlas.standard-catalog.systems.list') }),
  navItem({ id: 'atlas.standard-catalog.nav.components', title: 'Components', icon: Cube, route: routeRef('atlas.standard-catalog.components.list') }),
  navItem({ id: 'atlas.standard-catalog.nav.resources', title: 'Resources', icon: Database, route: routeRef('atlas.standard-catalog.resources.list') }),
  navItem({ id: 'atlas.standard-catalog.nav.teams', title: 'Teams', icon: Persons, route: routeRef('atlas.standard-catalog.teams.list') }),
]
