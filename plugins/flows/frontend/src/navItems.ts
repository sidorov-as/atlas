// Split out of `frontend/plugins/core/navItems.ts`.
import { BranchesRight } from '@gravity-ui/icons'
import { navItem, routeRef } from '@atlas/plugin-api'

export const flowsNavItems = [
  navItem({ id: 'atlas.flows.nav.flows', title: 'Flows', icon: BranchesRight, route: routeRef('atlas.flows.flows.list') }),
]
