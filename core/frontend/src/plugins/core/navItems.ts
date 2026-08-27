// AppShell's former literal NAV_ITEMS array, now navItem contributions resolved through
// routeRef.
// Systems/Components/Resources/Teams moved to `@atlas/plugin-standard-catalog`
// APIs to `@atlas/plugin-apis`,
// Flows to `@atlas/plugin-flows`.
import { Gear } from '@gravity-ui/icons'
import { navItem, routeRef } from '@atlas/plugin-api'

export const coreNavItems = [
  navItem({ id: 'atlas.core.nav.settings', title: 'Settings', icon: Gear, route: routeRef('atlas.core.settings') }),
]
