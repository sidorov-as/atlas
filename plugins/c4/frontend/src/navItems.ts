// `atlas.c4`'s own nav destination for the System Map — replaces the former `homeWidget` contribution.
// Positioned after "APIs" purely by plugin order in
// `distributions/default/manifest.yaml` (`... apis → c4 ...`), no manifest
// change needed.
import { Hierarchy } from '@gravity-ui/icons'
import { navItem, route, routeRef } from '@atlas/plugin-api'
import { SystemMapPage } from './pages/SystemMapPage'

export const c4Routes = [
  route({ id: 'atlas.c4.system-map', path: '/system-map', component: SystemMapPage }),
]

export const c4NavItems = [
  navItem({ id: 'atlas.c4.nav.system-map', title: 'System Map', icon: Hierarchy, route: routeRef('atlas.c4.system-map') }),
]
